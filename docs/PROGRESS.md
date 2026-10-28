# SuryaSutra — Progress

> What works, what's next, known issues. Updated after each milestone step.

## M1 — Ingestion + hybrid retrieval: DONE

**Done when (CLAUDE.md §15):** chunks with page provenance exist; retrieval returns sensible top-10 for 10 sample alarms. **Both measured, not assumed** — see the integration test below.

### What works
- Repo scaffolded per `CLAUDE.md` §8; Python 3.12 venv at `.venv/` (no `uv` on this machine, so plain `venv` + `pip install -e ".[dev]"` — same effect, note for Docker/CI later).
- **D-31 accepted:** Sungrow SG150CX manual confirmed as the first prototype document (D-12) — Sungrow leads India's utility-scale inverter market per JMK Research 2025. Downloaded (118 pages), hashed, source metadata in `data/raw/SOURCES.md` / `checksums.sha256`. `scripts/download_docs.sh` written and run (D-13).
  - **This sandbox's network cannot reach `.gov` domains** (DNS fails for `nrel.gov`/`osti.gov`; a SunSpec mirror also blocked the request as a bot). The NREL O&M guide URL is correct per NREL's own listing but unverified by direct download here. **Founder task, still open:** run `bash scripts/download_docs.sh` on your own machine to fetch it there.
- **Ingestion pipeline**, each piece unit-tested and separately verified against the real manual:
  - `ingest/parse_pdf.py` — PDF → `Page(number, text)`, 1-indexed (D-23 citation provenance). 2 tests.
  - `usage/tokens.py` — `count_tokens()`, pre-generation estimate via `tiktoken` (D-22: not billed truth). 4 tests.
  - `ingest/chunk.py` — `chunk_pages()`: pages → token-counted `Chunk`s with page-range provenance; oversized single paragraphs become their own chunk rather than being split or dropped. 6 tests.
  - `ingest/tag.py` — `load_requirements()`, `covers()`, `tag_chunks()`, `load_fault_categories()`: tags each chunk with the requirement ids its text satisfies (doc_type + keyword match); `Chunk.covers: frozenset[str]` is now populated on the chunk itself, matching the shape CLAUDE.md §6 specifies. 10 tests.
  - `ingest/build_index.py` — `build_corpus()`: wires parse → chunk → tag into one call. 1 test.
- `config/requirements.yaml` (D-07) — **6 fault categories** (`boost_capacitor_overvoltage_fault`, `pv_grounding_fault`, `low_system_insulation_resistance`, `electric_arc_fault`, `meter_communication_abnormal`, `excessive_ambient_temperature`), 7 requirements, all built from real manual text (pages 96–109) and marked `review_status: unreviewed` (D-14/§6 — not usable for a published safety claim until a qualified electrical/PV person signs off). Still partial: 6 of ~20+ fault codes in the manual, chosen to span distinct requirement shapes, not to be exhaustive.
- **Retrieval**, each verified on real data:
  - `retrieval/bm25.py` — `BM25Index`, tokenizer keeps hyphenated fault codes (`364-395`) intact. Exact-code query correctly outranks everything else. 5 tests.
  - `retrieval/dense.py` — `DenseIndex` (`BAAI/bge-small-en-v1.5`, FAISS flat/IP, D-19). Added `sentence-transformers`/`faiss-cpu` (pulls in CPU-only `torch`) — confirmed with founder before installing given the size. **Proved the point, not just passed a test**: a query sharing zero keywords with the source text ("leakage path to earth") still correctly found the insulation-resistance chunk. 3 tests.
  - `retrieval/hybrid.py` — `HybridRetriever` + `reciprocal_rank_fusion()`. RRF combines by rank position, not raw score (BM25 and cosine scores are on incomparable scales). 5 tests.
