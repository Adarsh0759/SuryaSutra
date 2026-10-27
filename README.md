# SuryaSutra

*From alarm to safe action, with the source on every step.*

SuryaSutra is an AI copilot for operations & maintenance (O&M) teams at Indian
utility-scale and large C&I solar plants. When an inverter or plant alarm fires,
SuryaSutra retrieves the relevant evidence from the plant's own documents (inverter
manuals, fault-code tables, safety procedures) and returns a **cited, step-by-step
triage plan with a mandatory safety checklist**, under a strict **token budget** so
cost per alarm stays low at fleet scale. If the evidence needed for a safe answer is
missing or doesn't fit the budget, it **refuses to guess** and says exactly what's
missing, instead of answering anyway.

This is a research prototype, not a finished product. See [Status & known
limitations](#status--known-limitations) before relying on anything here.

## The research question

Large plants generate many SCADA/inverter alarms a day; technicians triage them by
searching long vendor PDFs. Generic chatbots give confident, uncited, sometimes unsafe
answers, and cost too much per query at fleet scale.

**Question:** under a strict token budget, does evidence selection with *hard
per-requirement coverage constraints* — and abstention when those constraints are
infeasible — produce more complete, safer answers than relevance-based selection, at
equal token cost?

This isn't a claim that budgeted selection itself is novel (it isn't — see
`docs/DECISIONS.md`'s D-01-series entries for how this is positioned against prior
work like RAGuard and sufficient-context abstention). The claimed novelty is narrower:
**hard mandatory-requirement coverage + infeasibility-triggered abstention that names
the missing requirements**, evaluated on a real (if currently synthetic-alarm) solar
O&M fault-code corpus.

## Architecture

```
React (Vite) web app — alarm queue, triage view, cost dashboard
            │ REST (JSON), proxied through nginx's /api in Docker
FastAPI backend
  /triage: alarm → requirement resolver → hybrid retriever (BM25 + dense, RRF-fused)
           → budgeted selector (cover mandatory → fill by optional → dedupe)
               └─ INSUFFICIENT? → abstain, name the missing requirements
           → LLM generator (Groq) → citation validator → usage/cost logger
SQLite (triage_runs, usage, alarms, feedback) · in-memory corpus (chunks rebuilt from
the PDF + requirements.yaml at startup — not yet persisted as DB rows)
```

