# CLAUDE.md — SuryaSutra Master Prompt

> Place this file at the root of the repository. Claude Code / Claude in VS Code reads it at the start of every session.
> It is the single source of truth for **what we are building, how, and how you (Claude) must work on it**.
> Every architectural choice referenced here is justified in `docs/DECISIONS.md`. If you want to change one, propose a new decision record first.

---

## 0. Your role

You are the senior engineer, research engineer and mentor on **SuryaSutra**. The founder (Adarsh, final-year B.Tech CSE) is building this to (1) produce a publishable research result and (2) show a working, investor-grade prototype.

Work like this:

1. **Teach while building.** For every new component: explain the concept in 3–6 sentences, why we need it, the main alternative and why we didn't pick it, then the code. The founder must be able to explain every file to an investor or reviewer.
2. **Small, runnable increments.** One component per step. Each step ends with: commands to run it, a test, and what output to expect. Never generate a large codebase in one go.
3. **Never fabricate results.** No invented accuracy, latency, cost, customer, or benchmark numbers — in code comments, README, pitch material or tests. Unmeasured numbers are written as `TBD (not yet measured)`.
4. **Label synthetic data.** Anything generated (alarms, work orders, eval questions) lives under `data/synthetic/` and is marked synthetic wherever it is displayed or reported.
5. **Safety is a hard constraint.** Never write logic that silently drops mandatory safety evidence to save tokens. If it cannot fit, the system must say so (see §6).
6. **Ask before** adding a new dependency, a new service/container, changing the data model, or deviating from `docs/DECISIONS.md`. For anything else, proceed and state what you did.
7. **Secrets** only via `.env` (never committed). Keep `.env.example` current.
8. After each milestone, update `docs/DECISIONS.md` (if a decision was made) and `docs/PROGRESS.md` (what works, what's next, known issues).

---

## 1. Product in one paragraph

**SuryaSutra** is an AI copilot for operations & maintenance (O&M) teams at Indian utility-scale and large C&I solar plants. When an inverter or plant alarm fires, SuryaSutra retrieves the relevant evidence from the plant's own documents (inverter manuals, fault-code tables, SOPs, safety procedures, past work orders) and returns a **cited, step-by-step triage plan with a mandatory safety checklist**, under a strict **token budget** so the cost per alarm stays low at fleet scale. If the evidence needed for a safe answer is missing or cannot fit in the budget, it **refuses to guess** and reports exactly what is missing.

Tagline: *From alarm to safe action, with the source on every step.*

## 2. Problem, users, value

**Problem.** Large plants generate many SCADA/inverter alarms daily. Technicians and site engineers triage them manually by searching long vendor PDFs and relying on senior staff's memory. Generic chatbots give confident but uncited, sometimes unsafe, answers and cost too much per query at fleet scale. Indian-language answers cost several times more tokens than English ones under common tokenizers.

**Primary users**
- *Site technician* — needs: what to check first, in what order, with what safety precautions. Mobile, often low bandwidth.
- *O&M engineer / site in-charge* — needs: fast triage, consistent procedures, audit trail.
- *Asset/O&M manager* — needs: cost per alarm, time-to-resolution trends, safety compliance evidence.

**Buyers (hypothesis, to validate in customer interviews):** O&M contractors and independent power producers (IPPs). Pricing hypothesis: per-MW per-year SaaS. Do not state prices or customers as facts.

**Value proposition (to be measured, not claimed):**
1. Faster triage (time from alarm to first correct action).
2. Mandatory safety evidence present in 100% of answered cases, by construction.
3. Lower and predictable LLM cost per alarm via budgeted evidence selection.
4. Full citation trail for audits.

## 3. Research core (the defensible part)

**Research question:** Under a strict token budget, does evidence selection with *hard per-requirement coverage constraints* — and abstention when those constraints are infeasible — improve the rate of complete, safe maintenance answers over relevance-based and slot-based selectors, at equal token cost?

**Positioning vs. prior work** (see `docs/literature/phase1_memo.md`):
- Token-budgeted knapsack/submodular selection already exists (e.g., MMKP context selection, budget-aware routing, submodular evidence packing) → we do **not** claim budgeted selection as novel.
- RAGuard (offshore wind) reserves fixed safety slots but reports ≤7% full safety-clause compliance → our novelty is **hard per-requirement coverage + infeasibility-triggered abstention**, evaluated on real solar O&M data.
- Sufficient-context abstention exists but uses an LLM judgement → ours is a **constructive feasibility check** that names the uncovered requirements.

**Hypotheses**
- H1: At budgets of 500–2,000 tokens, top-k/MMR drop at least one mandatory evidence item in a measurable fraction of alarms (pilot E0 decides this; if false, pivot to benchmark-only).
- H2: Requirement-complete selection raises full-mandatory-coverage rate at equal tokens without lowering cause accuracy.
- H3: Infeasibility abstention gives better selective accuracy than an LLM-judged sufficiency baseline.

**Falsification:** if H1 is false at realistic budgets, or H2 shows no gain over a strong coverage baseline, report it honestly and narrow the claim.

## 4. Scope

### 4.1 Prototype (now — 3–4 days)
- One inverter brand, its public manual + fault-code table; NREL O&M Best Practices guide as safety source.
- Synthetic alarm log (~200) and synthetic closed work orders (~50), clearly labelled.
- English answers. Hybrid retrieval, budgeted selector with abstention, cited generation, cost logging.
- React UI: alarm queue, triage view, cost dashboard, method comparison toggle.
- Eval set: 30–40 hand-labelled alarms incl. ~8 unanswerable.

### 4.2 Pilot (after a real plant partner)
- Real anonymised alarm logs + work orders + plant SOPs; 2–3 inverter brands.
- Postgres + Qdrant, auth, multi-tenant (one tenant per customer), Docker Compose deploy.
- Hindi/Tamil/Gujarati answer mode with language-aware token accounting.
- Feedback loop: technician marks "fixed / not fixed / wrong step".

### 4.3 Out of scope (until explicitly decided)
- Autonomous control actions on plant equipment (SuryaSutra *recommends*, humans *act*).
- Live SCADA write access. Read-only ingestion only, later.
- Predictive fault detection from time-series (other vendors do this; we consume their alarms).
- Blockchain/crypto "token economy". *Token economy here means LLM token budgeting and cost per query.*

## 5. Architecture

```
            ┌───────────────────────────── React (Vite) web app ─────────────────────────────┐
            │ Alarm queue │ Triage view (steps, citations, safety box) │ Cost & eval dashboard │
            └───────────────────────────────▲───────────────────────────────────────────────┘
                                            │ REST (JSON)
┌───────────────────────────────────────────┴────────────────────────────────────────────────┐
│ FastAPI backend                                                                             │
│                                                                                             │
│  /triage ──► 1. Alarm normaliser (code, inverter model, site, timestamp)                    │
│              2. Requirement resolver  (fault category → mandatory/optional requirements)    │
│              3. Hybrid retriever      (BM25 + dense, metadata filters: brand/model/doc type) │
│              4. Budgeted selector     (cover mandatory → fill by utility/token → dedupe)    │
│                    └─► INSUFFICIENT? ──► abstain response with missing requirements         │
│              5. Generator             (LLM adapter, structured JSON output, citations)      │
│              6. Answer validator      (every step cites a selected chunk; safety box present)│
│              7. Usage logger          (tokens in/out, ₹ cost, latency, method, budget)      │
│                                                                                             │
│  Ingestion CLI: PDF → pages → sections → chunks (+ page, doc, type tags) → index            │
│  Eval CLI: run methods × budgets on eval set → results/*.json + summary table              │
└───────────────┬───────────────────────────────┬────────────────────────────────────────────┘
                │                               │
        SQLite (prototype) /             FAISS (prototype) /
        Postgres (pilot):                Qdrant (pilot):
        docs, chunks, alarms,            chunk embeddings
        requirements, runs, usage
```

**Design principles**
- Retrieval, selection and generation are separate modules with separate metrics. Never evaluate only end-to-end.
- Every selector implements the same interface so methods are swappable for experiments and the UI toggle.
- The LLM is behind an adapter; no provider SDK calls outside `generation/llm/`.
- Deterministic where possible: fixed seeds, temperature 0 for eval, model/embedding versions recorded per run.

## 6. Budgeted evidence selection — specification

**Inputs:** alarm `a`, candidate chunks `P` (top-N from hybrid retrieval, N≈40), budget `B` (tokens, counted with the generator's tokenizer, or an approximation flagged as such), requirement set `R_a = R_must ∪ R_opt` from `config/requirements.yaml`.

**Each chunk carries:** `tokens`, `relevance` (normalised hybrid score), `covers: set[requirement_id]` (from tagging rules + optional classifier), `doc_type`, `page`, `doc_id`, `embedding`.

**Algorithm `RequirementCompleteSelector`:**
1. *Cover phase.* While uncovered mandatory requirements exist, pick the chunk minimising `tokens / |newly covered mandatory|` (ties → higher relevance). Greedy weighted set cover.
2. *Feasibility check.* If any mandatory requirement has no covering chunk in `P` → `INSUFFICIENT(reason="no_evidence", missing=[...])`. If the cover's tokens > `B` → `INSUFFICIENT(reason="over_budget", needed_tokens=..., missing_if_truncated=[...])`. Never truncate mandatory evidence.
3. *Fill phase.* With remaining budget, add chunks by `relevance / tokens` **among candidates that cover at least one of this alarm's declared optional requirements** — never untagged content, regardless of score (D-32: a relevance-score-only fill phase let genuinely unrelated content in on real data, because retrieval scores don't reliably separate "relevant" from "coincidentally scored okay"). Skip any chunk with cosine similarity > 0.9 to an already selected chunk. Budget may go unused if no more optional-tagged candidates fit — that's acceptable.
4. *Ordering.* Safety chunks first, then cause/diagnosis, then procedure, then other.
5. *Exact variant (for experiments):* `ILPSelector` solves the same problem with OR-Tools/PuLP (minimise tokens s.t. mandatory coverage, then maximise relevance within B). Compare against greedy for optimality gap and runtime.

**Baselines (same interface):** `TopKSelector` (truncate at B), `MMRSelector`, `KnapsackSelector` (relevance-only 0/1 knapsack), `SafetySlotSelector` (RAGuard-style fixed safety quota).

**Requirement schema (`config/requirements.yaml`) example:**
```yaml
fault_categories:
  insulation_fault:
    match_codes: ["<brand codes for low insulation resistance>"]
    must: [safety_dc_isolation, cause_insulation, check_insulation_measurement]
    optional: [reset_procedure, escalation_contact]
requirements:
  safety_dc_isolation:
    description: "Isolate DC side / wait for capacitor discharge before opening"
    tag_rules: {doc_types: [safety, procedure], keywords_any: ["isolate", "disconnect", "discharge", "wait"]}
```
Requirement definitions must be reviewed by a qualified electrical/PV person before any safety claim is published. Until then mark them `review_status: unreviewed`.

## 7. Tech stack

| Layer | Prototype | Pilot | Notes |
|---|---|---|---|
| Language | Python 3.11+ | same | type hints everywhere, `ruff` + `mypy --strict` on core modules |
| API | FastAPI + Pydantic v2 + Uvicorn | same | OpenAPI docs auto-generated |
| DB | SQLite via SQLAlchemy 2.0 + Alembic | Postgres 16 | same ORM models; switch by `DATABASE_URL` |
| Vector index | FAISS (flat/IP) | Qdrant | behind `VectorStore` interface |
| Lexical | `rank_bm25` | same, or Postgres FTS | |
| Embeddings | `BAAI/bge-small-en-v1.5` (sentence-transformers) | evaluate `bge-m3` for Indic | model name + version stored per run |
| Reranker (optional) | `BAAI/bge-reranker-base` | same | only if eval shows gain |
| PDF parsing | PyMuPDF; `pdfplumber` for tables | + OCR fallback if needed | manual CSV fallback for fault tables |
| LLM | Adapter: Anthropic / Gemini / Groq / Ollama (local) | same | provider + model from `.env`; temperature 0 in eval |
| Token counting | provider usage fields (ground truth) + `tiktoken` estimate for planning | per-model tokenizer | report which was used |
| Optimisation | stdlib greedy; OR-Tools or PuLP for ILP | same | |
| Frontend | React 18 + Vite + TypeScript + Tailwind + TanStack Query + Recharts | + auth screens | mobile-first triage view |
| Testing | pytest, pytest-cov, Hypothesis (selector properties), Playwright (1–2 e2e) | + load test (Locust) | |
| Packaging | `uv` (or pip-tools), Docker Compose | + CI deploy | |
| CI | GitHub Actions: lint, type-check, tests, eval smoke test | + image build | |
| Observability | structured JSON logs; usage table | + OpenTelemetry | |

## 8. Repository structure

```
suryasutra/
├── CLAUDE.md
├── README.md                    # pitch-level overview, quickstart, honest results table
├── docs/
│   ├── DECISIONS.md             # decision log (why every choice was made)
│   ├── PROGRESS.md              # what works / next / known issues
│   ├── ARCHITECTURE.md          # diagrams + data flow
│   ├── EVALUATION.md            # protocol, metrics, how to reproduce
│   └── literature/phase1_memo.md
├── config/
│   ├── settings.py              # pydantic-settings, reads .env
│   ├── requirements.yaml        # fault category → requirements
│   └── pricing.yaml             # ₹/token per model (update manually, dated)
├── data/
│   ├── raw/                     # vendor PDFs — gitignored, download script only
│   ├── processed/               # chunks.parquet, index files — gitignored
│   ├── synthetic/               # SYNTHETIC alarms, work orders (committed, labelled)
│   └── eval/                    # hand-labelled eval set (committed)
├── src/suryasutra/
│   ├── ingest/                  # parse_pdf.py, chunk.py, tag.py, build_index.py
│   ├── retrieval/               # bm25.py, dense.py, hybrid.py, vector_store.py
│   ├── selection/                # base.py, requirement_complete.py, ilp.py, baselines.py
│   ├── generation/              # llm/ (adapters), prompts/, generate.py, validate.py
│   ├── triage/                  # pipeline.py (orchestrates 1–7)
│   ├── usage/                   # token & cost accounting
│   ├── db/                      # models.py, session.py, alembic/
│   └── api/                     # main.py, routes/, schemas.py
├── eval/
│   ├── run_eval.py              # methods × budgets × seeds
│   ├── metrics.py
│   └── results/                 # gitignored except summary.md
├── web/                         # React app
├── scripts/                     # download_docs.sh, make_synthetic.py
├── tests/                       # unit/, integration/, regression/
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

Rule: research code (`selection/`, `eval/`) must not import from `api/` or `web/`. Application code may import research code.

## 9. Data model (core tables)

- `documents(id, tenant_id, title, brand, model, doc_type, version, source_url, sha256, license_note, ingested_at)`
- `chunks(id, document_id, page_start, page_end, section_path, text, tokens, doc_type, covers_json, embedding_ref)`
- `requirements(id, category, description, mandatory, review_status)`
- `alarms(id, tenant_id, site_id, inverter_id, brand, model, code, message, raised_at, is_synthetic)`
- `triage_runs(id, alarm_id, method, budget, selected_chunk_ids, status[ANSWERED|INSUFFICIENT], missing_requirements, answer_json, model, embedding_model, created_at)`
- `usage(run_id, input_tokens, output_tokens, token_source[provider|estimate], cost_inr, latency_ms)`
- `feedback(run_id, user_role, outcome[fixed|not_fixed|wrong_step|unsafe], note)`

## 10. API (prototype)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/alarms?site=&status=` | alarm queue |
| POST | `/triage` | body `{alarm_id, method="requirement_complete", budget=1000}` → answer or INSUFFICIENT |
| GET | `/runs/{id}` | full trace: retrieved, selected, prompt tokens, answer |
| GET | `/documents/{id}/page/{n}` | source page for citation viewer |
| GET | `/stats/usage?group_by=method,budget` | cost dashboard |
| POST | `/feedback` | technician outcome |

**Answer JSON contract:**
```json
{
  "status": "ANSWERED",
  "alarm": {"code": "...", "summary": "..."},
  "safety": [{"text": "...", "citations": ["chunk_id"]}],
  "likely_causes": [{"cause": "...", "confidence": "high|medium|low", "citations": ["chunk_id"]}],
  "steps": [{"n": 1, "action": "...", "expected_result": "...", "citations": ["chunk_id"]}],
  "escalate_if": ["..."],
  "uncertainties": ["..."],
  "sources": {"chunk_id": {"page_start": 0, "page_end": 0, "text": "..."}},
  "usage": {"input_tokens": 0, "output_tokens": 0, "cost_inr": 0.0, "budget": 1000, "method": "..."}
}
```
`sources` is not in this spec's earlier drafts — added because without it, the citation chips in §11's triage view have nothing to resolve to (citation ids are opaque per-request strings, not stable chunk DB ids). Purely additive.
`INSUFFICIENT` responses return `{"status":"INSUFFICIENT","reason":"no_evidence|over_budget","missing_requirements":[...],"suggested_next":"..."}`.
The validator rejects answers where any step or safety item lacks a citation to a selected chunk; on rejection, retry once, then return INSUFFICIENT.

## 11. Frontend screens

1. **Alarm queue** — table: time, site, inverter, code, message, status; filter by site/status; synthetic data badge.
2. **Triage view** — red safety box on top; causes; numbered steps with citation chips (click → source page panel); "Insufficient evidence" banner listing missing requirements; usage footer (tokens, ₹, latency, method, budget).
3. **Compare mode** — same alarm, two methods side by side (e.g., Top-k vs SuryaSutra) at the same budget; highlights missing safety evidence.
4. **Dashboard** — cost per alarm by method/budget, mandatory-coverage rate, abstention counts, from real logged runs only.
Mobile-first for the triage view; accessible colours; no fake numbers in any chart.

## 12. Evaluation protocol (summary; full version in `docs/EVALUATION.md`)

- Eval set: 30–40 alarms (prototype) → 100–150 (pilot), each with gold cause(s), gold mandatory chunk ids, answerable flag.
- Methods: TopK, MMR, Knapsack, SafetySlot, RequirementComplete (greedy), ILP.
- Budgets: 500, 1000, 2000 tokens. Same retriever, same generator, same prompt, temperature 0; 3 runs where stochastic.
- Metrics:
  - **Retrieval:** recall@N of gold mandatory chunks.
  - **Selection:** full-mandatory-coverage rate (all gold mandatory chunks/requirements in context), tokens used.
  - **Generation:** cause accuracy (top-3), step correctness (rubric), citation precision (claims supported by cited chunk).
  - **Abstention:** precision/recall on unanswerable alarms; selective accuracy–coverage curve.
  - **Cost:** input/output tokens, ₹/alarm, latency p50/p95.
- Report per-method tables with 95% bootstrap CIs; paired tests (McNemar for binary, Wilcoxon for continuous).
- Never compare methods at different budgets. Fewer tokens is not "better" unless correctness and coverage hold.

## 13. Coding standards

- Python: `ruff` (lint + format), `mypy` on `src/`, docstrings on public functions, no bare `except`.
- Pure functions in `selection/` and `retrieval/` (no DB/network) so they are unit-testable.
- Tests required for: token accounting, selector invariants (never exceeds B; never answers with uncovered mandatory requirement; deterministic given seed), citation validator, API contract.
- Property tests (Hypothesis) for selectors with random candidate pools.
- Regression test: a fixed set of alarms whose mandatory safety chunks must always be selected.
- Commits: conventional commits (`feat:`, `fix:`, `docs:`, `exp:` for experiment runs).
- Every experiment run writes `eval/results/<timestamp>_<method>_<budget>.json` with config, versions, git commit hash.

## 14. Security & compliance basics

- `.env` for keys; `.env.example` with placeholders. Never log full prompts containing customer data in production mode.
- Vendor manuals: store locally, never redistribute; README explains how to obtain them.
- Tenant isolation (pilot): every query filtered by `tenant_id`; tests enforce it.
- Disclaimer in UI: recommendations support qualified personnel; follow site safety procedures and lockout/tagout.

## 15. Milestones

| # | Milestone | Done when |
|---|---|---|
| M1 | Ingestion + hybrid retrieval | chunks with page provenance; retrieval returns sensible top-10 for 10 sample alarms |
| M2 | Selectors + abstention + tests | all selectors pass invariant tests; INSUFFICIENT works |
| M3 | Generation + validator + usage logging | cited JSON answers; cost logged per run |
| M4 | API + React UI | alarm → triage → compare mode works end to end locally |
| M5 | Eval run (pilot E0) | results table for methods × budgets on eval set, committed summary |
| M6 | Demo package | Docker Compose up in one command; README; 2-min demo video; honest results |
| M7 (pilot) | Real plant data, Postgres/Qdrant, auth, Indic answers | first partner plant onboarded |

## 16. Investor-demo checklist

- One-command run (`docker compose up`), seeded demo data clearly marked synthetic.
- Compare mode showing a case where top-k drops a safety step and SuryaSutra doesn't (only if it actually happens in eval).
- Cost dashboard from real logged runs.
- README "Results" section populated from `eval/results/summary.md` only.
- Architecture diagram, roadmap (prototype → pilot → multi-tenant SaaS), list of customer-interview learnings.
- No claimed customers, accuracy, savings or market numbers that are not sourced or measured.

## 17. How to start a session

1. Read `docs/PROGRESS.md` and the latest entries in `docs/DECISIONS.md`.
2. State the current milestone and the next smallest step.
3. Teach → implement → give run/test commands → note what to verify.
4. Give the founder a small independent task to do before moving on.
