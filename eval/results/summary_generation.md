# Generation-level eval results

Run: `20261025T122607Z` · commit `7657054e350b31323957fcb287a04ae25b218d88`

Gold labels review_status: **founder_reviewed** — founder-reviewed, NOT yet reviewed by a qualified electrical/PV person (D-14). Treat these numbers as directional, not a publishable result.

`cause_match` and `step_checklist_coverage` are keyword-overlap heuristics (eval/generation_metrics.py), not semantic judgment — see that module's docstring before quoting these numbers anywhere.

| Method | Budget | Answered/Answerable | Page recall | Cause match | Step coverage | Abstained on answerable | Correct abstention (unanswerable) |
|---|---|---|---|---|---|---|---|
| requirement_complete | 1000 | 100% (10/10) | 45% | 20% | 50% | 0 | 2/2 |
| topk | 1000 | 100% (10/10) | 80% | 40% | 75% | 0 | 0/2 |
