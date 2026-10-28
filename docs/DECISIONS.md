# SuryaSutra — Decision Log

> Place at `docs/DECISIONS.md`. One entry per decision. Never delete an entry; supersede it with a new one.
> Status values: **Accepted**, **Provisional** (to revisit at a named trigger), **Superseded by D-xx**, **Rejected**.
> Date format: YYYY-MM-DD. All entries below were made on 2026-10-19 unless stated.

## Template

```
### D-xx: <title>
- Status:
- Context: what problem or question forced the decision
- Decision: what we chose
- Alternatives considered: and why not
- Consequences: what this commits us to / costs
- Revisit when: the trigger that would reopen it
```

---

## A. Problem & product

### D-01: Pivot from a pure research idea (FAEB) to an industry product with a research core
- Status: Accepted
- Context: Phase 1 literature review found token-budgeted, redundancy-aware selection (MMKP, submodular packing, budget-aware routing) and safety-slot retrieval (RAGuard) already published. FAEB as a novelty claim did not survive.
- Decision: Build SuryaSutra, a solar O&M alarm copilot, whose research core is the surviving idea: hard mandatory-evidence coverage + infeasibility-triggered abstention under a token budget.
- Alternatives: (a) Publish FAEB as-is — likely rejected as incremental. (b) Benchmark-only paper — kept as fallback. (c) Unrelated topic — wastes completed review.
- Consequences: Product and paper share code; research claims must stay narrow and honest.
- Revisit when: Pilot E0 shows mandatory evidence is rarely dropped at realistic budgets.

### D-02: Target market = O&M of Indian utility-scale and large C&I solar plants
- Status: Provisional
- Context: Compared three startup directions: O&M alarm copilot, renewable tender copilot, open-access regulatory copilot.
- Decision: O&M alarm copilot.
- Alternatives: Tender copilot — horizontal Indian tender-AI players already exist (e.g., Minaions, Arched). Open-access copilot — free calculators exist (CEEW, SurgePV), weaker willingness to pay; kept as second option. Residential rooftop consumer assistant — no clear payer.
- Consequences: Enterprise sales cycles; need a pilot plant partner for real data.
- Revisit when: After 10–15 customer interviews, if O&M managers don't confirm alarm triage as a top-3 pain.

### D-03: The product recommends; humans act
- Status: Accepted
- Context: Electrical safety and liability.
- Decision: No autonomous equipment control; read-only data access; explicit disclaimer in UI.
- Alternatives: Autonomous agents executing resets (some global startups move this way) — liability and trust risk for an early-stage company.
- Consequences: Simpler compliance story; value must come from triage speed and quality.
- Revisit when: A customer explicitly requests and contracts for supervised automation.

### D-04: "Token economy" means LLM token budgeting and cost per query — not crypto
- Status: Accepted
- Context: Ambiguous term in early project framing.
- Decision: Tokens = LLM tokens. Core business metric = cost per alarm; core research variable = context budget B.
- Alternatives: Blockchain incentive tokens — no defensible need identified.
- Consequences: Must log tokens and cost on every run.
- Revisit when: Never, unless a separate, justified need appears.

### D-05: Name = SuryaSutra
- Status: Provisional
- Context: Needs an India-rooted, brandable name that also works as a paper system name.
- Decision: "SuryaSutra" (sun + concise guiding rule).
- Alternatives: AlarmSetu, Raksha O&M, TokenTriage, PlantPocket.
- Consequences: Must check domain, GitHub org, and trademark conflicts ("Surya" is common in Indian solar).
- Revisit when: Trademark search shows a conflict.

## B. Research design

### D-06: Mandatory evidence is a hard constraint, never a weight
- Status: Accepted
- Context: A weighted "safety bonus" in a knapsack can still drop long safety passages.
- Decision: Cover all mandatory requirements first; if impossible within B, return INSUFFICIENT.
- Alternatives: Weighted utility (FAEB original); fixed safety slots (RAGuard) — neither guarantees per-requirement coverage.
- Consequences: Some alarms will get "insufficient" instead of an answer; abstention quality must be evaluated.
- Revisit when: Never relaxed for safety requirements.

### D-07: Requirements come from a reviewed schema per fault category
- Status: Provisional
- Context: Need per-alarm list of mandatory evidence.
- Decision: `config/requirements.yaml` mapping fault categories → must/optional requirements, with tagging rules; `review_status` field.
- Alternatives: LLM-generated requirements per query — unvalidated, non-deterministic. Fully learned classifier — no labelled data yet.
- Consequences: Reviewers may call it hand-crafted; mitigate by expert review, inter-annotator agreement, and an ablation (expert vs LLM-generated schema).
- Revisit when: Enough labelled data exists to train/validate a requirement tagger.

### D-08: Greedy set cover as the default, ILP as the exactness check
- Status: Accepted
- Context: Selection is budgeted set cover + fill (NP-hard in general) but candidate pools are small (~40).
- Decision: Greedy (tokens per newly covered requirement) in production; ILP (OR-Tools/PuLP) in experiments to measure the optimality gap.
- Alternatives: ILP everywhere — fine at this size but adds solver dependency to the hot path; learned selectors — no training data.
- Consequences: Must report greedy vs ILP gap.
- Revisit when: Gap is material or pool sizes grow.

### D-09: Baselines = TopK, MMR, relevance knapsack, RAGuard-style safety slots
- Status: Accepted
- Context: Reviewers will ask about the strongest practical comparators.
- Decision: Implement all four behind one selector interface; add a compression baseline (e.g., LLMLingua-family) if time permits.
- Alternatives: Compare only to top-k — too weak to be convincing.
- Consequences: More implementation work; cleaner paper.
- Revisit when: A newer strong selector is published with code.

### D-10: Pilot study (E0) gates the paper
- Status: Accepted
- Context: If baselines rarely drop mandatory evidence, the method has nothing to fix.
- Decision: Run E0 on the prototype eval set at budgets 500/1000/2000 before claiming anything.
- Alternatives: Build full system first — risks investing in a non-problem.
- Consequences: Results may redirect the paper to benchmark/analysis.
- Revisit when: E0 results are in.

### D-11: No fabricated numbers anywhere
- Status: Accepted
- Context: Investor and academic credibility.
- Decision: All results come from logged runs; unmeasured values show "TBD"; synthetic data always labelled.
- Alternatives: none acceptable.
- Consequences: The demo may look less flashy early on.
- Revisit when: Never.

## C. Data

