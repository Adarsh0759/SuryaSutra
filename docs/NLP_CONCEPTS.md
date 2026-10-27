# SuryaSutra — the NLP/AI pipeline, explained

This document exists so you (the founder) can explain, to yourself, an investor, or a
reviewer, exactly what SuryaSutra does, why each piece exists, and where to find it in
the code. It follows CLAUDE.md's own teaching rule: for each concept — what it is, why
we need it, what the alternative would be, then how it's actually implemented here.

If you only read one thing, read §1 and §7 (the end-to-end trace) — everything else is
detail underneath those two.

---

## 1. The problem, in one paragraph

A solar plant's SCADA system throws alarms constantly ("fault code 370," "fault code
1610," ...). A technician has to figure out: what does this mean, is it dangerous, what
do I check first, and in what order — usually by searching a 100+ page vendor PDF by
hand. SuryaSutra's job is to take an alarm and hand back a **cited, step-by-step,
safety-first answer**, generated from the plant's own manual, for a few rupees of LLM
cost — and to **say "I don't know"** rather than guess when it can't find the right
evidence. That last part — refusing to guess, with hard guarantees, not just a
confident-sounding hedge — is the actual research contribution. Everything below is in
service of that one property.

---

## 2. The pipeline, top to bottom

```
PDF manual  →  chunks  →  tagged chunks  →  [alarm fires]  →  hybrid retrieval
                                                                      │
                                                            candidate chunks (~40)
                                                                      │
                                                          budgeted selection (the
                                                           research contribution)
                                                                      │
                                              Answered(chunks) ──or── Insufficient
                                                      │
                                              LLM generates cited JSON
                                                      │
                                           citation validator checks it
                                                      │
                                          ANSWERED or INSUFFICIENT to the UI
```

Two things happen at different times:

- **Ingestion** (§3) happens once, when the app starts: the manual gets parsed,
  chunked, and tagged.
- **Triage** (§4–6) happens once per alarm, when you click a row in the UI.

---

## 3. Ingestion: turning a PDF into searchable, taggable chunks

**Concept.** An LLM (and a retrieval index) can't work with a whole 100-page PDF at
once — it needs bite-sized, independently-retrievable pieces ("chunks"), each small
enough to fit in a prompt, each still making sense read on its own.

**Why chunk at all, and why this size.** Too large a chunk wastes token budget on
irrelevant text around the useful sentence; too small a chunk cuts a thought in half
(we actually hit this — see §8). SuryaSutra packs paragraphs into ~300-token chunks,
splitting only at paragraph boundaries, never mid-sentence.

- Code: `src/suryasutra/ingest/chunk.py`, `chunk_pages()`
- It reads each PDF page's text (`parse_pdf.py`, using PyMuPDF), splits on blank lines
  into paragraphs, and greedily packs consecutive paragraphs into a chunk until the
  next one would push it over `max_tokens=300`. A single paragraph that's already
  bigger than that becomes its own (oversized) chunk rather than being cut mid-sentence
  — correctness of what gets cited matters more than hitting the token budget exactly
  at this stage.

**Tagging.** Each chunk also gets labelled with which "requirements" it satisfies —
e.g. "this chunk covers the DC-isolation safety procedure" or "this chunk covers the
corrective-measures for fault 37." This is what lets the selector (§5) later ask "do I
have evidence for everything this alarm legally needs?"

- Code: `src/suryasutra/ingest/tag.py`, `covers()`
- **How it decides**: keyword matching, not a trained classifier. Each requirement
  (defined in `config/requirements.yaml`) has a list of keyword phrases; if a chunk's
  text contains any of them (and matches the required `doc_type`), it's tagged with
  that requirement's id. Simple, fully inspectable, and — importantly for a safety
  product — a human can read the exact rule that produced a tag, rather than trusting a
  black box.
- **The gap we found the hard way (D-41)**: keyword matching alone is too coarse. The
  manual's one big fault table repeats boilerplate language ("disconnect the DC
  switch," "0.5 A," "Contact Sungrow Customer Service") across *many different, unrelated
  fault rows*. A plain keyword rule can't tell "this is the Boost Capacitor fault's own
  safety text" from "this is some other fault's safety text that happens to use the
  same words." Fixed by adding a second, required keyword group — `anchor_keywords_any`
  — so a chunk only counts if it *also* names the actual fault (e.g. "Boost Capacitor").
  This is the kind of thing a real production tagging system eventually needs: not just
  "does this text look relevant," but "is it relevant to *this specific* case."

---

## 4. Hybrid retrieval: finding candidate evidence for an alarm

