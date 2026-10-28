# SuryaSutra — Product Requirements Document (PRD)

> Version 1.0 · 2026-10-28 · Owner: Adarsh
> Related: `CLAUDE.md`, `docs/TRD.md`, `docs/APP_FLOW.md`, `docs/DESIGN_BRIEF.md`, `docs/BACKEND_SCHEMA.md`, `docs/DECISIONS.md`
> Rule: every metric below is a **target to validate**, not a measured result. Measured values come only from `eval/results/summary.md`.

---

## 1. Overview

SuryaSutra is an AI copilot for operations & maintenance (O&M) teams at solar plants. When an inverter or plant alarm fires, it returns a **cited, step-by-step triage plan with a mandatory safety checklist**, built from the plant's manuals, SOPs and past work orders, under a strict **token budget**. If the evidence for a safe answer is missing or does not fit the budget, it **refuses to guess** and lists what is missing.

**One-line pitch:** From alarm to safe action, with the source on every step.

**What it is not:** a monitoring/SCADA platform, a predictive-fault model, or an autonomous control system. It consumes alarms; humans act.

## 2. Problem

| Pain | Who feels it | Today |
|---|---|---|
| Many alarms daily, triaged by hand | Site engineers | Search long vendor PDFs, ask senior staff |
| Knowledge is locked in PDFs and people's memory | Technicians, new hires | Slow, inconsistent fixes |
| Generic AI answers are uncited and can skip safety steps | Everyone | Low trust, safety risk |
| LLM cost grows with alarm volume; Indian-language answers cost more tokens | O&M managers | No visibility into cost per query |

**Context:** inverter vendors and O&M software companies already ship AI assistants (e.g., Huawei FusionSolar, Raptor Maps). SuryaSutra's position is the part they don't advertise: **guaranteed safety-evidence coverage, plant-specific history, and measured cost per alarm.**

## 3. Goals & objectives

**Product goals**
1. G1 — Every answered alarm includes all mandatory safety evidence, by construction.
2. G2 — Every step in an answer cites a source passage the user can open.
3. G3 — The system abstains, and names the missing evidence, instead of guessing.
4. G4 — Cost per alarm is logged and predictable.
5. G5 — Plant history (past fixes) is reused safely.

**Research goal**
- R1 — Measure whether token-budgeted RAG drops safety-critical evidence, and whether hard-coverage selection fixes it at equal cost (see `CLAUDE.md` §3).

**Non-goals (this version)**
- Autonomous resets or any write access to plant equipment.
- Time-series fault prediction.
- Multi-language answers (planned for pilot).
- Mobile native app (responsive web only).

## 4. Users & personas

| Persona | Context | Needs | Success for them |
|---|---|---|---|
| **Ravi — Site technician** | On site, phone, gloves, sun glare, weak network | What to check first, in order, with precautions | Fixes the fault safely on first visit |
| **Meena — O&M engineer** | Control room, desktop, many alarms | Fast triage, consistent procedures, audit trail | Clears queue faster; trusts the citations |
| **Arjun — O&M / asset manager** | Office, weekly reviews | Cost per alarm, safety compliance, trends | Can justify the tool's cost |
| **Faculty / reviewer / investor** | Demo, 5–10 minutes | See the safety guarantee and honest numbers | Understands what is new and what is measured |

## 5. User stories

| ID | As a… | I want to… | So that… | Priority |
|---|---|---|---|---|
| US-01 | engineer | see a queue of incoming alarms with site, inverter and code | I can pick what to triage | P0 |
| US-02 | engineer | open an alarm and get likely causes and ordered steps | I know what to do | P0 |
| US-03 | technician | see safety precautions first, clearly separated | I don't miss them | P0 |
| US-04 | engineer | click any step's citation and see the source page | I can verify it | P0 |
| US-05 | engineer | get "insufficient evidence" with the missing items when the system can't answer safely | I'm never given a guess | P0 |
| US-06 | manager | see tokens, ₹ cost and latency per alarm | I can track spend | P0 |
| US-07 | engineer | see similar past fixes at this plant | I reuse what worked | P1 |
| US-08 | technician | mark the outcome (fixed / not fixed / wrong step / unsafe) | the system learns and wrong steps are flagged | P1 |
| US-09 | reviewer | compare two selection methods side by side on the same alarm and budget | I see the difference | P1 |
| US-10 | engineer | upload a new manual or SOP and have it indexed | the system knows our equipment | P1 |
| US-11 | manager | see a dashboard of cost, coverage and abstention over time | I see trends | P2 |
| US-12 | visitor | read a landing page explaining the product | I understand it in under a minute | P2 |

## 6. Requirements