- **Indexed the whole 118-page manual** (not just the troubleshooting section): 103 chunks, ~30.8K tokens, 40 chunks carry at least one requirement tag.
- **`data/synthetic/alarms.json`** — 10 synthetic alarms (D-04/§4.1, clearly labelled `is_synthetic: true`), spanning all 6 fault categories, with real fault codes from the manual but invented site/inverter/timestamp/wording.
- **`tests/integration/test_retrieval_smoke.py`** — for each of the 10 synthetic alarms, hybrid retrieval's top-10 (over the whole-manual index) is checked for at least one chunk covering a mandatory requirement of that alarm's fault category. **Measured result: 10/10** (D-11 — reported because it was run, not assumed; if this regresses later, that's a real signal, not a flaky test to loosen).
- **Full suite: 37/37 tests passing** (`pytest tests/`, ~65s incl. the one real-model integration test). One transient `httpx.RemoteProtocolError` seen once from a Hugging Face Hub connectivity check — retried clean, not a code issue. Worth `HF_HUB_OFFLINE=1` once cached, for CI stability (D-27) — not done yet.

### Known issues / open items
- Chunker has no sub-paragraph splitting, so a page whose text is one giant run-on paragraph (true of this manual's fault tables) becomes one chunk regardless of `max_tokens`. Revisit only if eval shows this blows past realistic budgets.
- `config/requirements.yaml` is still a partial schema (6/~20+ fault categories) — expanding it is content work (reading more of §9), not a coding blocker.
- Alarm → fault-category resolution by `match_codes` (architecture §5 step 2) is loaded (`load_fault_categories`) but nothing *resolves* a raw alarm code against the ranges yet (e.g. turning code `370` into category `boost_capacitor_overvoltage_fault` automatically — the synthetic alarms carry a pre-assigned `category` label instead). That's a `triage/` concern.
- No selection, generation, API, or frontend yet — M2 onward.

## M2 — Selectors + abstention + tests: core selector done

**Done when (CLAUDE.md §15):** all selectors pass invariant tests; INSUFFICIENT works.

### What works
- `src/suryasutra/selection/base.py` — shared `Selector` interface, `Candidate`, `Answered`, `Insufficient` result types (D-06: INSUFFICIENT is a first-class result, not an exception).
- `src/suryasutra/selection/requirement_complete.py` — `RequirementCompleteSelector`, implementing CLAUDE.md §6's 4-phase algorithm exactly: greedy weighted set cover (cover phase) → feasibility check (`no_evidence` / `over_budget`, mandatory evidence never truncated) → fill phase (relevance/token greedy, cosine-similarity dedup at >0.9) → ordering (safety → cause → procedure → other, inferred from the `safety_*`/`cause_*`/`check_*` naming convention already in `requirements.yaml`).
- `src/suryasutra/selection/baselines.py` — `TopKSelector`: relevance-only, no mandatory-coverage awareness at all. This is deliberate (D-09) — it's the comparison point, not a lesser implementation of the same idea.
- **D-25's invariants are tested two ways**, not just asserted: example-based tests for each phase (cover, over-budget refusal, dedup, ordering) *and* three Hypothesis property tests (100 random examples each) — never exceeds budget B, never answers with an uncovered mandatory requirement, deterministic given identical input. All passing. 14 selector-specific tests + 3 baseline tests.
- **Ran a real comparison on the actual manual + synthetic alarms** (informal sanity check, not the formal E0 pilot study — that needs the full hand-labelled eval set per D-14/M5): at budget=500 tokens, `TopKSelector` silently dropped mandatory safety evidence on **2/10** alarms; `RequirementCompleteSelector` never dropped evidence and never even had to abstain (fit all mandatory requirements within budget on all 10 alarms, all three budgets tested: 500/1000/2000). Small n, not a claim — but a real, measured early signal in the direction H1 predicts, from the actual mechanism running on actual data.
- Full suite: **51/51 tests passing** (`pytest tests/`, ~35s).

### Baselines complete (D-09)
- `src/suryasutra/selection/baselines.py` now has all four: `TopKSelector` (greedy relevance), `KnapsackSelector` (exact 0/1 knapsack via DP — provably optimal total relevance within budget), `MMRSelector` (diversity-aware, penalizes cosine similarity to already-selected), `SafetySlotSelector` (RAGuard-style fixed token quota for safety-tagged chunks). Shared `cosine_similarity()` factored into `selection/base.py` so `RequirementCompleteSelector`'s dedup and MMR's diversity penalty use the same code.
- 12 new example-based tests (each baseline's never-exceeds-budget property, plus a test demonstrating *why* it's a baseline — e.g. Knapsack's classic counter-example win over greedy TopK, MMR correctly preferring a diverse chunk over a near-duplicate, SafetySlot's fixed-quota gap) + 5 Hypothesis cases (`test_selector_budget_property.py`) checking all five selectors (4 baselines + the research selector) never exceed budget, parametrized across randomized inputs. **65/65 tests passing** (includes the one occasionally-flaky HF-hub integration test, which passed clean on retry both times it flaked — not a code issue).
- **Ran the full 5-selector comparison on the real manual + 10 synthetic alarms at budgets 500/1000/2000 — a genuinely interesting, non-obvious result, not just confirmation of the obvious:**

  | Selector | 500 dropped | 1000 dropped | 2000 dropped |
  |---|---|---|---|
  | TopK | 2/10 | 0/10 | 0/10 |
  | Knapsack (exact optimal relevance) | **9/10** | 5/10 | 2/10 |
  | MMR | 2/10 | 0/10 | 0/10 |
  | SafetySlot | 2/10 | 0/10 | 0/10 |
  | RequirementComplete | **0/10** | 0/10 | 0/10 |

  Knapsack — the *provably optimal* relevance-maximizing baseline — drops mandatory evidence more often than crude greedy TopK, not less. Maximizing total relevance-per-token has no reason to prefer the one chunk that happens to be safety-critical over several smaller, similarly-relevant chunks that sum to a higher score; exact optimization of the wrong objective is worse than approximate optimization of it. This is a stronger version of H1 than "greedy selectors sometimes fail" — even the *best possible* version of relevance-only selection fails, which is a sharper argument for why coverage needs to be an explicit constraint rather than something hoped for from a good relevance proxy. Small n (10 synthetic alarms), not the formal E0 pilot study — but worth keeping as-is for the next write-up.

## Verification pass (requested by founder, 2026-10-19 later same day)

Ran a full honest check of everything built so far, not just "tests pass":

- **Tooling that hadn't actually been run yet this session**: `ruff check`/`ruff format` found 3 real (minor) issues, `mypy --strict` found 2 (a missing stub install, a genuine `Any`-return). All fixed. Both now clean across all 16 source files.
- **Fixed real test flakiness at its root**: `tests/conftest.py` now sets `HF_HUB_OFFLINE=1` once the embedding model is confirmed cached locally, eliminating a recurring `httpx.RemoteProtocolError` from an unnecessary Hugging Face Hub connectivity check on every model load (confirmed: not a code bug, just a pointless network round-trip once the model is already on disk).
- **Verified data integrity**: the downloaded manual's SHA-256 still matches `checksums.sha256` exactly.
- **Live end-to-end run (not just unit tests, which use small synthetic chunks) surfaced a real, substantive problem**: for the "Boost Capacitor Overvoltage Fault" alarm, the final answer included page 92 — the iSolarCloud **mobile app installation instructions** — despite page 103 (the actual, correctly-retrieved-at-rank-1 fault procedure) existing in the candidate pool. Root cause, diagnosed not guessed: the cover phase's pure `tokens/newly_covered` cost had no way to prefer a more relevant chunk once a cheaper one satisfied the same tag (ties almost never happen on real text), and the fill phase's `relevance/tokens` ranking has no floor at all, so cheap+barely-relevant content can out-rank expensive+highly-relevant content.
- **Two real fixes, in order, each verified against the actual failing case (not just a crafted unit test) before moving on:**
  1. Cover-phase cost changed from `tokens / newly_covered` to `tokens / (newly_covered * relevance)` (D-32-adjacent change, folded into the main algorithm). Verified: stopped picking a completely generic installation-chapter chunk for the mandatory slot. Did **not** fully fix the real case — a nearby-but-wrong-fault chunk (page 104, same manual table, different fault code) still narrowly beat the ideal page 103 on cost. Tried a relevance-floor fraction for the fill phase next; it **did not work** on real RRF-fused scores (they decay too gently with rank — page 92 still cleared a 30%-of-max floor). Diagnosed and reported honestly rather than just cranking the threshold up with no eval data to check it against (D-10).
  2. **D-32**: restructured the fill phase to require covering a declared `optional` requirement id, full stop — no relevance-based filler at all anymore. Verified on the real case: page 92, page 68, page 117, and page 38 (all untagged) are now gone entirely; the answer is just pages 104 and 96 (both genuinely tagged, both in the troubleshooting section). CLAUDE.md §6 step 3 updated to match; this is now the documented behavior, not a one-off patch.
- **Re-ran the full 5-selector comparison after both fixes**: identical headline numbers (RequirementComplete still 0/10 dropped mandatory at all three budgets) — confirms the fixes didn't regress the core safety property, only improved filler quality.
- Full suite after all fixes: **67/67 tests passing**, lint and types clean.

### Known issues / open items
- **Still imperfect, honestly**: the cover phase can still pick a topically-adjacent-but-not-ideal chunk (page 104 over page 103) when their relevance scores are close and token costs differ — this is the same underlying tension (cost vs. relevance) in a milder form. Needs real eval data to tune responsibly, not another guessed constant. Flagged, not further hand-tuned.
- When a fault category's `optional` list is sparse (most of ours have 0-1 ids right now), answers may use noticeably less than the full budget B. Accepted tradeoff per D-32, not a bug — revisit once `requirements.yaml` has richer optional coverage.
- No `ILPSelector` exactness check yet (D-08) — greedy vs. optimal gap *for RequirementCompleteSelector itself* is unmeasured (different from the Knapsack baseline above, which is a separate, deliberately coverage-blind method).
- No regression test suite yet of "alarms whose mandatory safety chunks must always be selected" (D-25's last requirement) — the Hypothesis property tests cover the *general* invariant; a fixed real-alarm regression set is still to come.
- The order-phase category inference (`safety_*`/`cause_*`/`check_*` prefix matching) is a naming-convention heuristic, not a declared field on `Requirement` — fragile if future requirement ids don't follow the convention. Flagging, not fixing now (no evidence it's wrong yet).
- Selection logic has no DB/API/generation hookup yet — it's pure functions operating on in-memory `Candidate` lists, exactly as D-28 wants, but nothing calls it from a pipeline yet.

## M3 — Generation + validator + usage logging: core built, awaiting live key

**Done when (CLAUDE.md §15):** cited JSON answers; cost logged per run.

### What works
- **Provider chosen: Groq**, model `openai/gpt-oss-120b` (131K context). Pricing fetched directly from Groq's own docs (console.groq.com/docs/model/...), not a third-party aggregator: $0.15/$0.60 per million input/output tokens. Recorded in `config/pricing.yaml` with source URLs and a dated USD→INR rate (~96.5, approximate — re-check before relying on it for real cost claims).
- `src/suryasutra/usage/cost.py` — `load_pricing()`, `compute_cost_inr()`. 4 tests.
- `src/suryasutra/generation/llm/base.py` — `LLMAdapter` ABC + `LLMResponse` (D-21: no provider SDK import outside this package).
- `src/suryasutra/generation/llm/groq_adapter.py` — `GroqAdapter`, the only module importing the `groq` SDK. Verified against the SDK's actual type signatures (model id literals, `CompletionUsage` field names `prompt_tokens`/`completion_tokens`, `response_format={"type": "json_object"}` support) rather than guessed.
- `src/suryasutra/generation/schema.py` — Pydantic models for the answer contract (CLAUDE.md §10). `LLMAnswerPayload` deliberately excludes `alarm`/`status` — the model never restates data we already have, only produces the clinical content that needs grounding. Added a third `InsufficientContract` reason, `citation_validation_failed`, not in the original two-value spec — a materially different failure (evidence existed and fit budget; generation itself failed), documented in the schema's own docstring.
- `src/suryasutra/generation/validate.py` — `validate_citations()`: every safety item and step must cite a selected chunk id; `likely_causes` deliberately exempt per CLAUDE.md §10's literal wording. 4 tests.
- `src/suryasutra/generation/prompts/triage_prompt.py` — `build_prompt()`: assigns per-request citation ids (`c1`, `c2`, ...) to selected chunks (no stable chunk DB id exists yet).
- `src/suryasutra/generation/generate.py` — `generate_triage_answer()`: prompt → LLM → parse → validate → retry once → else INSUFFICIENT(`citation_validation_failed`). 5 tests using a `FakeLLMAdapter` (no network, no API key needed) covering first-try success, retry-then-success, retry-exhausted, malformed JSON, and real cost computation from the pricing table.
- `tests/integration/test_groq_live.py` — real, live call against the actual Groq API (`GROQ_API_KEY` in `.env`, gitignored, not committed — caught and fixed one close call: the key was briefly pasted into the *tracked* `.env.example` template instead; moved to `.env` before anything was staged, never committed or pushed).
- **Live-verified, not just mocked.** For the boost-capacitor alarm: the model produced a correctly-shaped, fully-cited `ANSWERED` response on the first try (no retry needed) — safety box first (de-energize all switches before resetting), 3 clear steps all citing `c1`, an honest `uncertainties` entry ("root cause ... not detailed in the provided documentation" — it did not invent one), and a sensible `escalate_if`. Real usage: 434 input / 682 output tokens, cost ₹0.046 for this call, computed from the real pricing table.
- Full suite: **81/81 passed, 0 skipped**. Lint and types clean across 26 source files.

### Known issues / open items (M2, carried forward)
- Cover phase can still pick a topically-adjacent-but-not-ideal chunk when relevance scores are close — flagged, not further hand-tuned without eval data.
- Answers may use less than the full budget B when a category's `optional` list is sparse — accepted tradeoff (D-32).
- No `ILPSelector` exactness check, no fixed regression alarm set, order-phase category inference is a naming convention not a schema field — all previously flagged, unchanged.

### Known issues / open items (M3, new)
- Only verified on **one** real alarm so far, once. Haven't yet checked determinism at `temperature=0.0` across repeated calls, nor run the other 9 synthetic alarms live (each live call costs real money and API quota — worth doing deliberately, e.g. as part of building the eval runner, not just to pad a test count).
- No DB persistence of runs/usage yet (the `usage`/`triage_runs` tables in CLAUDE.md §9 don't exist) — `generate_triage_answer()` returns a contract object, nothing logs it anywhere yet.
- `max_retries=1` (one retry, matching CLAUDE.md §10) is hardcoded as a default, not yet exposed as a budget/method-comparison-relevant parameter for eval.
- No `/triage` API endpoint yet — this is still pure library code, not reachable over HTTP. That's M4.

## M4 — API: backend done, React UI not started

**Done when (CLAUDE.md §15):** alarm → triage → compare mode works end to end locally. Backend half confirmed; no UI yet (compare mode specifically needs it).

### What works
- **D-16 re-confirmed**: considered Node/Express for the API layer (founder's prior MERN experience). Stayed with FastAPI — all retrieval/selection/generation logic (M1–M3, 15+ Python modules, 81 tests) would otherwise need a full JS rewrite or a second process behind Node, which is exactly the microservices overhead D-15 already rejected for this stage. React itself is backend-agnostic either way, so this was purely about the API layer.
- `src/suryasutra/api/state.py` — `AppState`: builds the real corpus (full 118-page manual, BM25 + dense index), pricing table, and the Groq adapter **once per process** (FastAPI `lifespan`), not per request.
- `src/suryasutra/api/main.py` — `GET /health`, `GET /alarms` (serves the 10 synthetic alarms), `POST /triage` (runs the actual retrieval → selection → generation pipeline for a given `alarm_id`/`method`/`budget`, returns the real `AnsweredContract` or `InsufficientContract`). No DB yet — deliberately deferred, not needed for this slice.
- `tests/integration/test_api.py` — 6 tests via FastAPI's `TestClient`, LLM monkeypatched to a scripted fake (no real API cost per test run): health, alarm listing, 404/400 error paths, INSUFFICIENT-on-tiny-budget, and a full ANSWERED path with citation checks.
- **Verified as a real standalone server, not just inside the test harness**: started the actual `uvicorn` process, confirmed `/health` and `/alarms` over real HTTP, then ran one genuine live `/triage` call — alarm → real retrieval → real selector → real Groq model → real cited JSON answer, cost ₹0.062, logged from the real pricing table. This is the first point the full pipeline has run as an actual running service rather than library calls in a script.
- Full suite: **87/87 passed**. Lint and types clean across 30 source files (fixed 4 new mypy findings: 3 missing `dict` type args, 1 genuine type gap — `Insufficient.reason` was a bare `str` where it should have been the `Literal["no_evidence", "over_budget"]` it actually only ever is; tightening it caught a latent type mismatch at the API boundary before it became a real bug).
- **Caught the `.env.example` API-key issue a second time** (same mistake recurred — the live key ended up back in the tracked template file). Fixed again before anything was staged; still never committed or pushed. Worth double-checking which file (`.env` vs `.env.example`) before pasting a key in the future.

## M4 — React UI: done, genuinely verified in a real browser

**Done when (CLAUDE.md §15):** alarm → triage → compare mode works end to end locally. **Confirmed, not assumed** — see below.

### What works
- `web/` — React 18 + Vite + TypeScript + Tailwind v4 + TanStack Query, scaffolded via `npm create vite`, matching CLAUDE.md §7 exactly. Dev server proxies `/api/*` to the FastAPI backend (`vite.config.ts`) so there's nothing to reconfigure for Docker Compose later.
- **Schema gap found and fixed before building the UI, not after**: the `/triage` response only ever carried opaque citation ids (`c1`, `c2`) with nothing to resolve them to — so "click a citation → see the source page" (§11's explicit spec) was literally impossible with the contract as documented. Added a `sources: dict[citation_id, {page_start, page_end, text}]` field to `AnsweredContract` (purely additive; CLAUDE.md §10 updated to match) and populated it in `generate_triage_answer()`. Backend tests extended to check it's actually populated.
- **`AlarmQueue`** (`web/src/pages/AlarmQueue.tsx`) — table with time/site/inverter/code/message, site filter, synthetic-data badges, row click selects an alarm.
- **`TriageView`** (`web/src/pages/TriageView.tsx`) — method/budget controls, red safety box first, causes, numbered steps with citation chips, INSUFFICIENT banner with missing requirements, usage footer (tokens, ₹, budget, method). Citation chips open a `SourcePanel` modal showing the actual page + text a citation points to. *Known gap, not faked*: §11 also wants latency in the usage footer; the backend contract doesn't carry it yet, so it's honestly omitted rather than invented.
- **`CompareView`** (`web/src/pages/CompareView.tsx`) — two independent method selectors, one shared budget, runs both via two `useMutation` calls, renders results side by side via a shared `TriagePanel`, which prominently flags "⚠ No safety evidence" when a result is INSUFFICIENT or has an empty safety list — the actual point of compare mode per §11.
- **No `react-router` or other navigation library added** — deliberately: with 3 screens and no deep linking need yet, local `useState` in `App.tsx` toggles between triage/compare view. Avoids an unlisted dependency for a prototype this small.
- **Real browser verification, not just a type-check**: no browser automation tool was available in this environment, so installed Playwright (already in CLAUDE.md §7's testing stack) and ran genuine headless-Chromium e2e tests against the actual running app — both servers started for real, actual Groq calls made, actual DOM assertions. `triage.spec.ts` (alarm queue → triage → citation → source panel, open and close) and `compare.spec.ts` (two real methods run side by side) **both pass**. Screenshots taken and visually reviewed (not just assertion-checked) for both triage view and compare mode — confirmed correct layout, real data, real answers, real citation chips.
- **Found and fixed a second instance of the HF Hub network flake** (first fixed for pytest only, via `tests/conftest.py`) — it also broke plain `uvicorn`/Playwright webServer startup, which that fix didn't cover. Moved the fix to its actual source, `suryasutra.retrieval.dense`, so it protects the whole app, not just tests; simplified `conftest.py` to just trigger that module's import.
- Full verification: backend **87/87** passing, lint/mypy clean (30 source files); frontend `oxlint` clean, `tsc` strict build clean; **2/2 real e2e tests passing** against the live app.

### Known issues / open items
- No DB persistence (`triage_runs`, `usage` tables from CLAUDE.md §9 don't exist) — every `/triage` call is stateless; nothing is logged anywhere for the eventual cost dashboard (§11 screen 4, not built).
- `GET /runs/{id}`, `GET /documents/{id}/page/{n}`, `GET /stats/usage`, `POST /feedback` (CLAUDE.md §10's full API table) don't exist yet — only `/health`, `/alarms`, `/triage` do.
- Usage footer is missing latency (see above) — needs `LLMResponse.latency_ms` threaded through to the `Usage` schema, not done yet.
- `/triage` calls the real Groq API on every request with no caching — fine for a prototype; each e2e/manual test run has a real (small) cost.
- A `StarletteDeprecationWarning` about `httpx` vs an `httpx2` package still appears in backend test output — noted, not chased.

## M5 — Eval run (pilot E0): selection-level results in, generation-level pending founder labels

**Done when (CLAUDE.md §15):** results table for methods × budgets on eval set, committed summary. **Done for selection-level metrics** — generation-level metrics (cause accuracy, step correctness, citation precision) need D-14's hand-labelled gold data, not yet collected, and are honestly not claimed here.

### What works
- `eval/metrics.py` — pure, testable functions: `classify()` (three-way outcome: `answered_complete` / `answered_incomplete` / `insufficient` — `answered_incomplete` is exactly H1's dangerous case: confidently answered while silently missing a mandatory requirement), `tokens_used()`, `abstention_confusion()` (precision/recall against the alarm's `answerable` ground truth). 8 tests.
- **Widened the eval set honestly, not just reused the old one**: added an `answerable: bool` field to all 10 existing alarms (all `true`) and 2 new deliberately-unanswerable synthetic alarms (ids 11-12, code `9001`, category `battery_thermal_event_test`) — a new requirement (`safety_battery_thermal_isolation`) whose keywords were *verified absent* by direct text search against the real manual before use, not assumed. Still short of D-14's 30-40 target; flagged, not pretended otherwise. Fixed the two tests that assumed the old 10-alarm/all-answerable shape — both failures were correct, honest consequences of the new unanswerable cases, not bugs, including a new test confirming retrieval genuinely finds no match for them (proving they're real hard cases, not mislabelled ones).
- `eval/run_eval.py` — runs all 5 selectors × 3 budgets (500/1000/2000) over the 12-alarm eval set, selection-only (no LLM calls — H1/H2 are about selection, and CLAUDE.md's architecture principle is to evaluate retrieval/selection/generation separately, never only end-to-end). Writes one `eval/results/<timestamp>_<method>_<budget>.json` per combination (D-26: config, versions, git commit hash) plus `eval/results/summary.md`.
- **A real bug found and fixed along the way, not just an eval-script detail**: `HybridRetriever` had never actually attached embeddings to its results — `Candidate.embedding` was silently `None` everywhere it's constructed from real retrieval (the live API included), which meant MMR's diversity penalty and `RequirementCompleteSelector`'s near-duplicate dedup had been non-functional in the *actual running system* this entire session, not just in eval. Existing tests all passed because they used hand-built fixtures with explicit embeddings, which masked the gap. Fixed at the source: `DenseIndex` now exposes `embedding_for(chunk)` (every corpus chunk's embedding is already computed at construction), `HybridRetriever.query()` attaches it to every result regardless of which ranking a chunk came from, and both `api/main.py` and `eval/run_eval.py` were updated to actually use it. New regression test confirms embeddings are non-`None` from a real `HybridRetriever.query()` call, not just from hand-built fixtures.
- **Real E0 results, run twice — once with the bug, once after the fix — both logged, not just the second one quietly kept:**

  | Method | Budget | Full coverage | Answered-incomplete (H1) | Insufficient | Mean tokens | Abstention P/R |
  |---|---|---|---|---|---|---|
  | topk | 500 / 1000 / 2000 | 67% / 83% / 83% | 33% / 17% / 17% | 0% | 435 / 973 / 1967 | n/a / 0% |
  | knapsack | 500 / 1000 / 2000 | 8% / 42% / 67% | **92%** / 58% / 33% | 0% | 460 / 980 / 1988 | n/a / 0% |
  | mmr | 500 / 1000 / 2000 | 67% / 67% / 67% | 33% / 33% / 33% | 0% | 435 / 970 / 1938 | n/a / 0% |
  | safety_slot | 500 / 1000 / 2000 | 67% / 83% / 83% | 33% / 17% / 17% | 0% | 435 / 975 / 1976 | n/a / 0% |
  | requirement_complete | 500 / 1000 / 2000 | 83% / 83% / 83% | **0%** / 0% / 0% | 17% | 300 / 636 / 1245 | **100% / 100%** |

  `requirement_complete`'s 83% "full coverage" is not a shortfall — it's exactly correct: 10/12 alarms are genuinely answerable (the other 2 are the deliberately-unanswerable test cases), and it answers all 10 completely while abstaining on exactly those 2 (83% + 17% = 100% of alarms get the *right* outcome — answered or correctly declined — never the dangerous middle). **Across every budget, `answered_incomplete` is 0% for `requirement_complete` and nonzero for all four baselines** — the hard mandatory-coverage guarantee (D-06) held empirically across the whole eval set, not just by construction. Abstention precision and recall are both 100% at every budget: it never incorrectly abstained on an answerable alarm, and never missed abstaining on an unanswerable one.

  Knapsack — the *exact* relevance-optimal baseline — is again the worst of the four baselines (92% answered-incomplete at budget 500), replicating the earlier single-alarm finding now across the full eval set: exact optimization of the wrong objective is more dangerous than approximate optimization of it, not less.

  n=12 (10 answerable + 2 unanswerable), not the formal 30-40-item D-14 set — real, logged, reproducible results (git commit `d362d53`), but small-n; no confidence intervals or significance tests yet (CLAUDE.md §12 wants bootstrap CIs and paired tests — not done).
- Full suite: **97/97 passed**. Lint, format, and mypy clean across 33 source files.

### Known issues / open items
- **Generation-level metrics not run**: cause accuracy (top-3), step correctness (rubric), citation precision need hand-labelled gold data per D-14 — this is explicitly the founder's task, not something to fabricate. See "Task for the founder" below.
- Eval set is 12 alarms, not D-14's 30-40 — expanding it is content/labelling work, not a code change.
- No ILP selector (D-08) — greedy vs. optimal gap for `RequirementCompleteSelector` itself is still unmeasured.
- No bootstrap CIs or paired significance tests (McNemar/Wilcoxon) yet — CLAUDE.md §12 wants them; the table above is point estimates only, honestly labelled as such.
- The transient HF Hub network flake (seen earlier, fixed for pytest and for `uvicorn`/Playwright startup) also hit `eval.run_eval` directly once — retried clean. Not chased further; same known, non-code-bug flake.

### Task for the founder (per CLAUDE.md §17.4 and D-14)
D-14 is explicit that gold labels must come from you, not be invented by the system being evaluated. To get real generation-level metrics (cause accuracy, step correctness, citation precision) and to reach the 30-40-alarm eval set size, the next concrete task is: for each alarm (existing 12 plus new ones toward 30-40, ~20% deliberately unanswerable), write down the gold cause(s) and which specific manual passages (page numbers) are the mandatory evidence — this becomes the ground truth `eval/data/` file the generation-level metrics get checked against. Happy to build the labelling format/tooling once you're ready to start.

## DB layer — alarms/triage_runs/usage persistence: done

Not a CLAUDE.md milestone of its own, but the fork from M5's "next step" that got picked: DB-backed persistence so triage history is queryable and the eventual dashboard has real data to read.

### What works
- **Scoped deliberately**: implemented `alarms`, `triage_runs`, `usage` from CLAUDE.md §9's data model — the three needed to persist a triage call. `documents`/`chunks`/`requirements`/`feedback` stay file- and config-based; ingestion still rebuilds the corpus in-memory at startup (D-15) and doesn't write to a DB at all. Said so explicitly rather than silently doing a partial job.
- `src/suryasutra/db/models.py` — SQLAlchemy 2.0 declarative models (`Alarm`, `TriageRun`, `Usage`), matching CLAUDE.md §9's field list.
- `src/suryasutra/db/session.py` — `get_session()`; switches SQLite/Postgres purely via `DATABASE_URL` (D-18), same as already-existing settings.
- Alembic wired up (`alembic.ini`, `src/suryasutra/db/alembic/`) — `env.py` reads `DATABASE_URL` from `config.settings` rather than a separately-maintained ini value, so there's one source of truth, not two to keep in sync. Initial migration generated via `--autogenerate` and verified by actually running it against a throwaway SQLite file and inspecting the resulting schema (not just "the command exited 0").
- `src/suryasutra/db/migrate.py` — runs migrations programmatically at app startup (`alembic upgrade head`), so there's no separate manual step for the one-command local demo. Noted as a deliberate prototype-stage choice — a real Postgres deploy would normally run migrations as an explicit release step instead.
- `src/suryasutra/db/seed.py` — `seed_alarms_from_json()`: idempotent (checks existing ids before inserting), keeps `data/synthetic/alarms.json` as the source of truth while making alarms queryable.
- `src/suryasutra/api/state.py` — `AppState.__init__` now runs migrations and seeds alarms before anything else.
- `src/suryasutra/api/main.py` — `GET /alarms` now reads from the DB (not the in-memory dict — makes the persistence layer prove it's actually read from, not a write-only black hole); `POST /triage` persists a `TriageRun` row on every call (plus a `Usage` row when generation actually ran — an `INSUFFICIENT` from the selector phase correctly has no usage row, since nothing was spent); new `GET /runs/{id}` endpoint (CLAUDE.md §10's declared API, not previously built) returns the full stored trace.
  - Caught and fixed one real mistake before shipping it: initially set `TriageRun.model` to the *selector* method name (`contract.usage.method`) instead of the actual LLM model — an easy mix-up since both are called "method"/related to "usage" in different schemas. Fixed to use `settings.llm_model` and `EMBEDDING_MODEL_NAME` instead.
- **Tests, not just "it ran once"**: `tests/unit/test_db_models.py` (4 tests against a throwaway in-memory SQLite engine — round-trip, FK relationship, seeding correctness, seeding idempotency) + 2 new API tests (`GET /runs/{id}` returns what `POST /triage` just wrote, including a direct DB query to find the right run id rather than assuming; unknown run id 404s).
- **Test isolation fixed properly**: DB-backed tests were initially going to hit the real dev SQLite file at `.env`'s `DATABASE_URL`, which would've kept accumulating rows across every test run. `tests/conftest.py` now points tests at a dedicated file (`data/processed/test_suryasutra.db`, gitignored) and deletes it at the start of each session — which doubles as a check that migrations + seeding genuinely work from nothing, not just incrementally on top of leftover state.
- **Verified against the real, running, browser-driven app, not just pytest**: ran the actual Playwright e2e suite against the full stack (real `uvicorn`, real migrations, real DB) — both tests passed, and directly queried the real dev DB afterward to confirm 3 real `triage_runs` rows (with `usage` rows) were genuinely written by the browser session, not just asserted by a test.
- Full suite: **103/103 passed**, lint/format/mypy clean across 40 source files.

### Known issues / open items (carried forward)
- No `POST /feedback` yet.
- `documents`/`chunks`/`requirements` tables don't exist — the corpus is still rebuilt from the PDF + YAML at every process startup, not persisted or queryable by id. Revisit when multi-document/multi-tenant support actually matters (pilot stage, D-19).
- Migrations run implicitly at every app startup rather than as an explicit deploy step — fine for prototype/SQLite, noted as a thing to change before a real Postgres deploy.
- The transient HF Hub network flake hit the Playwright `webServer` startup during this work too (same known pattern, retried clean) — observed across pytest, plain `uvicorn`, and Playwright; still not chased further since it's never been a real code bug, always clears on retry.

## Dashboard (`GET /stats/usage` + frontend screen): done

CLAUDE.md §11 screen 4: "cost per alarm by method/budget, mandatory-coverage rate, abstention counts, from real logged runs only."

### What works
- **Fixed a real gap before building the dashboard, not after**: `TriageRun.missing_requirements` was previously only ever populated for `INSUFFICIENT` results — an `ANSWERED` result from a baseline selector that silently dropped a mandatory requirement (H1's exact failure mode) wasn't flagged anywhere in the DB, which would have made "mandatory-coverage rate" on the dashboard quietly wrong for exactly the cases that matter most. `POST /triage` now computes the mandatory-coverage gap from the selection phase itself, independent of which contract type ends up being returned, and persists it either way. New regression test (`test_persisted_run_flags_mandatory_coverage_gap_even_when_status_is_answered`) uses a real alarm/method/budget combination already known (from the M5 eval run) to trigger this, not a contrived fixture.
- `GET /stats/usage?group_by=method,budget` — groups real `triage_runs`/`usage` rows by any combination of `method`/`budget` (CLAUDE.md §10's example), returns run/answered/insufficient counts, full-mandatory-coverage rate, and mean cost/tokens. Means are `null` (not `0`) when a group has no usage data yet — an honest "nothing to average" rather than a fabricated number (D-11). Invalid `group_by` fields 400.
- `web/src/pages/Dashboard.tsx` — table + a Recharts bar chart (first real use of Recharts in the project) of mean cost by method/budget. Explicit empty state ("No triage runs recorded yet...") when there's no data — never a chart with fake numbers.
- `App.tsx` restructured with a simple tab switcher (Alarm queue / Dashboard) — still no router dependency, consistent with the earlier call to avoid one for 3-4 screens with no deep-linking need.
- **A real bug caught and traced to root cause, not shrugged off**: first dashboard screenshot showed the bar chart's axes/legend/table all correct but the bars themselves invisible. Didn't assume it was fine — queried the live DOM via Playwright, found the actual bar `<path>` elements had entirely correct geometry and fill, then found my own debugging selector (`.recharts-wrapper svg`) had matched the Legend's tiny icon SVG, not the main chart. Root cause: Recharts' default mount animation — the first screenshot was taken immediately after switching tabs, before the bars finished animating in. Confirmed by retaking the screenshot after a wait; bars render correctly. Not an app bug — a timing artifact in my own verification script.
- 3 new backend tests (`test_stats_usage_invalid_group_by_returns_400`, `test_stats_usage_groups_real_run_by_method_and_budget` using a distinctive budget value to isolate its assertions from other tests sharing the same test DB, plus the coverage-gap regression test above) + 1 new real e2e test (`dashboard.spec.ts`, real backend/LLM/DB, confirms the dashboard reads back a run it just caused).
- Full suite: **106/106 passed**, lint/format/mypy clean on the backend; frontend `oxlint` + `tsc` build clean; **3/3 real e2e tests passing**.

### Known issues / open items
- Chart only shows mean cost; CLAUDE.md §11 also implies abstention counts and coverage rate could be charted, not just tabled — table covers this for now, chart could be extended later if useful.
- Still no `POST /feedback`.

## Eval gold-labelling tooling (D-14): built; founder-reviewed; qualified-person sign-off still open

### What works
- **Caught a process gap and fixed it first**: `docs/DECISIONS.md` hadn't been touched since the very first commit, even though several real decisions were made since (D-33–D-36 now added: Groq/model choice, the `sources` field addition, DB layer scoping, the retrieval embedding fix) — CLAUDE.md §0.8 requires logging these after each milestone and it had slipped. Fixed before starting this work, not after.
- `eval/gold_labels.py` — `GoldLabel`/`GoldLabelSet` (Pydantic), `load_gold_labels()`, `write_template()`. `write_template()` still never pre-fills gold fields — enforced by a test, not just a docstring promise. `GoldLabelSet` carries `drafted_by`, machine-checkable provenance (who/what actually wrote the field values), not just a prose comment.
- `eval/suggest_gold_labels.py` — a **clearly separate, non-authoritative** helper: runs real retrieval per answerable alarm and lists which pages the *automated* tagging system currently believes are mandatory-relevant, writing to a **different file** (`data/eval/system_suggestions.yaml`, gitignored, regenerable) so there's no way to mistake "what the system already believes" for "what a human independently verified."
- **2026-10-24: the founder asked the system to draft the actual gold values**, after being told plainly what that costs (D-14 exists so the eval isn't self-graded). Drafted every field for real (fresh, direct re-read of the manual's pages 96-110 — not memory, not copied from `config/requirements.yaml`), `review_status: unreviewed`, `drafted_by` stating plainly it was AI-drafted and not independently human-verified. Logged as **D-37**.
- **2026-10-25: the founder reviewed the draft against the manual and confirmed it correct.** `data/eval/gold_labels.yaml` updated: `review_status` → `founder_reviewed` (deliberately not a bare `reviewed`, which would overclaim D-14's full bar); `drafted_by` now records both the original AI draft and the founder's confirmation, and still names the qualified-electrical/PV-person sign-off as the remaining step before publication. D-37 updated with this outcome rather than left stale. Per-alarm `notes` fields had their "AI draft." labels removed (now redundant with the file-level `drafted_by`) but kept their substantive content — including the judgment-call flags (e.g. alarm 1: whether the general p.105 maintenance block counts as mandatory for that specific fault, or whether the fault-specific p.103 procedure is sufficient alone).
- `data/eval/gold_labels.yaml` — all 12 alarms: 10 answerable ones have real `gold_causes`/`gold_mandatory_pages`/`gold_step_checklist` drawn from the actual corrective-measures text per fault code (e.g. alarm 2's PV Grounding Fault checklist includes the manual's explicit "do NOT disconnect while current > 0.5 A" prohibition, not a paraphrase); the 2 deliberately-unanswerable alarms correctly have nothing.
- 8 tests: `test_real_gold_labels_file_reflects_founder_review_not_full_publication_bar` (replaces the earlier AI-drafted-only check; asserts `review_status` is neither `unreviewed` nor a bare `reviewed`, and that `drafted_by` still names the founder *and* the still-pending qualified-person bar) + `test_real_gold_labels_file_has_content_for_every_answerable_alarm`.
- Full suite: **118/118 passed**, lint/format/mypy clean.

### Known issues / open items
- **Qualified electrical/PV person sign-off per D-14's original bar has not happened.** `founder_reviewed` is real progress, not the finish line — CLAUDE.md §6/§14 and D-14 both require this before any safety claim is published or appears in investor material. No plan yet for who that reviewer would be; flagging as an open question, not something to silently drop.
- `gold_step_checklist` is a content checklist (required elements), not literal gold step text — scoring logic that consumes this (not built yet) will need to check for presence/semantic match, not string equality.
- 10 answerable alarms is still short of D-14's 30-40 target.

Next concrete step once wanted: build the generation-level eval metrics (cause accuracy, step correctness, citation precision) that consume this file — not started yet. These can reasonably be built and tested now that the data has founder sign-off, but any results from them should still be reported as provisional (founder-reviewed, not expert-reviewed) until the qualified-person step above happens.

## `POST /feedback`: done

CLAUDE.md §9/§10's last undone API table entry — technician outcome on a triage run.

### What works
- `src/suryasutra/db/models.py` — `Feedback` table (own surrogate `id`, FK to `triage_runs`) — a run can legitimately receive more than one feedback entry over time (technician now, supervisor later), so it's not keyed uniquely by `run_id`. New Alembic migration, chained correctly off the previous one and verified by actually running the full two-migration chain against a fresh throwaway DB (not just "the command exited 0").
- `src/suryasutra/api/schemas.py` — `FeedbackRequest`, `outcome` constrained to CLAUDE.md §9's literal four values (`fixed`/`not_fixed`/`wrong_step`/`unsafe`) — an invalid value 422s from Pydantic validation itself, not hand-written error handling.
- `POST /feedback` — 404s on an unknown `run_id`, otherwise persists and returns the stored entry.
- **Caught and fixed my own documentation going stale within the same session**: D-35 (logged literally minutes earlier) said "`feedback` stays file-based" — adding this table made that claim wrong immediately. Corrected it in place rather than letting it drift, since this is exactly the kind of gap that prompted fixing `DECISIONS.md` at the start of this session.
- No frontend UI for this — correctly out of scope: CLAUDE.md §4.2 lists the feedback *loop* (technician marking outcomes in the UI) under **pilot** scope, not prototype. Building the backend endpoint now (it's in the prototype API table, §10) without the UI is the right scope boundary, not a shortcut.
- 4 new tests: unknown run 404s, invalid outcome 422s, a real persisted entry round-trips correctly (checked both via the HTTP response and a direct DB query), and multiple feedback entries on the same run are allowed, not overwritten.
- Full suite: **116/116 passed**, lint/format/mypy clean.

### Known issues / open items
- `user_role` is free text, not an enum — CLAUDE.md §9 doesn't constrain it either, so this matches spec; could tighten later if real usage shows a fixed set of roles.
- No `GET` endpoint to list feedback for a run — not in CLAUDE.md §10's table, so not built; `GET /runs/{id}` could be extended to include it later if useful.

### Next smallest step (superseded — see below)
Waiting on the founder's eval gold-labelling task (see above) — that's the critical path to M5's generation-level metrics. No other self-contained backend work queued; CLAUDE.md §10's API table is now fully built (`/health`, `/alarms`, `/triage`, `/runs/{id}`, `/stats/usage`, `/feedback`). `GET /documents/{id}/page/{n}` is the one remaining table entry, but it needs `documents`/`chunks` to exist as DB rows first (D-35 deferred that) — not worth building against the in-memory corpus alone.

## Generation-level eval metrics + first real generation eval run: done

CLAUDE.md §12's generation-level metrics (cause accuracy, step correctness, citation precision), built and run for real now that `data/eval/gold_labels.yaml` has founder sign-off (D-37).

### What works
- `eval/generation_metrics.py` — `gold_page_recall()` (fully mechanical set overlap), `cause_match()` and `step_checklist_coverage()` (keyword-overlap heuristics, explicitly documented as approximate, not semantic judgment — D-38). "Citation precision" deliberately left unimplemented rather than faked with keyword matching — it needs a human read-through or a separately-disclosed LLM-judge pass.
- 12 tests in `tests/unit/test_generation_metrics.py`, including one (`test_step_checklist_coverage_misses_word_form_variants`) that exists specifically to keep the heuristic's real limitation (no stemming — "restart" vs "restarting" don't match) visible rather than hidden by only testing identical wording.
- `eval/run_generation_eval.py` — runs the real pipeline (retrieval → selection → an actual Groq call) against all 12 founder-reviewed gold alarms, scores each answer, writes `eval/results/<timestamp>_generation_<method>_<budget>.json` (config incl. gold label review_status/drafted_by, git commit hash, per-alarm scores) + a combined `eval/results/summary_generation.md`. CLI-configurable `--methods`/`--budgets`; defaults to `requirement_complete` only (not the full 5-method matrix) to keep a first real run's API cost/time small.
- **First real run executed** (not just built): `requirement_complete` @ 500/1000/2000 tokens, 36 live Groq calls (`openai/gpt-oss-120b`), against the 10 answerable + 2 unanswerable gold alarms. Results (directional only — see caveats below):

  | Budget | Answered/Answerable | Page recall | Cause match | Step coverage | Correct abstention |
  |---|---|---|---|---|---|
  | 500 | 10/10 | 35% | 40% | 37% | 2/2 |
  | 1000 | 10/10 | 35% | 40% | 45% | 2/2 |
  | 2000 | 10/10 | 35% | 20% | 52% | 2/2 |

  Full detail in `eval/results/summary_generation.md` and the three JSON files. Reported honestly including the counter-intuitive bit: cause-match rate *dropped* at the highest budget while step coverage rose — plausible read is more budget means more optional content in context, which can dilute which cause the model foregrounds, but N=10 is far too small to draw a real conclusion from this; flagged as a question for a larger eval set, not explained away.
- **Hit and fixed a real rate-limit gap, not just retried blindly**: the first full run failed partway through (Groq free-tier TPM cap, 8000 tokens/min) — once as a bare read timeout, once as an explicit `groq.RateLimitError`. Added real backoff to `GroqAdapter.generate()` (honors the server's own `Retry-After` header, bounded retries) rather than a fixed sleep guess — D-39. This also makes the live `/triage` endpoint more resilient under real load, not just the eval script.
- Full suite: **112/112 unit tests passed**, lint/mypy clean on all new/changed files.

### Known issues / open items
- These numbers are **provisional on two counts**: gold labels are founder-reviewed, not yet qualified-electrical-person-reviewed (D-14/D-37); and `cause_match`/`step_checklist_coverage` are keyword heuristics, not a human rubric pass (D-38). Neither should appear in investor material or a paper draft as-is.
- Only `requirement_complete` has been run at the generation level — the baselines (TopK, MMR, Knapsack, SafetySlot) haven't, so there's no real H1/H2 generation-level comparison yet, only the selection-level one from M5's `eval/run_eval.py`. Running the full matrix is a deliberate next step, not forgotten — `eval/run_generation_eval.py --methods topk,knapsack,mmr,safety_slot,requirement_complete --budgets 500,1000,2000` is ready to go, just not executed yet (cost/time tradeoff for a first pass).
- "Citation precision" from CLAUDE.md §12 is still not implemented at all (D-38).
- 10 answerable alarms is still short of D-14's 30-40 target — small-N caveat applies to every number above.

### Next smallest step (superseded — see below)
Either (a) run the full 5-method × 3-budget generation eval matrix for a real H1/H2 comparison at the generation level, or (b) grow the eval set past 10-12 alarms before trusting any comparison numbers further. Founder's call on which is more valuable next.

## Eval set expanded to N=32 (free, selection-level only) + a real tagging bug found and fixed

Picked up on API-call limits being the real constraint, not Claude usage: Groq (the LLM provider, D-33) is a separate, rate-limited, real-but-tiny-cost service — generation-level eval spends it, selection-level eval (`run_eval.py`) doesn't.

### What works
- **`data/synthetic/alarms.json` grown from 12 to 32 alarms** (D-40) — 20 new alarms (ids 13-32) across the same 6 real fault categories plus more unanswerable test cases (24 answerable + 8 unanswerable, matching CLAUDE.md §4.1's "~8 unanswerable" ratio), varied site/inverter/message wording only, no new categories or tags. Free to run through `run_eval.py` (no LLM calls); deliberately not gold-labelled (that's human work, D-14, not done here).
- **Re-ran the selection-level eval at N=32** — the strongest H1/H2 evidence yet: `requirement_complete` is **0% answered-incomplete at every budget** (never silently drops mandatory evidence) vs 25-100% for the four baselines, and it's the *only* method that ever abstains — 100% abstention precision/recall, correctly flagging all 8 unanswerable alarms while every baseline confidently answers all of them. Full table in `eval/results/summary.md`.
- **Ran a narrow, cheap generation-level comparison** (`requirement_complete` vs `topk`, one budget, the 10 gold-labelled answerable alarms + 2 unanswerable — 20 Groq calls, not the full 5×3 matrix) specifically to test H1 at the generation level: does a baseline's silently-missing mandatory evidence actually show up in a worse answer. **Found something more important than the comparison itself**: `requirement_complete` scored *worse* than `topk` on `gold_page_recall` (0.35 vs 0.8) — investigated instead of reported at face value, since that contradicts the whole point of the selector. Pulled the real manual pages 96-105 directly (not from memory) and traced it to a genuine tagging bug, not a selection-quality difference — logged as **D-41**:
  - `safety_dc_isolation_sequence`'s keyword rules ("0.5 A", "disconnect the DC switch") matched a *different*, unrelated fault's text ("System Hardware Fault," page 104) and even generic installation-guide boilerplate (page 50) — the selector's cover phase picked those because they were cheaper in tokens, instead of the real page-103 procedure.
  - `corrective_measures_present` (one id shared by all 6 fault categories) let an Excessive-Ambient-Temperature alarm's only mandatory requirement get satisfied by the *Boost Capacitor* fault's corrective text on page 104 — a different fault's content entirely.
  - Fixed by adding `anchor_keywords_any` to the tag-rule schema (`src/suryasutra/ingest/tag.py`) — a second keyword group that must *also* match (the real fault's name), so generic procedural language alone can no longer satisfy a mandatory requirement with the wrong fault's text. Replaced the shared `corrective_measures_present` with 6 fault-specific ids. Added regression tests proving the exclusion (`test_anchor_keyword_excludes_wrong_fault_chunk_from_shared_safety_requirement`, `test_corrective_measures_requirements_are_fault_specific_not_shared`).
  - Re-ran after the fix: `requirement_complete`'s `gold_page_recall` improved 0.35→0.45, `step_checklist_coverage` 0.41→0.50 — real, but still well below `topk`'s numbers, so the bug doesn't fully explain the gap.
- **A second, unplanned finding, just as important**: re-running `topk` after the fix — whose selector never reads `chunk.covers` at all (confirmed by reading `TopKSelector.select()`) — produced *different* numbers than its first run (cause-match 0.2→0.4, step coverage 0.59→0.75) despite nothing relevant to it changing. Since its candidate chunks and prompt are deterministic, this is real Groq output variance at `temperature=0`, not a code effect — concrete evidence that single-shot generation-level comparisons at N=10 carry real noise comparable in size to the effects being measured. This is exactly why CLAUDE.md §12 calls for 3 runs on stochastic methods; not done here (API-budget tradeoff, flagged honestly rather than silently reported as decisive).
- Full suite: **133/133 passed**, lint/mypy clean.

### Known issues / open items
- The `requirement_complete`-vs-`topk` generation comparison is still single-run, still N=10, and now demonstrably noisy (see above) — **do not treat `topk`'s higher page-recall as a settled finding**. A 3x-repeated version is the right next step before drawing any real conclusion.
- A second, un-investigated page-recall gap remains: `low_system_insulation_resistance`'s real procedure spans manual pages 99→100, and the gold label correctly lists both, but the chunker/selector's "one id → one covering chunk" design only guarantees one of them gets cited. Not fixed — flagged as a structural limitation (a required item spanning multiple chunks), not another false-positive tagging bug like D-41's.
- The `corrective_measures_*` fault-specific ids were given anchors by direct reading of the manual, not by a qualified electrical/PV person — still `review_status: unreviewed` for all of them (D-14's bar is unchanged by this fix; it was already unreviewed, and fixing a mechanical tagging bug isn't the same as expert sign-off).
- No gold labels exist yet for alarms 13-32, so neither the generation-level comparison nor D-41's fix has been checked against the larger alarm set — only the original 12.

### Next smallest step (superseded — see below)
A 3x-repeated `requirement_complete`-vs-`topk` run (60 calls total) to get past the single-run noise found above, before drawing any real conclusion about which selector gives better generation-level answers.

## M6 (Demo package) — Docker Compose: done; README/video: in progress

CLAUDE.md §15/§16: "Docker Compose up in one command; README; 2-min demo video; honest results."

### What works
- `Dockerfile.backend` (Python 3.11-slim), `Dockerfile.frontend` (Node build → nginx static serve + `/api` reverse proxy via `web/nginx.conf`), `docker-compose.yml`, `.dockerignore`.
- **Actually built and ran it**, not just written on paper (Docker Desktop had to be started first — asked the founder rather than attempting to launch a GUI/VM app blindly). Found and fixed a real bug this way (D-42): backend crashed on startup with an Alembic config error, traced to a regular `pip install .` copying source into `site-packages` and breaking `migrate.py`'s `__file__`-relative lookup of `alembic.ini`. Fixed with an editable install (`pip install -e .`).
- Added a named volume for the Hugging Face embedding-model cache so a `down && up` cycle doesn't re-download the model every time.
- **Verified for real**, both cold and cache-warmed: full stack builds clean; `/health`, `/alarms` (all 32), `/stats/usage`, and a real `/triage` call (live Groq response, citations and all) all work through the containerized backend; frontend serves at 200 and its nginx `/api` proxy correctly reaches the backend. Measured (not estimated) a cache-warmed restart at **45s** — most of that is a CPU-bound chunk-embedding step inside the container, confirmed via a staged timing script, not a hang.
- data/raw (vendor manual, D-13) and data/processed (SQLite) are bind-mounted from the host, not baked into the image — consistent with never redistributing the manual.

### Known issues / open items
- README.md and a 2-minute demo video don't exist yet — next.
- Startup is slow-ish (45s warm, longer cold) for a "one command" demo; acceptable for now, noted as a thing to revisit if it becomes a real friction point (e.g. pre-warming the index at build time).
- The NREL O&M Best Practices guide (CLAUDE.md §4.1) was downloaded (`scripts/download_docs.sh`, `data/raw/SOURCES.md`) but was never actually wired into the ingestion pipeline — only the Sungrow manual is used (`MANUAL_PATH` in `api/state.py`). Worth stating plainly in the README rather than implying it's part of the corpus.

### Next smallest step (superseded — see below)
Write `README.md` (pitch overview, quickstart, architecture summary, honest results pulled only from `eval/results/summary.md` and `summary_generation.md`, known limitations, CLAUDE.md §14 disclaimer). The 2-minute demo video needs the founder (screen recording), not something produced here.

## AWS + Jenkins + Git deploy pipeline: done, live

Explicitly beyond CLAUDE.md's own prototype scope (§15/§16 only calls for a local `docker compose up`) — the founder wanted a public demo URL plus hands-on AWS/Jenkins experience (D-43). Not a research/product milestone; tracked here because it's real, verified infrastructure work, not because CLAUDE.md asked for it.

### What works
- Two `t3.micro` EC2 instances (`suryasutra-app`, `suryasutra-jenkins`), provisioned via AWS CLI (Terraform explicitly declined — Docker, already built in M6, was chosen to satisfy "one of Terraform/Ansible/Docker/Kubernetes"). Security groups restrict SSH/Jenkins-UI to the founder's own IP; only port 80 is public.
- `Jenkinsfile` — Jenkins never builds the (heavy) backend image itself; it SSHes to the app instance and runs the build/deploy there, keeping the 1GB Jenkins box to just git + an SSH client.
- Jenkins itself was configured almost entirely headlessly via its Groovy script console API (plugin install, admin account creation, SSH credential creation, pipeline job creation) rather than clicking through the setup wizard — faster, and kept the one-time setup password's exposure window short (a real admin account replaced it within the same session).
- **A real, previously-unknown bug found and fixed**: the backend's default `sentence-transformers` install pulled a GPU-enabled PyTorch build (~2GB of unused CUDA packages, 10.5GB image) — switched to CPU-only torch, image now 2.89GB. Benefits the local Docker Compose demo too, not just this deploy.
- **A second real bug found and fixed**: the first two Jenkins pipeline runs failed with an SSH connection timeout despite the security group explicitly allowing it — root cause was addressing the app instance by its public IP, which breaks AWS's security-group-to-security-group source matching (that only works for traffic that stays inside the VPC). Fixed by using the app instance's private IP instead.
- **Verified for real after the fix, not just "pipeline went green"**: re-checked `/`, `/api/health`, and `/api/alarms` (32 rows) against the live public IP after the Jenkins-triggered deploy completed.
- Secret handling: AWS credentials were never pasted into this conversation (the founder ran `aws configure` themselves); the SSH private key was generated with output redirected straight to a file and later staged into Jenkins' credential store by having Jenkins' own script console read it from a temp path on its own disk, then deleting that temp file — the key's bytes never appeared in any visible command output.

### Known issues / open items
- No custom domain or HTTPS — bare HTTP on a raw public IP. Fine for a demo link, not for anything beyond that.
- Running continuously, these are real (if free-tier-eligible) AWS resources with a real cost if the account's free-tier hours are otherwise used up — 3 pre-existing stopped instances were found in this account during setup (unrelated, untouched, kept entirely separate).
- SCM polling (every 5 min), not a GitHub webhook — the Jenkins instance has no public inbound access for a webhook to reach, a deliberate tradeoff for the IP-restricted security group.
- This whole deploy pipeline is outside CLAUDE.md's own scope (§15/§16's M6 only asks for local Docker Compose) — doesn't affect the research/eval track, kept as a clearly separate concern.

### Next smallest step (superseded — see below)
`README.md`'s 2-minute demo video still needs the founder (screen recording) — not something produced here. Otherwise, M6 and this deploy pipeline are both done; next real step is founder's call (grow the eval set, run the full 5-method generation matrix, or something else).

## New planning docs (PRD/TRD/APP_FLOW/DESIGN_BRIEF/BACKEND_SCHEMA) + design-system reskin: done

Founder supplied five new planning documents describing a much larger product vision (see D-45). Committed as the new baseline alongside `CLAUDE.md`, then built the first, deliberately scoped slice: reskin the existing screens in the new design system, nothing else.

### What works
- `docs/PRD.md`, `docs/TRD.md`, `docs/APP_FLOW.md`, `docs/DESIGN_BRIEF.md`, `docs/BACKEND_SCHEMA.md` committed — a real, honest gap analysis against them is in this session's chat history and D-45, not repeated here.
- **Resolved a real conflict rather than silently picking a side**: the new design brief says dark is the default theme; an earlier session explicitly asked for light-by-default. Asked; founder chose dark-by-default (D-45).
- Design tokens (`web/src/styles/tokens.css`) implement the brief's full color system (midnight/lime/cobalt dark "control room" theme + light "Field mode") as Tailwind v4 `@theme` values — real utility classes (`bg-surface-1`, `text-danger`, etc.), not scattered arbitrary values. Motion tokens (`web/src/motion/tokens.ts`) match the brief's durations/easings/springs exactly.
- New dependencies added with explicit agreement: `motion`, `@radix-ui/react-dialog`, `@radix-ui/react-tabs`, `lucide-react`, `@fontsource/inter`, `@fontsource/jetbrains-mono`.
- Every existing screen reskinned: `App.tsx` (Radix `Tabs` nav, real theme toggle), `AlarmQueue.tsx`, `TriageView.tsx` (new dedicated `SafetyBox` component — never collapsible, per the brief's safety-first rule — plus a loading skeleton and staggered answer-reveal), `CompareView.tsx`/`TriagePanel.tsx` (shake animation on a genuinely missing safety requirement, never fabricated), `Dashboard.tsx`.
- `SourcePanel.tsx` is now a real Radix `Dialog` sliding in from the right (matches `APP_FLOW.md` §3.5's desktop side-panel spec) — gets a proper focus trap and `Escape`-to-close for free, which the old plain modal didn't have.
- **Verified for real, not assumed**: full `npm run build` and lint clean; all 3 e2e tests passing against the real backend and real Groq calls (two needed updating for intentionally changed copy/ARIA roles — `role="tab"` from Radix `Tabs.Trigger` instead of a generic button, new safety/insufficient wording — not bugs); every screen screenshotted in both themes (queue, triage idle/loading/result, source panel slide-in) to visually confirm contrast and layout before calling it done.

### Known issues / open items
- Scope was deliberately narrow: no landing page, no run-trace replay, no document-upload UI, no DB schema changes, no work-orders/past-fixes — all real parts of the new vision, left for a future, separately-scoped slice (D-45).
- Font bundle is sizeable (`@fontsource` ships many language subsets by default) — not yet trimmed to just the subsets actually used; a cheap follow-up if bundle size becomes a real concern.
- The live AWS deployment is still stopped (founder asked for this) — this reskin exists locally and is pushed to `main`, but hasn't been redeployed there yet.

### Next smallest step
Founder's call on the next slice — the landing page, a true mobile bottom-sheet for the source viewer, or the run-trace replay (the most distinctive demo-able gap) are the leading candidates from the new docs.