Five selection methods share one interface so they're swappable in the UI and in eval:
`TopKSelector`, `MMRSelector`, `KnapsackSelector`, `SafetySlotSelector` (RAGuard-style
fixed safety quota), and `RequirementCompleteSelector` (this project's own method).

Full design rationale for every non-obvious choice is in `docs/DECISIONS.md` (42
dated decision records as of this writing) — that file, not this README, is the
source of truth for *why* something is built the way it is.

## Quickstart (Docker Compose)

```bash
git clone https://github.com/Adarsh0759/SuryaSutra.git
cd SuryaSutra

cp .env.example .env
# edit .env: set GROQ_API_KEY (console.groq.com — free tier works)

./scripts/download_docs.sh   # fetches the vendor manual into data/raw/ (not committed — see D-13)

docker compose up --build
```

Then open **http://localhost:5173**.

First startup takes a couple of minutes (downloading the embedding model + building
the retrieval index from the manual). Measured, not estimated: a cache-warmed restart
(`docker compose down && docker compose up`) came up in **45s** on the machine this
was built on — most of that is a CPU-bound chunk-embedding step inside the container,
not the download. The backend API docs are at **http://localhost:8000/docs**.

The alarm queue is seeded from `data/synthetic/alarms.json` — every alarm there is
synthetic and labelled as such in the UI; fault codes are real (drawn from the actual
manual), but the alarm *instances* (site, inverter, timestamp) are invented.

## Results

**Nothing below is a finished research result.** Both eval layers run on a small,
currently-synthetic alarm set; see [Status & known limitations](#status--known-limitations).

### Selection-level (free — no LLM calls, full 32-alarm set)

From `eval/results/summary.md` (reproduce with `python -m eval.run_eval`):

| Method | Budget | Full mandatory coverage | Answered-incomplete (H1 failure mode) | Abstention precision / recall |
|---|---|---|---|---|
| topk | 500 / 1000 / 2000 | 59% / 62% / 66% | 41% / 38% / 34% | n/a (never abstains) |
| mmr | 500 / 1000 / 2000 | 59% / 59% / 59% | 41% / 41% / 41% | n/a (never abstains) |
| knapsack | 500 / 1000 / 2000 | 0% / 9% / 28% | 100% / 91% / 72% | n/a (never abstains) |
| safety_slot | 500 / 1000 / 2000 | 59% / 62% / 69% | 41% / 38% / 31% | n/a (never abstains) |
| **requirement_complete** | 500 / 1000 / 2000 | **75% / 75% / 75%** | **0% / 0% / 0%** | **100% / 100%** |

`requirement_complete` is the only method that never silently drops a mandatory
requirement at any budget, and the only one that ever abstains — it correctly flags
all 8 deliberately-unanswerable alarms in the set, while every baseline confidently
answers all of them with zero abstentions. "Full coverage" tops out at 75% (not 100%)
because the other 25% of the set is the unanswerable alarms, correctly routed to
abstention instead of a forced answer.

### Generation-level (costs real LLM calls — narrow, single-run comparison)

From `eval/results/summary_generation.md` (`requirement_complete` vs `topk`, budget
1000, the 10 gold-labelled answerable alarms + 2 unanswerable):

| Method | Page recall | Cause match | Step coverage | Correct abstention (of 2 unanswerable) |
|---|---|---|---|---|
| requirement_complete | 45% | 20% | 50% | 2/2 |
| topk | 80% | 40% | 75% | 0/2 |

**Read this table with real caution, not as a conclusion.** `cause_match` and `step
coverage` are keyword-overlap heuristics, not semantic judgment (see
`eval/generation_metrics.py`'s docstring). More importantly: re-running `topk` alone —
whose selector never even reads the tags this project tunes — produced *different*
numbers between two otherwise-identical runs, demonstrating real Groq output variance
at `temperature=0` large enough to rival the differences in this table (full story in
`docs/DECISIONS.md` D-41). A 3×-repeated version of this comparison is the honest next
step before treating `topk`'s lead here as real.

## Status & known limitations

- **All alarm and work-order data is synthetic**, clearly labelled as such in the UI
  and in `data/synthetic/`. Fault codes are real (from the actual vendor manual);
  alarm instances are invented.
- **Gold eval labels are founder-reviewed, not yet reviewed by a qualified
  electrical/PV person** (`data/eval/gold_labels.yaml`) — per this project's own rule
  (D-14), nothing derived from them should be treated as a safety claim or a finished
  research result yet.
- **Eval set is small**: 32 alarms for the free selection-level eval, 12 (10
  answerable) for the generation-level eval — short of this project's own 30-40 target.
- **Requirement tagging (`config/requirements.yaml`) is `review_status: unreviewed`
  everywhere** — real vendor text, not fabricated, but not yet checked by a qualified
  electrical/PV person.
- **Only one source document is actually used.** The NREL PV O&M Best Practices guide
  was downloaded but was never wired into the retrieval corpus — only the inverter
  vendor's own manual is indexed right now.
- **No cost, customer, or accuracy numbers appear anywhere in this repo that weren't
  measured** — unmeasured numbers are written as `TBD (not yet measured)`, not
  invented. The tables above are the actual, reproducible output of the eval scripts.
- **Single-tenant, no auth, SQLite.** Multi-tenant, Postgres/Qdrant, and an auth layer
  are pilot-stage work (see `docs/DECISIONS.md` D-35), not built yet.
- **"Citation precision"** (does a cited chunk's text actually support the specific
  claim made, not just share keywords) is not implemented — it needs a human
  read-through or a carefully-disclosed LLM-judge pass, not a keyword approximation.

## Roadmap

- **Prototype (here):** one inverter brand, synthetic alarms, hybrid retrieval,
  budgeted selection with abstention, cited generation, cost logging, local Docker
  Compose demo.
- **Pilot (next, needs a real plant partner):** real anonymised alarm logs, 2-3
  inverter brands, Postgres + Qdrant, auth, multi-tenant, Hindi/Tamil/Gujarati answer
  mode, technician feedback loop.
- **Out of scope until explicitly decided:** autonomous control actions, live SCADA
  write access, predictive fault detection from time-series data.

## Safety disclaimer

SuryaSutra's output is a recommendation to support qualified personnel, not a
substitute for site safety procedures, lockout/tagout, or a qualified electrical/PV
person's judgment. Do not act on a safety step from this system without following your
site's own procedures.

## Reproducing the eval tables above

```bash
python -m eval.run_eval                                    # selection-level, free, full alarm set
python -m eval.run_generation_eval --methods requirement_complete,topk --budgets 1000  # costs real Groq API calls
```

Every run writes config (model/embedding versions, git commit hash) alongside results
to `eval/results/` for reproducibility; only the summary tables are committed (see
`.gitignore`).