**Concept.** Given an alarm's message ("Boost Capacitor Overvoltage Fault, code 370"),
find the ~40 chunks most likely to be useful, out of the whole manual. This is
*retrieval* — it doesn't decide what's safety-critical, it just narrows "everything" down
to "plausibly relevant," cheaply.

**Two different retrieval methods are combined, because they catch different things:**

### 4a. BM25 — lexical (keyword) search

**What it is.** A statistical scoring function — an improved version of TF-IDF — that
ranks documents by how well their *exact words* match the query, discounting common
words and rewarding rare, distinctive ones.

**Why.** If the alarm message literally says "Boost Capacitor Overvoltage Fault," BM25
will reliably find the manual's own row with that exact phrase. It's fast, needs no
model, and is excellent at exact/near-exact term matches.

**Where it falls short.** It only matches words, not meaning. "Inverter won't restart"
and the manual's "once a fault occurs, the fault information is displayed" mean related
things but share almost no words — BM25 misses this kind of paraphrase entirely.

- Code: `src/suryasutra/retrieval/bm25.py`, using the `rank_bm25` library.

### 4b. Dense retrieval — semantic (embedding) search

**What it is.** Every chunk of text is converted into a vector (a list of numbers,
384-dimensional here) by an embedding model, such that texts with *similar meaning*
end up as *nearby vectors* — regardless of exact wording. A query gets embedded the
same way, and the chunks whose vectors are closest (by cosine similarity) are
considered the best matches.

**Why.** This is what catches the paraphrase case BM25 misses — "won't restart" and
"fault information is displayed" can be close in meaning-space even with zero word
overlap.

**Model used**: `BAAI/bge-small-en-v1.5` (via `sentence-transformers`), a small,
CPU-friendly embedding model — chosen deliberately over a larger one so the prototype
doesn't need a GPU.

**Where it's built**: `src/suryasutra/retrieval/dense.py`. A FAISS flat index (exact
nearest-neighbour search, no approximation — fine at this corpus size of ~100 chunks;
a real fleet-scale deployment would swap in Qdrant, same interface, see `D-19`).

### 4c. Combining the two: Reciprocal Rank Fusion (RRF)

**The problem with just adding the scores together.** BM25 scores and cosine
similarities live on completely different, incomparable scales (BM25 might output 8.3,
cosine similarity is always between -1 and 1) — summing them directly would let
whichever metric happens to have bigger numbers dominate, for no principled reason.

**RRF's trick**: ignore the actual scores entirely, and only look at *rank position* —
"this chunk was #1 in BM25's list and #4 in dense's list." Each ranking contributes
`1 / (k + rank)` to a chunk's fused score (`k=60`, a standard damping constant), summed
across both rankings. Being ranked highly in *either* list counts; being ranked highly
in *both* counts more.

- Code: `src/suryasutra/retrieval/hybrid.py`, `reciprocal_rank_fusion()`
- `HybridRetriever.query()` runs both BM25 and dense search (40 candidates each),
  fuses them with RRF, and returns the top 40 fused results — these become the
  candidate pool the selector (§5) chooses from.

---

## 5. Budgeted evidence selection — the actual research contribution

This is the part the rest of the project exists to test. Retrieval (§4) gives you ~40
*plausible* chunks. Selection decides *which subset* actually goes into the LLM prompt,
under a hard token budget (so cost per alarm stays predictable). This is where
SuryaSutra differs from a generic RAG chatbot.

**The research question** (full version in CLAUDE.md §3): under a strict token budget,
does selecting evidence by *hard per-requirement coverage* — and refusing to answer
when that's infeasible — produce safer, more complete answers than picking chunks by
relevance alone?

### 5a. The naive approach (and why it's not good enough)

The obvious thing to do: rank candidates by relevance, keep adding the most-relevant
ones until the token budget runs out (`TopKSelector`,
`src/suryasutra/selection/baselines.py`). The problem: relevance ranking has no
concept of "this specific piece of information is *mandatory* for a safe answer." If
the budget runs out one chunk short of the safety procedure, top-k just silently drops
it — the answer still looks complete and confident, it's just missing the one thing
that matters most. Our own eval measured this directly: at a 500-token budget, top-k
drops at least one mandatory requirement in **41% of alarms** (`eval/results/summary.md`).

### 5b. `RequirementCompleteSelector` — hard coverage, then fill, then abstain if infeasible

**Concept.** Before optimizing for anything else, guarantee that every *mandatory*
requirement for this alarm's fault category (from `config/requirements.yaml`) is
covered by at least one selected chunk. If that's impossible — no evidence exists, or
it would blow the budget — **refuse to answer** and say exactly what's missing, instead
of answering with a gap.