### D-12: Prototype data = one public inverter manual + NREL O&M guide + synthetic alarms/work orders
- Status: Provisional
- Context: No plant partner yet; need to demo in 3–4 days.
- Decision: Use one brand's public manual and fault-code table locally; NREL "Best Practices for O&M of PV and Energy Storage Systems, 3rd ed." for safety/procedure text; generate synthetic alarms and work orders.
- Alternatives: Wait for real data — blocks progress. Multi-brand — too slow to parse.
- Consequences: Results are indicative only; LLMs may have seen public manuals in pretraining (include a no-retrieval baseline).
- Revisit when: A pilot plant shares anonymised logs.

### D-13: Do not redistribute vendor manuals
- Status: Accepted
- Context: Vendor documents are copyrighted.
- Decision: Commit a download script + SHA-256 hashes, not PDFs; chunks/indices gitignored.
- Alternatives: Commit PDFs — licensing risk.
- Consequences: Reproducibility relies on vendors keeping documents online; record versions/hashes.
- Revisit when: A vendor grants redistribution rights.

### D-14: Eval set is hand-labelled, with deliberately unanswerable items
- Status: Accepted
- Context: Need ground truth for coverage and abstention.
- Decision: 30–40 alarms (prototype), ~20% unanswerable; gold cause(s) and gold mandatory chunks labelled by the founder, then reviewed by a qualified electrical/PV person before publication.
- Alternatives: LLM-generated eval — known to inflate results and bias evaluation.
- Consequences: Small n → report confidence intervals; expand in pilot.
- Revisit when: Pilot provides real resolved work orders as labels.

## D. Architecture & stack

### D-15: Modular monolith (single FastAPI service), not microservices
- Status: Accepted
- Context: One developer, prototype stage.
- Decision: One backend service with clean module boundaries (ingest, retrieval, selection, generation, triage, usage, api).
- Alternatives: Microservices — operational overhead with no benefit at this scale.
- Consequences: Split later only along proven load boundaries.
- Revisit when: Independent scaling needs appear (e.g., ingestion workers).

### D-16: Python + FastAPI backend
- Status: Accepted
- Context: ML/NLP ecosystem is Python; need typed, documented API.
- Decision: FastAPI + Pydantic v2.
- Alternatives: Node/Express (founder knows MERN) — weaker NLP ecosystem; Django — heavier than needed.
- Consequences: Two languages in the repo (Python + TypeScript).
- Revisit when: No trigger expected.

### D-17: React + Vite + TypeScript frontend
- Status: Accepted
- Context: Founder knows React; need a fast, demo-quality UI.
- Decision: React 18, Vite, TypeScript, Tailwind, TanStack Query, Recharts.
- Alternatives: Streamlit — fastest but looks like a prototype to investors and limits UX; Next.js — SSR not needed.
- Consequences: Slightly more setup than Streamlit.
- Revisit when: A mobile app is needed (consider React Native/PWA).

### D-18: SQLite now, Postgres for pilot, same ORM
- Status: Accepted
- Context: Zero-setup locally vs multi-tenant production.
- Decision: SQLAlchemy 2.0 + Alembic; switch via `DATABASE_URL`.
- Alternatives: MongoDB (founder knows it) — relational data (runs, usage, tenants) and SQL analytics fit Postgres better.
- Consequences: Avoid SQLite-only features.
- Revisit when: First multi-user deployment.

### D-19: FAISS now, Qdrant for pilot, behind a VectorStore interface
- Status: Accepted
- Context: Small corpus now; filtering, persistence and multi-tenancy later.
- Decision: FAISS flat index for prototype; Qdrant (payload filters by tenant/brand/doc type) for pilot.
- Alternatives: pgvector — viable, keeps one database; reconsider if ops simplicity matters more than filtering features. Managed vector DBs — cost and data-residency questions.
- Consequences: Interface must support metadata filters from day one.
- Revisit when: Corpus > ~1M chunks or pgvector proves sufficient in benchmarks.

### D-20: Hybrid retrieval (BM25 + dense)
- Status: Accepted
- Context: Fault codes and part numbers are exact strings (BM25 strength); symptoms are paraphrased (dense strength). Prior work on manual-based fault diagnosis found plain retrieval strong for code matching.
- Decision: Weighted/RRF fusion of BM25 and `bge-small-en-v1.5`; metadata filters by brand/model.
- Alternatives: Dense-only — misses exact codes; BM25-only — misses paraphrase.
- Consequences: Two indices to maintain.
- Revisit when: Eval shows one component adds nothing.

### D-21: LLM behind a provider adapter; model chosen by config
- Status: Accepted
- Context: Costs, availability and data-residency needs differ by customer; research needs model comparisons.
- Decision: Adapters for Anthropic, Gemini, Groq and local Ollama; provider/model in `.env`; temperature 0 for eval.
- Alternatives: Hard-code one provider — lock-in, blocks experiments.
- Consequences: Must normalise usage/token fields across providers.
- Revisit when: A customer mandates on-prem only (prioritise local models).

### D-22: Token counts from provider usage fields are ground truth
- Status: Accepted
- Context: Tokenizers differ by model; cost accuracy matters.
- Decision: Record provider-reported input/output tokens; use `tiktoken` (or model tokenizer) only for pre-generation budgeting, and flag estimates as such.
- Alternatives: One tokenizer for everything — wrong for non-OpenAI models and Indic text.
- Consequences: Budget B is approximate pre-call; report both planned and actual.
- Revisit when: Provider exposes a counting API we can call cheaply pre-generation.

### D-23: Structured JSON answers + citation validator
- Status: Accepted
- Context: Uncited steps are unsafe and unauditable.
- Decision: LLM must return the answer schema; validator rejects any step/safety item without a citation to a selected chunk; one retry, then INSUFFICIENT.
- Alternatives: Free-text answers — impossible to verify automatically.
- Consequences: Slightly higher output tokens; much better auditability.
- Revisit when: No trigger expected.

### D-24: English-only in prototype; Indic answers in pilot
- Status: Provisional
- Context: Indic scripts cost several times more tokens under common tokenizers; adds evaluation burden.
- Decision: Ship English first; design usage logging to support language-aware budgets later.
- Alternatives: Hindi/Tamil from day one — more impressive, but doubles eval work in a 4-day sprint.
- Consequences: Must not claim multilingual support until evaluated.
- Revisit when: M7 / first partner requests local-language answers.

## E. Engineering practice

### D-25: Tests on selector invariants are mandatory, including property-based tests
- Status: Accepted
- Context: The selector is the safety-critical core.
- Decision: pytest + Hypothesis: never exceed B; never answer with uncovered mandatory requirement; deterministic output; plus a safety regression suite.
- Alternatives: Example-based tests only — miss edge cases.
- Consequences: Slower first implementation; far fewer silent failures.
- Revisit when: Never relaxed.

