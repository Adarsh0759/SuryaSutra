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