**The algorithm** (`src/suryasutra/selection/requirement_complete.py`), four phases:

1. **Cover phase — greedy weighted set cover.** This is a classic computer-science
   problem: you have a set of "things that must be covered" (the mandatory
   requirements) and a collection of "items" (chunks), each covering some subset of
   those things, each with a cost (tokens). Find a small-cost collection of items that
   covers everything. Exact set cover is NP-hard, so a *greedy* approximation is used
   (provably within a `ln(n)` factor of optimal, a well-known result): repeatedly pick
   whichever remaining chunk covers the most *still-uncovered* requirements per token
   spent — `tokens / (newly_covered × relevance)` — until nothing is uncovered.
   Relevance is folded into the cost (not just token-efficiency) because, on real
   data, the cheapest chunk that technically matches a keyword tag is sometimes the
   *wrong* chunk (see D-41's cross-fault contamination story in §3).
2. **Feasibility check.** If some mandatory requirement has no chunk in the candidate
   pool that covers it at all → `INSUFFICIENT(reason="no_evidence")`. If the minimal
   covering set's token cost exceeds the budget → `INSUFFICIENT(reason="over_budget")`.
   **Mandatory evidence is never truncated to fit** — a partial safety answer is treated
   as no answer, not a safe one. This is the one non-negotiable rule of the whole
   project (`D-06`).
3. **Fill phase.** With whatever budget is left over, add more chunks — but *only*
   ones that cover one of this alarm's declared *optional* requirements, ranked by
   relevance-per-token. Never add untagged content just because it scored well on
   relevance — found necessary on real data (`D-32`): raw relevance scores don't
   reliably separate "actually about this alarm" from "coincidentally scored okay,"
   and a pure-relevance fill phase was pulling in things like unrelated app-install
   instructions. If a category has little optional content, the answer may use less
   than the full budget — that's fine; unused budget is not the failure mode this
   project cares about.
4. **Ordering.** Selected chunks are sorted safety-first, then cause/diagnosis, then
   procedure, then everything else, inferred from each chunk's requirement-id prefix
   (`safety_*`, `cause_*`, `corrective_measures_*`) — so the LLM sees safety
   information first, and the eventual answer naturally leads with it too.

**Baselines it's compared against** (same interface, `baselines.py`): `TopKSelector`
(pure relevance), `MMRSelector` (relevance + diversity penalty, no requirement
awareness), `KnapsackSelector` (0/1 knapsack on relevance alone), `SafetySlotSelector`
(RAGuard-style — reserves a fixed slot for "safety" content, but doesn't verify it's
*complete* for this specific alarm).

### 5c. What the eval actually measured (not claimed — measured)

From `eval/results/summary.md`, running all five selectors against 32 synthetic alarms
at three budgets, with zero LLM calls (this layer is pure local computation, so it's
free and reproducible — `python -m eval.run_eval`):

| Method | Full mandatory coverage (any budget) | Ever silently drops a requirement |
|---|---|---|
| `requirement_complete` | **75%** (the other 25% = correctly-abstained unanswerable alarms) | **0%** |
| `topk` / `mmr` / `safety_slot` | 59–69% | 31–41% |
| `knapsack` | 0–28% | 72–100% |

And **only `requirement_complete` ever abstains** — 100% precision and recall at
spotting the 8 deliberately-unanswerable alarms in the set, while every baseline
confidently answers all of them.

---

## 6. Generation: turning selected chunks into a cited answer

**Concept.** Once a selector returns `Answered(chunks)`, those chunks get turned into
a prompt, sent to an LLM, parsed back into structured JSON, and checked — the LLM
doesn't get free rein over the format or get trusted to cite correctly.

### 6a. Prompt construction

- Code: `src/suryasutra/generation/prompts/triage_prompt.py`, `build_prompt()`
- Each selected chunk gets a short citation id (`c1`, `c2`, ...) assigned in selection
  order (safety chunks first, per §5b step 4). The prompt lists every chunk's text
  next to its id and page range, and a system prompt instructs the model: respond in
  an exact JSON shape, cite every safety item and step with at least one given id,
  *never invent a citation id, never state anything the evidence doesn't support.*
- This is a deliberate design choice: the LLM is never asked to decide *what counts as
  evidence* — that already happened in selection. Its only job is turning
  already-vetted evidence into a readable, organized answer with citations attached.

### 6b. The LLM call

- Provider: **Groq**, model `openai/gpt-oss-120b` (chosen for low cost and speed —
  `config/pricing.yaml` records the per-token USD pricing, sourced from Groq's own
  docs, not guessed). `temperature=0` for determinism.
- The provider is behind an adapter interface (`src/suryasutra/generation/llm/base.py`,
  implemented by `groq_adapter.py`) — nothing outside that one file imports the `groq`
  SDK directly, so swapping providers later (e.g. for an on-prem/data-residency
  requirement) touches one file, not the whole codebase.

### 6c. Citation validation — the last line of defense

**Concept.** The model *might* hallucinate a citation anyway (cite `c7` when only `c1`
through `c5` were given, or state a step with no citation at all). This has to be
caught mechanically, not just hoped against.

- Code: `src/suryasutra/generation/validate.py`, `validate_citations()`
- Every safety item and step's citation set must be a non-empty subset of the ids
  that were actually given in the prompt. If anything fails this check, the whole
  generation is retried once (`max_retries=1` in `generate.py`); if it still fails,
  the system returns `INSUFFICIENT(reason="citation_validation_failed")` rather than
  silently shipping an answer with a broken citation.

---

## 7. End-to-end: one alarm, traced through every stage

Alarm: *"Inverter inv-04 raised fault code 370, Boost Capacitor Overvoltage Fault."*

1. **Ingestion (already done at startup)**: the manual's page 103 — which contains
   both the Boost Capacitor fault's corrective text *and* the shared DC-isolation
   safety sequence — got tagged with `safety_dc_isolation_sequence` and
   `corrective_measures_boost_capacitor`.
2. **Retrieval**: the alarm message is embedded and BM25-searched; page 103's chunk
   ranks highly in both rankings (it literally contains "Boost Capacitor Overvoltage
   Fault"), so RRF fusion puts it near the top of the ~40 candidates.
3. **Selection**: `boost_capacitor_overvoltage_fault`'s fault category (from
   `config/requirements.yaml`) declares `must: [safety_dc_isolation_sequence]`. The
   cover phase finds page 103's chunk covers it, cheaply and relevantly — selected.
   Feasible and under budget → `Answered`. Fill phase adds the optional
   `corrective_measures_boost_capacitor`-tagged content if budget allows.
4. **Generation**: the prompt lists that evidence with citation id `c1`; Groq returns
   JSON with a safety item, likely causes, and numbered steps, each citing `c1`.
5. **Validation**: `c1` is in the valid id set — passes.
6. **Response**: `AnsweredContract` — safety box, causes, steps, `sources["c1"]` (so
   the UI's citation chip can show you the actual page-103 text) — with real token
   counts and a real ₹ cost, logged to the `usage` table.

---

## 8. Glossary — the ML/NLP terms used above

- **Tokenization / tokens**: the units an LLM actually processes (not quite words —
  roughly 4 characters of English on average). "Token budget" means a cap on how much
  evidence text can go into one prompt, which directly controls per-alarm LLM cost.
- **Embedding**: a fixed-length vector representation of text such that semantically
  similar text produces similar vectors. The whole basis of "dense"/semantic retrieval.
- **Cosine similarity**: a measure of how similar two vectors' *directions* are
  (ignoring magnitude) — the standard way to compare embeddings.
- **BM25 / TF-IDF**: lexical ranking functions that score documents by matching
  *exact terms*, weighted so rare/distinctive words count more than common ones.
- **Reciprocal Rank Fusion (RRF)**: a scale-free way to combine multiple ranked lists
  by rank position alone, avoiding the apples-to-oranges problem of combining
  differently-scaled scores.
- **Greedy algorithm / set cover**: an algorithm that makes the locally-best choice at
  each step without backtracking. Used here because exact optimal set cover is
  NP-hard, and the greedy approximation has a known, provable bound on how far it can
  be from optimal.
- **Temperature (LLM)**: a generation-randomness knob; `0` makes output (close to)
  deterministic — important for reproducible eval runs.
- **Hallucination**: an LLM stating something not actually supported by its given
  evidence — the entire reason the citation validator (§6c) exists.
- **RAG (Retrieval-Augmented Generation)**: the general pattern of "retrieve relevant
  text, then have an LLM generate an answer grounded in it" — SuryaSutra is a RAG
  system with a non-standard, hard-constrained selection layer in the middle, which is
  the part under research here.

---

## 9. Where to look for more

- `docs/DECISIONS.md` — every non-obvious choice above, with the real alternative
  considered and why it was rejected (search for D-06, D-07, D-20, D-32, D-38, D-41 for
  the ones referenced here).
- `eval/` — the actual measurement code and results referenced in §5c.
- `config/requirements.yaml` — the real requirement definitions and fault categories
  driving §5's selection logic.