### D-26: Every experiment run is reproducible and logged
- Status: Accepted
- Context: Paper and investor claims must be traceable.
- Decision: Results JSON includes config, model + embedding versions, budget, method, seed, git commit hash.
- Alternatives: Notebook-only experiments — hard to reproduce.
- Consequences: Small overhead per run.
- Revisit when: Never.

### D-27: Docker Compose for one-command demo; GitHub Actions CI
- Status: Accepted
- Context: Investors and reviewers must be able to run it; regressions must be caught.
- Decision: `docker compose up` starts API + web (+ Qdrant/Postgres in pilot); CI runs lint, type-check, tests and an eval smoke test.
- Alternatives: Kubernetes — premature.
- Consequences: Keep images small; pin versions.
- Revisit when: Multi-customer hosting.

### D-28: Separate research code from application code
- Status: Accepted
- Context: Research modules must stay pure and testable; app code changes often.
- Decision: `selection/`, `retrieval/`, `eval/` never import from `api/` or `web/`.
- Alternatives: Single mixed codebase — experiments break when the app changes.
- Consequences: Clear interfaces; slightly more boilerplate.
- Revisit when: Never.

## F. Go-to-market (provisional, to validate)

### D-29: Validate with customer interviews before building pilot features
- Status: Accepted
- Context: Pain, buyer and pricing are hypotheses.
- Decision: Interview 10–15 O&M managers/site engineers (Tamil Nadu, Rajasthan, Gujarat) after the prototype exists; record learnings in `docs/customer_interviews.md`.
- Alternatives: Build first, sell later — high risk of building the wrong thing.
- Consequences: Feature roadmap driven by interview evidence.
- Revisit when: After interviews.

### D-30: Pricing hypothesis = per-MW per-year SaaS
- Status: Provisional
- Context: O&M budgets are typically expressed relative to plant capacity; cost per alarm is our internal margin driver.
- Decision: Test per-MW/year pricing in interviews; no price stated publicly until validated.
- Alternatives: Per-seat, per-alarm usage pricing.
- Consequences: Need cost-per-alarm data to set a floor.
- Revisit when: After first 5 pricing conversations.

## G. Session start (2026-10-19)

