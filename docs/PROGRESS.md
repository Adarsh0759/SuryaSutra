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

### Next smallest step
M4 is functionally complete per its own done-criterion. Two reasonable directions, not decided: (a) M5 — build the eval runner (`eval/run_eval.py`) and the 30–40-item hand-labelled eval set (D-14) to actually run the formal E0 pilot study the whole research core has been building toward; or (b) add the DB layer (`triage_runs`/`usage` persistence) so the dashboard screen and real cost tracking become possible. Flagging the fork rather than picking silently.