### 6.1 Functional

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| FR-01 | Alarm ingestion from CSV (prototype) | P0 | Alarms appear in queue with `is_synthetic` badge when synthetic |
| FR-02 | Requirement resolution per fault category | P0 | Each alarm maps to must/optional requirements from `config/requirements.yaml` |
| FR-03 | Hybrid retrieval (BM25 + dense) with brand/model filters | P0 | Top-N candidates returned with scores and provenance |
| FR-04 | Requirement-complete selection under budget B | P0 | Never exceeds B; never answers with an uncovered mandatory requirement |
| FR-05 | Abstention | P0 | Returns `INSUFFICIENT` with `reason` and `missing_requirements` |
| FR-06 | Cited structured answer | P0 | Every safety item and step cites ≥1 selected chunk; validator enforces |
| FR-07 | Source viewer | P0 | Clicking a citation opens the document page with the passage highlighted |
| FR-08 | Usage logging | P0 | Input/output tokens, token source, ₹ cost, latency stored per run |
| FR-09 | Baseline selectors (Top-k, MMR, Knapsack, Safety-slot) | P0 | Same interface; selectable per run |
| FR-10 | Compare mode | P1 | Same alarm, two methods, same budget; missing safety evidence highlighted |
| FR-11 | Past work orders as optional evidence | P1 | Never satisfy mandatory requirements; capped share of B |
| FR-12 | Feedback and close-as-work-order | P1 | Outcome stored; closed run creates a `work_orders` row |
| FR-13 | Document upload and ingestion | P1 | PDF parsed, chunked, tagged, indexed; status visible |
| FR-14 | Dashboard | P2 | Charts from logged runs only |
| FR-15 | Public landing page with animations | P2 | Meets `DESIGN_BRIEF.md` motion rules and accessibility |
| FR-16 | Auth + multi-tenant | Pilot | Every query scoped by `tenant_id` |

### 6.2 Non-functional

| ID | Requirement | Target (to validate) |
|---|---|---|
| NFR-01 | Triage latency (p95), API model | ≤ 8 s end to end |
| NFR-02 | Triage view usable on a 360 px phone | No horizontal scroll; tap targets ≥ 44 px |
| NFR-03 | Accessibility | WCAG 2.2 AA; full keyboard use; reduced-motion support |
| NFR-04 | Reproducibility | Every eval run logs config, model/embedding versions, git hash |
| NFR-05 | Safety | 0 answered runs with uncovered mandatory requirement (enforced by tests) |
| NFR-06 | Privacy | No customer prompts logged in production mode; secrets only in `.env` |
| NFR-07 | Performance (web) | Lighthouse performance ≥ 85 on landing; animations at 60 fps |

## 7. User experience (summary)

- Safety box always on top of the answer, rendered first and never collapsed.
- Every step has a citation chip; the source opens in a side panel (desktop) or bottom sheet (mobile).
- "Insufficient evidence" is a first-class state, not an error.
- Synthetic data is always labelled.
- Motion explains state (selection, loading, comparison); it never delays safety information.
- Full spec: `docs/DESIGN_BRIEF.md`. Screens and paths: `docs/APP_FLOW.md`.

## 8. Success metrics

All targets are hypotheses to test; report measured values with their source.

| Metric | Definition | Target | Source |
|---|---|---|---|
| Mandatory-coverage rate (answered runs) | % answered runs with all mandatory requirements in context | 100% by construction | `triage_runs`, tests |
| Cause accuracy (top-3) | Gold cause in top-3 likely causes | Measure vs baselines | Eval set |
| Citation precision | Claims supported by their cited chunk | Measure | Eval set (rubric) |
| Abstention precision / recall | On unanswerable items | Measure | Eval set |
| Cost per alarm | Mean ₹ per triage run | Measure; compare at equal budgets | `usage` |
| Time to first correct action | From alarm open to correct first step | Measure in pilot | Pilot study |
| Technician-reported outcome | % runs marked "fixed" | Measure in pilot | `feedback` |

## 9. Release plan

| Release | Contents | Gate |
|---|---|---|
| R0 — Research core | Ingestion, retrieval, 6 selectors, generation, eval CLI | Selector invariant tests pass |
| R1 — Demo | API + React app (queue, triage, compare, dashboard), landing page with motion | `docker compose up` works; README results from real runs only |
| R2 — Pilot | Real plant data, auth, Postgres/Qdrant, Indic answers | Plant partner + expert-reviewed requirements |

## 10. Risks & open questions

| Risk | Mitigation |
|---|---|
| Vendor assistants are "good enough" | Customer interviews before pilot features (D-29) |
| Safety labels unreviewed | Expert reviewer is a gate (D-34) |
| Synthetic data overstates gains | Label everything synthetic; seek real plant data |
| Animations hurt performance or accessibility | Motion budget + reduced-motion rules in design brief |

Open questions:
- Which inverter brands do target plants use most?
- Do engineers want desktop-first or phone-first triage?
- Is per-MW pricing acceptable to O&M contractors?