### D-31: First inverter brand for prototype data = Sungrow (model SG150CX)
- Status: Accepted
- Context: D-12 requires picking one brand with a public manual + fault-code table to seed ingestion. No plant partner yet. Founder confirmed: pick whichever brand is actually used in India and has public documentation.
- Decision: Sungrow SG150CX string inverter. Verified: (1) Sungrow leads India's utility-scale inverter market — ~50%+ share of central inverters, ~20% of string inverters, per JMK Research 2025 data; (2) the SG150CX user manual is public, no-login, downloaded successfully (118 pages); (3) it contains a real §9 "Troubleshooting and Maintenance" section (pages 96–110) with a Fault Code / Fault Name / Corrective Measures table plus DC-isolation / DANGER / CAUTION safety blocks — exactly the mandatory-evidence shape D-06 needs.
- Alternatives: TBEA (actually #1 in Indian string-inverter shipments) or Solis — not checked for manual availability, Sungrow's was confirmed working first and its central-inverter lead is larger. Huawei, ABB/FIMER, Delta — not checked.
- Consequences: Fault-code table, requirement schema examples, and synthetic alarms in the prototype reference Sungrow/SG150CX terminology; switching brands later means re-tagging requirements. Hash recorded in `data/raw/checksums.sha256`, source metadata in `data/raw/SOURCES.md`.
- Revisit when: A real plant partner's actual inverter brand is known, or the founder prefers a different brand.

### D-32: Fill phase gated by declared optional requirements, not raw relevance score
- Status: Accepted
- Context: Live-verifying `RequirementCompleteSelector` against the real manual (not just unit tests) surfaced a real failure: the fill phase, specified in CLAUDE.md §6 step 3 as "add chunks by relevance/tokens," pulled in genuinely unrelated content (iSolarCloud app-install instructions) as filler, because on real RRF-fused retrieval scores, irrelevant chunks don't score low enough relative to the best match for any relevance threshold to reliably separate them — RRF scores decay gently with rank (`1/(60+rank)`) and mostly encode order, not degree of relevance. A tried relative-relevance floor (0.3× the pool's max) did not exclude the bad case; raising the threshold further would be tuning against one example with no labelled data to check it against (exactly what D-10 warns against).
- Decision: The fill phase now only adds candidates that cover at least one of the alarm's own declared `optional` requirement ids (`chunk.covers & optional`). Untagged content is never eligible as filler, regardless of relevance score. This also updates the cover phase's cost function from `tokens / newly_covered` to `tokens / (newly_covered * relevance)` (D-06's hard mandatory-coverage guarantee is unaffected — this only changes which valid covering chunk is picked when several exist).
- Alternatives considered: (a) keep tuning the relevance-floor fraction — rejected, tuning-by-vibes without eval data. (b) rank-cutoff on retrieval position instead of score — simpler patch, considered but less principled (still trusts "rank = relevance," arbitrary K to pick). (c) drop the fill phase entirely, answer with only the mandatory cover — rejected, would waste available budget on alarms with useful optional content (most troubleshooting pages carry `corrective_measures_present`).
- Consequences: Every chunk in a final answer — mandatory or optional — now has an explicit, nameable reason for being there (strengthens the citation/audit story, D-23). Answers may use less than the full budget B when a fault category's `optional` list is sparse (ours mostly have 0-1 optional ids right now) — this is treated as acceptable, not a defect; unused budget is not the failure mode D-06 cares about. CLAUDE.md §6 step 3's description should be read as superseded by this decision.
- Revisit when: `config/requirements.yaml` grows richer optional-requirement coverage (making the fill phase more consistently useful), or eval data (M5) shows budget is being left on the table in cases where it clearly shouldn't be.

## H. Generation, API and persistence (M3–M5, DB layer)

### D-33: LLM provider = Groq, model = openai/gpt-oss-120b
- Status: Accepted
- Date: 2026-10-21
- Context: D-21 already decided to keep the LLM behind a provider-agnostic adapter; M3 needed a first real provider to build and test against. Founder chose Groq (fast, cheap inference) and had a key ready.
- Decision: `GroqAdapter` behind `LLMAdapter`. Model `openai/gpt-oss-120b` (131K context) — pricing and model id verified directly from Groq's own docs (console.groq.com/docs/model/openai/gpt-oss-120b), not a third-party aggregator: $0.15/$0.60 per million input/output tokens, recorded with source URLs and a dated USD→INR rate in `config/pricing.yaml`.
- Alternatives: `gpt-oss-20b` (cheaper, smaller) — kept as a documented alternative in `pricing.yaml`, not used by default; quality/context tradeoff favoured the larger model for this prototype's safety-critical structured output.
- Consequences: `GROQ_API_KEY` required in `.env` for any live generation; `tests/integration/test_groq_live.py` skips cleanly without it. Caught and fixed a real near-miss during this work: the key was twice pasted into the *tracked* `.env.example` template instead of the gitignored `.env` — fixed before anything was staged or committed both times, never pushed.
- Revisit when: A customer needs on-prem/data-residency (D-21 already flags this — prioritise Ollama then), or Groq pricing/availability changes materially.

### D-34: Answer contract extended with a `sources` field
- Status: Accepted
- Date: 2026-10-21
- Context: Building the React triage view (M4) surfaced that CLAUDE.md §10's original JSON contract gave the frontend citation ids (`c1`, `c2`, ...) with nothing to resolve them to — "click a citation → see the source page" (§11) was impossible against the documented contract as written, since citation ids are opaque per-request strings, not stable chunk DB ids.
- Decision: Added `sources: dict[citation_id, {page_start, page_end, text}]` to `AnsweredContract`, populated in `generate_triage_answer()` from the same citation map the prompt itself uses. CLAUDE.md §10 updated to match. Purely additive — nothing existing changed shape.
- Alternatives: Give chunks stable DB ids and have the frontend fetch pages via a separate endpoint — rejected for now, since chunks aren't persisted to a DB at all yet (D-35 below); would have pulled forward DB work that wasn't needed for this.
- Consequences: Every citation chip in the UI can show real source text without a second round trip. Answer payloads are somewhat larger (full chunk text repeated per citation) — not yet a problem at prototype scale.
- Revisit when: Chunks get persisted with stable ids (if `documents`/`chunks` tables are ever built) — `sources` could then shrink to id + page, with text fetched on demand.

### D-35: DB layer scoped to `alarms`, `triage_runs`, `usage`, `feedback` — not `documents`/`chunks`/`requirements`
- Status: Accepted
- Date: 2026-10-22 (initial `alarms`/`triage_runs`/`usage`); `feedback` added 2026-10-24
- Context: CLAUDE.md §9 declares seven tables. Building all of them — including wiring `documents`/`chunks`/`requirements` persistence into the ingestion pipeline, which currently rebuilds the whole corpus in memory from the PDF + YAML at every process startup (D-15) — was a materially larger undertaking than "add persistence so triage history is queryable," which was the actual, scoped ask. `feedback` was deferred initially (not needed until `POST /feedback` was actually built) and added once that endpoint was.
- Decision: SQLAlchemy models + Alembic migrations for `alarms`, `triage_runs`, `usage`, `feedback` (CLAUDE.md §9's field lists, unchanged). `documents`/`chunks`/`requirements` stay file- and config-based. Migrations run programmatically at app startup (`alembic upgrade head` via `suryasutra.db.migrate.run_migrations()`) rather than as a separate deploy step — acceptable at prototype/SQLite stage, explicitly flagged as a thing to change before a real Postgres deploy. `feedback` has its own surrogate `id` (not just `run_id` as a key) since a run can legitimately receive more than one feedback entry over time (e.g. a technician marks it, a supervisor reviews it later).
- Alternatives: Build the full seven-table schema now — rejected, no current feature needs `documents`/`chunks` as DB rows (retrieval already works fine in-memory), and persisting them would mean deciding `embedding_ref`'s actual storage format with no real use case yet to validate the design against.
- Consequences: `GET /runs/{id}`, `GET /stats/usage`, and `POST /feedback` all work on real data. Ingestion still has no DB write path at all — adding the remaining three tables later means a further migration and real integration work with the ingestion CLI, not just more model classes.
- Revisit when: Multi-document or multi-tenant support actually matters (pilot stage, D-19), or the dashboard/eval work needs to query chunks by id instead of rebuilding the corpus each time.

### D-36: Retrieval embeddings fix — `DenseIndex.embedding_for()`
- Status: Accepted
- Date: 2026-10-22
- Context: While building the M5 eval runner, found that `HybridRetriever.query()` had never actually attached embeddings to its results — every real `Candidate` built from retrieval (the live API included, not just eval) had `embedding=None`, silently disabling `MMRSelector`'s diversity penalty and `RequirementCompleteSelector`'s near-duplicate dedup for the entire session up to that point. Existing unit tests all passed because they used hand-built fixtures with explicit embeddings, which masked the gap — nothing exercised the real retrieval→selection path with real embeddings until the eval run's MMR results looked suspiciously identical to TopK's.
- Decision: `DenseIndex` now keeps a `{chunk: embedding}` map built once at construction (every corpus chunk is already embedded for the FAISS index, so this is free) and exposes `embedding_for(chunk)`. `HybridRetriever.query()` attaches it to every result regardless of whether that chunk came from the BM25 ranking, the dense ranking, or both. Both callers (`api/main.py`, `eval/run_eval.py`) updated to pass it through to `Candidate`.
- Alternatives: Re-embed retrieved chunk text on demand in each caller — rejected, duplicates computation the `DenseIndex` already did at construction time for no benefit.
- Consequences: MMR and the selector's dedup are now actually functional in the running system, not just in selector-level unit tests. The M5 eval was re-run after this fix (both runs logged in `eval/results/`, not just the corrected one kept quietly) — MMR's numbers changed from the first run; `RequirementCompleteSelector`'s core guarantee (0% answered-incomplete) did not, since it never depended on the dedup feature for correctness.
- Revisit when: Never relaxed — this is a correctness fix, not a tunable.

### D-37: Gold eval labels drafted by the AI system, with explicit provenance tracking — D-14's independence bar not yet met
- Status: Accepted (provisional — see Consequences)
- Date: 2026-10-24
- Context: `eval/gold_labels.py` (D-14's tooling) was built to deliberately never pre-fill gold values, precisely so the eval isn't self-graded by the system being evaluated. The founder was told this plainly, then explicitly asked the system to draft the actual values anyway (chat request: "I want you to check each and every and fill all the things on my behalf since you know the project better") — a conscious tradeoff of speed against D-14's original independence guarantee, made by the founder with the tradeoff stated up front, not a silent shortcut.
- Decision: Drafted all 10 answerable alarms' `gold_causes`/`gold_mandatory_pages`/`gold_step_checklist` from a fresh, direct re-read of the manual's pages 96-110 (not memory, not copied from `config/requirements.yaml`). Added a `drafted_by` field to `GoldLabelSet` (machine-checkable, not just a comment) stating plainly this is an AI-assisted draft, not independently human-verified. `review_status` stays `unreviewed`. Added a test (`test_real_gold_labels_file_is_marked_ai_drafted_not_reviewed`) that fails if this provenance marker is ever silently dropped or changed to imply verification happened when it didn't.
- Alternatives: Refuse outright and insist only the founder write it — rejected as unhelpfully rigid once the founder understood and accepted the tradeoff explicitly; this isn't a case of hiding a shortcut, it's a documented one. Silently comply without flagging the methodological cost — rejected, would have let a self-graded eval quietly pass as if it met D-14.
- Consequences: Any generation-level metric computed against this file (once that code exists) is **not yet a valid research result** — it is checking the system against a draft written by the same author, exactly the circularity D-14 was designed to prevent. The "Status: Accepted" above refers to the tooling/provenance-tracking decision, not to treating this draft's content as settled ground truth. The actual labels still need a real review pass (minimum: founder reads the draft against the manual and corrects it; ideally, per D-14's original bar, a qualified electrical/PV person signs off) before anything derived from them appears in a paper or investor material.
- Revisit when: The founder (or a qualified reviewer) has actually gone through `data/eval/gold_labels.yaml` against the manual and corrected it — at that point, update `drafted_by` to record who reviewed it and reconsider `review_status`.
- **Update, 2026-10-25**: The founder did this — went through the draft against the manual and confirmed it correct. `review_status` changed from `unreviewed` to `founder_reviewed` (not plain `reviewed`, which would overclaim D-14's full bar); `drafted_by` now records both the original AI draft and the founder's confirmation, and still names the qualified-electrical/PV-person review as the remaining step before publication. Test renamed/updated (`test_real_gold_labels_file_reflects_founder_review_not_full_publication_bar`) to assert `review_status` is neither `unreviewed` nor a bare `reviewed` — it must land exactly on `founder_reviewed` so the intermediate state can't be silently read as fully done. D-14's independence concern this decision was about is now resolved to the extent a founder-only org can resolve it; the qualified-person sign-off is still open and tracked in `drafted_by`'s own text, not just here.

### D-38: Generation-level eval metrics are transparent keyword-overlap heuristics, not an LLM judge — citation precision left unimplemented
- Status: Accepted
- Date: 2026-10-25
- Context: CLAUDE.md §12 calls for cause accuracy, step correctness (rubric), and citation precision at the generation level, checked against `data/eval/gold_labels.yaml` (founder_reviewed as of D-37). The obvious shortcut — have an LLM grade the triage LLM's own output — just relocates the self-grading problem D-14 exists to prevent, one level up.
- Decision: `eval/generation_metrics.py` implements three functions. `gold_page_recall()` is fully mechanical (set overlap between cited pages and gold mandatory pages — no judgment call). `cause_match()` and `step_checklist_coverage()` are explicit keyword-overlap heuristics (stopword-filtered token intersection against a tunable threshold, default 0.4) — documented in the module and every function's own docstring as approximate, not semantic judgment, so nothing downstream can mistake a heuristic number for a rubric pass. "Citation precision" (does the cited chunk's text actually *support* the specific claim, not just share keywords with it) is deliberately **not implemented** — faking it with keyword overlap would be more misleading than leaving it as an open item.
- Alternatives considered: (a) LLM-judge pass for all three metrics — rejected per the self-grading concern above, though CLAUDE.md §12 itself doesn't rule this out for a later, more rigorous pass with a separate judge model and disclosed methodology. (b) Exact-string matching against the gold checklist — rejected, gold_step_checklist is deliberately paraphrased content ("exact wording doesn't need to match, the content does," per `gold_labels.py`'s own template header), so exact match would undercount correct answers trivially.
- Consequences: The heuristic has a known, demonstrated failure mode — exact-token matching doesn't catch word-form variants (e.g. "restart" vs "restarting"), confirmed by a dedicated test (`test_step_checklist_coverage_misses_word_form_variants`) that exists specifically so this limitation stays visible rather than hidden by only ever testing identical wording. Any number produced by `cause_match`/`step_checklist_coverage` should be read as a fast directional signal for iteration, not a substitute for a human rubric pass — restated in `eval/run_generation_eval.py`'s own summary output so it travels with the numbers, not just in source comments.
- Revisit when: Citation precision actually needs measuring for a real result (would need a human read-through or a carefully-flagged, separately-disclosed LLM-judge pass — not this heuristic approach), or the keyword heuristic's miss rate on word-form variants proves large enough on real eval data to justify adding basic stemming.

### D-39: `GroqAdapter` retries on rate-limit errors instead of failing the whole eval run
- Status: Accepted
- Date: 2026-10-25
- Context: Running `eval/run_generation_eval.py` for real (36 live Groq calls across 3 budgets) hit Groq's free-tier tokens-per-minute cap (8000 TPM) partway through the largest-budget runs — a real, expected constraint of the cheap-provider tradeoff D-33 already made, not a code bug. The first failure was a plain read timeout (likely the same underlying congestion); the second was an explicit `groq.RateLimitError` with a `Retry-After` header. Without handling this, a multi-call batch eval can never complete past whatever call happens to land when the TPM window is full.
- Decision: `GroqAdapter.generate()` now catches `groq.RateLimitError` and retries (up to `max_rate_limit_retries`, default 5), sleeping for the server's own `Retry-After` header value (+1s buffer) when present, else a fixed 10s guess. Other exceptions (including plain timeouts) are not caught here — they surface as before, since silently retrying everything would risk masking a real persistent failure.
- Alternatives considered: (a) Rate-limit the eval script's own call rate proactively (e.g. a fixed delay between calls) — simpler but either over-throttles (wasting time when under the limit) or under-throttles (still fails occasionally); reactive backoff on the server's actual signal is more accurate. (b) Catch-and-retry at the eval-script level instead of the adapter — rejected, the live API (`/triage`) hits the exact same rate limit under real fleet load and deserves the same resilience, not a eval-only patch.
- Consequences: The full 3-budget generation eval (36 calls) completed successfully after this fix, split across two runs (500/1000 in the first, 2000 retried separately after the fix) — see `eval/results/summary_generation.md`. The live `/triage` endpoint also benefits from this resilience now, not just the eval script.
- Revisit when: Rate limits recur often enough in real usage to warrant a Dev Tier upgrade (Groq's own suggestion in the error message) rather than retrying around the free tier's cap.

### D-45: New planning docs (PRD/TRD/APP_FLOW/DESIGN_BRIEF/BACKEND_SCHEMA) adopted; design-system reskin of existing screens is the first slice built
- Status: Accepted
- Date: 2026-10-28
- Context: Founder supplied five new, cross-referenced planning documents describing a substantially larger product vision than what's built — a full design system (dark "control room" theme: midnight/lime/cobalt, Instrument Serif/Inter/JetBrains Mono, Motion animation library, Radix UI, Lucide icons), a public landing page, a 10-table multi-tenant DB schema (work orders, past-fixes reuse, DB-tracked eval, run-candidate traces), and new screens (source viewer panel, run trace replay, document upload UI). None of this existed yet; the gap to the already-built research core (retrieval/selection/generation/abstention, which matches this vision closely) and the then-current UI (the light/dark amber theme from D-44) was large. Given CLAUDE.md's "small increments, never a large codebase in one go" rule and its "ask before new dependencies" rule, the full scope was not attempted at once.
- Decision: (1) Committed all five docs to `docs/` as the new planning baseline, alongside `CLAUDE.md` (not replacing it). (2) Resolved a direct conflict between D-44 (explicit "light by default, dark toggle") and the new `DESIGN_BRIEF.md` ("dark theme is default, light is the secondary Field-mode toggle") by asking — founder chose dark-by-default, superseding D-44's default (the toggle itself, and both palettes, are kept). (3) Scoped the first implementation slice to a pure design-system reskin of the four already-working screens (alarm queue, triage view, compare mode, dashboard) — new colors/typography/icons/motion only, explicitly no new features, no DB changes, no landing page. New dependencies added with the founder's explicit agreement: `motion` (the successor to Framer Motion), `@radix-ui/react-dialog`, `@radix-ui/react-tabs` (the citation panel and the queue/dashboard switcher, respectively — both now have correct ARIA semantics for free), `lucide-react`, `@fontsource/inter` + `@fontsource/jetbrains-mono` (self-hosted, no external font requests).
- Alternatives considered: (a) Build everything in the new docs at once — rejected, far too large a jump for one pass and violates the project's own increment-size rule. (b) Start with the landing page or the run-trace animation instead — both real options, left for the founder's next prioritization call rather than assumed.
- Consequences: Design tokens live as CSS custom properties in `web/src/styles/tokens.css`, consumed via Tailwind v4's `@theme` block (so `bg-surface-1`, `text-text-1`, etc. are real utility classes, not ad-hoc arbitrary values) — redefined per theme under `:root[data-theme="light"]`, toggled by `useTheme.ts` setting `data-theme` on `<html>` (not OS-detected). Motion tokens (durations/easings/springs) live in `web/src/motion/tokens.ts` matching `DESIGN_BRIEF.md` §7.1's values exactly. The citation modal became a real Radix `Dialog` sliding in from the right (desktop side-panel per `APP_FLOW.md` §3.5), with a proper focus trap and `Escape`-to-close it didn't have before. Verified for real: full build + lint clean, all 3 real-backend/real-LLM Playwright e2e tests passing (two needed updating for intentionally changed copy/ARIA roles, not bugs), and every screen screenshotted in both themes to visually confirm contrast and layout before calling it done.
- Revisit when: The founder picks the next slice (landing page, source-viewer-as-true-bottom-sheet-on-mobile, or the run-trace replay) — each is its own decision given the same "ask before this much new scope" discipline.

### D-46: Landing page built — spatial (3D-tilt + glassmorphism) design, real routing, real numbers only
- Status: Accepted
- Date: 2026-10-28
- Context: Founder picked the landing page as the next slice (following D-45's "pick the next slice" open item), with "spatial" meaning specifically 3D perspective/tilt on cards plus glassmorphism/floating layered panels — narrowed down from an initially ambiguous request by asking rather than guessing (the first ask, "connect watermelon ui," referred to no real, identifiable library and was abandoned once clarified).
- Decision: Added `react-router-dom` (confirmed with the founder first, per the project's ask-before-new-dependency rule) — `/` is now the landing page, `/app` is the existing alarm-queue/triage/dashboard tool (moved into `AppShell.tsx` unchanged in behavior, just relocated behind a route). Built `web/src/landing/` (`Hero`, `ProblemCards`, `HowItWorks`, `SafetyGuarantee`, `Results`, `Footer`) plus a reusable `GlassTiltCard` (frosted glass + cursor-following 3D tilt via Motion springs, with a cursor-following radial glow). Added `@fontsource/instrument-serif` for the hero headline per `DESIGN_BRIEF.md`'s type system. Scope discipline carried over from D-45: no landing content states anything unmeasured as measured.
- Content honesty specifics: the "How it works" 7 steps are the real pipeline from `docs/NLP_CONCEPTS.md` §2, not a marketing simplification. The "safety guarantee" token-budget animation is explicitly labelled illustrative ("not a live run") rather than implied to be a real run trace — `GET /runs/{id}` doesn't yet return a candidate-by-candidate decision log (`TRD.md` §3.2), so a real replay isn't possible yet; building a fake one that looked real was rejected. The "Results" tiles show exactly the three numbers in `eval/results/summary.md` (0% mandatory evidence ever silently dropped, 100% abstention precision/recall, 75% full-coverage rate) with the source file and run id stated on the page itself, and an explicit "not yet measured" line for cause accuracy/citation precision/real-plant outcomes — no number appears that isn't in that file.
- Alternatives considered: (a) a custom hand-drawn SVG hero illustration (alarm bell → bridge arc → checklist) as `DESIGN_BRIEF.md` §7.3 specifies — real illustration work beyond reasonable scope for this pass; substituted with floating glass chips using the same depth/glass language used throughout the rest of the page, noted plainly in a code comment as a conscious simplification, not a silent gap. (b) A full scroll-pinned (`position: sticky`-locked) safety-guarantee section — simplified to a `whileInView`-triggered animation instead, functionally similar (plays once as you scroll to it) without the added complexity of a pinned scroll hijack.
- Consequences: `Github` is not an exported icon in the installed `lucide-react` version (brand/logo icons were dropped from the core package) — used `Code2` instead for the "Source on GitHub" footer link. **A real screenshot-verification pitfall found and worked around**: Playwright's `fullPage` screenshot resizes the viewport instantly rather than actually scrolling, which can race with Motion's `whileInView` IntersectionObserver-based triggers — an initial fullPage capture showed several sections looking empty. Diagnosed correctly before treating it as a page bug, by re-verifying by scrolling incrementally and screenshotting at each real scroll position; the page itself was working the whole time. All 4 e2e tests pass against the real backend (3 pre-existing, re-pointed from `/` to `/app`; a new one added for the landing page's CTA navigation), build/lint clean.
- Revisit when: A real `/runs/{id}` decision trace exists (would let the safety-guarantee demo replay an actual run instead of an illustrative example); or the founder wants the hero's placeholder glass-chip visual replaced with a real custom illustration.

### D-40: Expanded `data/synthetic/alarms.json` from 12 to 32 alarms — selection-level only, no new gold labels
- Status: Accepted
- Date: 2026-10-25
- Context: Both eval layers were capped at the same N=12 (well under CLAUDE.md §4.1's 30-40 target) — not generation-eval being thinner than selection-eval, they shared one dataset. Generation-level eval costs real, rate-limited Groq API calls per data point; selection-level eval (`run_eval.py`) costs none — it's pure local retrieval/selection logic. So the free lever to pull first is growing the alarm set and re-running selection-level eval at scale, not spending more API calls on the same thin N.
- Decision: Added alarms 13-32 (20 new) to the existing 6 real fault categories only — no new categories or requirement tags, just varied site/inverter/message wording, keeping each category at 4 answerable instances and bringing unanswerable cases to 8 (24 answerable + 8 unanswerable = 32, matching §4.1's "~8 unanswerable" target). Deliberately did **not** add gold labels for ids 13-32 — D-14 gold labels need human authorship/review, and that wasn't part of this ask; `data/eval/gold_labels.yaml` stays scoped to alarms 1-12. `eval/run_generation_eval.py` already only iterates `gold.labels.keys()`, so it's unaffected by the larger alarm set.
- Consequences: Re-running `eval/run_eval.py` at N=32 produced the strongest evidence yet for H1/H2: `requirement_complete` never silently drops mandatory evidence at any budget (0% answered-incomplete vs 25-94% for the baselines) and perfectly distinguishes the 8 unanswerable alarms via abstention (100% precision/recall), while every baseline (topk/mmr/knapsack/safety_slot) answers all 8 confidently with zero abstentions — see `eval/results/summary.md`. Still provisional: still synthetic data, still short of the 30-40 target's upper end, and this doesn't yet include a generation-level (actual LLM answer) comparison at this scale.
- Alternatives considered: Draft gold labels for the new 20 alarms too (same AI-draft-then-founder-review pattern as D-37) — deferred, since it wasn't asked for and the free selection-level win didn't need it; worth revisiting if a larger generation-level comparison is wanted later.
- Revisit when: A generation-level comparison at N=32 is wanted (needs gold labels for ids 13-32 first), or the set should grow further toward/past CLAUDE.md's 30-40 target.

### D-41: Fixed cross-fault contamination in requirement tagging — `anchor_keywords_any` + fault-specific `corrective_measures_*` ids
- Status: Accepted
- Date: 2026-10-25
- Context: The narrow `requirement_complete`-vs-`topk` generation comparison (above) showed `requirement_complete` scoring *worse* than `topk` on `gold_page_recall` (0.35 vs 0.8) — investigated rather than taken at face value, since `requirement_complete`'s whole design point is guaranteeing mandatory coverage. Traced to a real bug, not a selection-quality difference: `config/requirements.yaml`'s keyword-only `tag_rules` (D-07) matched generic procedural phrases ("0.5 A", "disconnect the DC switch", "Contact Sungrow Customer Service") that recur across many *unrelated* fault rows in the manual's one big troubleshooting table. The greedy cover phase, which optimizes for token-cheapest valid chunk, was satisfying `safety_dc_isolation_sequence` for Boost-Capacitor/PV-Grounding alarms with a cheaper "System Hardware Fault" chunk (page 104) or even generic installation-guide boilerplate (page 50) instead of the real, correct, fault-specific procedure on page 103. Separately, `corrective_measures_present` (one id shared across all 6 fault categories) let an Excessive-Ambient-Temperature alarm's only mandatory requirement get satisfied by the *Boost Capacitor* fault's corrective text — a different fault's content entirely, confirmed by direct inspection of the manual's raw text (pages 96-105 pulled and read in full, not assumed).
- Decision: Added `anchor_keywords_any` to `Requirement`/`covers()` (`src/suryasutra/ingest/tag.py`) — a second, optional OR-group ANDed with the existing `keywords_any`, so a chunk must mention the actual fault by name (e.g. "Boost Capacitor", "PV Grounding") in addition to the generic procedural language. Backward compatible: omitting it preserves old behaviour exactly. Applied it to `safety_dc_isolation_sequence` (anchors: Boost Capacitor, PV Grounding — this safety sequence is genuinely shared by both fault categories, confirmed by reading the manual: both rows sit in the same page-103 chunk). Replaced the single fault-agnostic `corrective_measures_present` with 6 fault-specific ids (`corrective_measures_boost_capacitor`, `_pv_grounding`, `_low_insulation`, `_electric_arc`, `_meter_communication`, `_ambient_temperature`), each anchored on its own fault's name. Updated `fault_categories*`'s must/optional lists and `requirement_complete.py`'s citation-ordering logic (which matched the old id by exact string) to use a `corrective_measures_` prefix check instead.
- Alternatives considered: (a) Make coverage depend on the alarm's own fault category at selection time (query-time filtering) instead of a static per-chunk tag at ingestion — more correct in principle, but changes the `Selector` interface's inputs and D-28's "ingestion tags, triage resolves" separation; rejected as a bigger, riskier change than the ask warranted. (b) Merge adjacent same-topic chunks at the chunker level to avoid any page-boundary splits — rejected for now; the paragraph-packing chunker (D-23) isn't inherently page-bounded (it already spans pages when a paragraph doesn't divide evenly), and the specific case here wasn't actually a split-procedure problem, it was a wrong-fault-entirely problem.
- Consequences: Re-running the narrow generation comparison after the fix: `requirement_complete`'s `gold_page_recall` rose 0.35→0.45 and `step_checklist_coverage` 0.41→0.50 (`eval/results/summary_generation.md`) — real improvement, but still well below `topk`'s 0.8/0.75, which rules out "the bug fully explains the gap." **Separately and unexpectedly**, re-running `topk` — whose `TopKSelector.select()` never reads `chunk.covers` at all, confirmed by inspection (`src/suryasutra/selection/baselines.py:18-36`) — produced *different* numbers on the second run (cause_match_rate 0.2→0.4, step_coverage 0.59→0.75) despite nothing relevant to it changing. Since `topk`'s candidate chunks and prompt are deterministic given the same corpus, this is real Groq output variance at `temperature=0`, not a code effect — a concrete demonstration of why CLAUDE.md §12 calls for 3 runs on stochastic methods (not done here, single-shot each run, for API-budget reasons) and a reason to read any single-run generation-level comparison at this N as noisy, not decisive.
- Revisit when: A multi-run (3x) version of this comparison is affordable/wanted to separate real method differences from this demonstrated run-to-run noise; or the remaining `requirement_complete` vs `topk` page-recall gap is investigated further (e.g. the 99/100 two-page split for `low_system_insulation_resistance` noted but not fixed here — see `eval/results` per-alarm data).

### D-42: Docker Compose demo package (M6) — editable install, HF cache volume
- Status: Accepted
- Date: 2026-10-27
- Context: CLAUDE.md §15/§16 requires a one-command local demo (`docker compose up`) before the prototype is investor-demo-ready. Built `Dockerfile.backend` (Python 3.11-slim), `Dockerfile.frontend` (Node build → nginx), `web/nginx.conf`, and `docker-compose.yml`, then actually built and ran the stack rather than trusting the config on paper (Docker Desktop wasn't running at first — asked the founder to start it rather than attempting to launch a full GUI/VM app blindly).
- Decision: Backend installs the package with `pip install -e .` (editable), not a regular install. Found why the hard way: a regular install copies source into `site-packages`, which breaks `src/suryasutra/db/migrate.py`'s `REPO_ROOT = Path(__file__).resolve().parents[3]` lookup of `alembic.ini` (an assumption that already quietly depended on the package never being properly installed — true for local dev, via pytest's `pythonpath` setting, but not for a real `pip install .`). The container crashed on startup with `alembic.util.exc.CommandError: No 'script_location' key found` until fixed. Also added a named volume for the Hugging Face embedding-model cache (`/root/.cache/huggingface`) — without it, every `docker compose down && up` re-downloads the ~130MB model and redoes the slow first-load encode step.
- Alternatives considered: Fix `migrate.py` to not depend on `__file__`-relative path resolution (e.g. pass `alembic.ini`'s path via an env var or package resource) — more robust long-term, but bigger surface change than this ask warranted; the editable-install fix is a one-line Dockerfile change with zero application-code risk, and documents the real fragility here for whoever touches `migrate.py` next.
- Consequences: Verified for real, not just "docker compose up and assume": both images build clean; a from-scratch backend startup completes (slower — first run has to download the embedding model over the network, plus a CPU-bound chunk-encoding step that turned out to be the main cost, not a hang, confirmed by a staged timing script inside the container: ~7s PDF parse/chunk/tag, ~30s `DenseIndex` construction); a cache-warmed restart (after `down && up` with the volume in place) came up in **45s** (measured, not estimated). `/health`, `/alarms` (32 rows), `/stats/usage`, and a real `/triage` call (through to a live Groq response, citations and all) all verified working through the containerized stack, including nginx's `/api` reverse proxy to the backend from the frontend's own origin.
- Revisit when: Startup time becomes a real problem (e.g. pre-warming the FAISS/BM25 index at image-build time instead of every container start, if the manual/corpus is ever baked into the image rather than bind-mounted — not done now per D-13's never-redistribute-the-manual rule).

### D-43: AWS + Jenkins + Git deploy pipeline — two EC2 instances, SSH-based deploy, no Terraform/Ansible/Kubernetes
- Status: Accepted
- Date: 2026-10-27
- Context: Founder needed a public demo URL and separately specified wanting hands-on AWS/Jenkins experience alongside it (course/skill-building, not a product requirement — CLAUDE.md's own scope caps the prototype at a local `docker compose up`, M7/pilot doesn't call for any of this either). Explicit choice made after asking: Docker (already built, D-42) satisfies "one of Terraform/Ansible/Docker/Kubernetes" rather than adding another IaC/orchestration tool; Jenkins runs on its own instance rather than alongside the app.
- Decision: Two `t3.micro` EC2 instances (us-east-1, default VPC) provisioned directly via AWS CLI (not Terraform — the founder's choice): `suryasutra-app` (runs the dockerized app) and `suryasutra-jenkins` (runs `jenkins/jenkins:lts` in Docker). Security groups restrict SSH (22) and the Jenkins UI (8080) to the founder's own IP; only port 80 (the app's frontend+API, via nginx) is public. A single SSH key pair (`suryasutra-deploy-key`) was generated with its private key written directly to a local file (never printed to any terminal output) and loaded into Jenkins' own credential store the same way (staged into the Jenkins container's filesystem via `scp`+`docker cp`, read from disk by a Jenkins Groovy script, then deleted — the key's bytes never appeared in any visible command output or chat transcript). The `Jenkinsfile` does **not** build the backend image on the Jenkins box — it SSHes to the app instance and runs `docker compose build` *there*, so the 1GB-RAM Jenkins instance never needs Docker or multiple GB of ML build dependencies, only git + an SSH client. SCM polling (every 5 min) triggers builds, not a GitHub webhook — the Jenkins instance has no public inbound access for a webhook to reach.
- Alternatives considered: (a) Terraform to provision the instances — explicitly declined by the founder (Docker already satisfies the "one of" requirement); (b) Jenkins on the same instance as the app — declined in favor of a more realistic two-instance setup; (c) a GitHub webhook instead of polling — would need Jenkins reachable from GitHub's IPs, which conflicts with the IP-restricted security group chosen for safety; (d) building the backend image on the Jenkins instance itself — rejected once the backend image was found to need ~2.9GB (even after the D-42 CPU-only-torch fix) and real memory headroom a 1GB instance can't comfortably spare for a build *and* an idle Jenkins controller at the same time.
- Consequences: Two real, previously-undiscovered issues surfaced during this work and were fixed before they blocked the deploy. (1) The backend's default `sentence-transformers` install pulled a GPU-enabled PyTorch build (~2GB of unused CUDA/NVIDIA packages — image was 10.5GB before the fix), which would not have fit comfortably on a small instance's disk or build memory at all; pinning CPU-only torch (`--index-url https://download.pytorch.org/whl/cpu`) cut the image to 2.89GB, a real, measured improvement that helps the local dev/demo experience too, not just this deploy. (2) The first two Jenkins pipeline runs failed with `ssh: connect to host ... port 22: Connection timed out` despite the app SG explicitly allowing SSH from the Jenkins SG — root cause: AWS security-group-to-security-group source rules only match **intra-VPC** traffic; the Jenkinsfile was addressing the app instance by its *public* IP, which routes out through the Internet Gateway and back in, losing the "which security group did this packet originate from" context that SG-reference rules depend on. Fixed by pointing the Jenkinsfile at the app instance's **private** IP instead (both instances are in the same VPC/subnet, so this is simple internal routing) — build #3 then succeeded. Verified end-to-end for real, not assumed: the app is reachable at the app instance's public IP (frontend, `/api/health` returning 32 alarms, all confirmed working after the pipeline run, not just before it), and the Jenkins pipeline build genuinely ran through checkout → SSH deploy → remote `docker compose up -d --build` → smoke test, confirming the whole chain works, not just that the pieces exist on paper.
- Revisit when: A real custom domain + HTTPS is wanted (currently bare HTTP on a raw public IP — fine for a demo link, not for anything beyond that); or free-tier EC2 hours become a real constraint if these instances are left running continuously alongside whatever else already exists in this AWS account (3 pre-existing stopped instances were found during setup — not touched, kept entirely separate).
