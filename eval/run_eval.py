"""E0 pilot study: selection-level eval across methods x budgets (CLAUDE.md §12, D-10).

Generation is deliberately NOT run here — H1/H2 are about selection quality, and
CLAUDE.md's own architecture principle is to evaluate retrieval/selection/generation
separately (§5), never only end-to-end. Generation-level metrics (cause accuracy, step
correctness, citation precision) need hand-labelled gold data per D-14 and are a later,
separate pass — not fabricated here.

Usage: python -m eval.run_eval
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.metrics import Outcome, abstention_confusion, classify, tokens_used
from suryasutra.api.state import SELECTORS, AppState
from suryasutra.selection.base import Candidate

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "eval" / "results"
BUDGETS = [500, 1000, 2000]


def _git_commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def evaluate_method_at_budget(state: AppState, method: str, budget: int) -> dict[str, Any]:
    selector = state.selector(method)
    per_alarm: list[dict[str, Any]] = []
    outcomes: list[tuple[Outcome, bool]] = []
    total_tokens = 0

    for alarm in state.alarms.values():
        category = state.fault_categories[alarm["category"]]
        results = state.retriever.query(alarm["message"], top_k=40)
        candidates = [
            Candidate(chunk=r.chunk, relevance=r.score, embedding=r.embedding) for r in results
        ]
        result = selector.select(
            candidates, must=category.must, optional=category.optional, budget=budget
        )
        outcome = classify(result, category.must)
        outcomes.append((outcome, alarm["answerable"]))
        tokens = tokens_used(result)
        total_tokens += tokens
        per_alarm.append(
            {
                "alarm_id": alarm["id"],
                "answerable": alarm["answerable"],
                "outcome": outcome,
                "tokens_used": tokens,
            }
        )

    confusion = abstention_confusion(outcomes)
    n = len(per_alarm)
    n_complete = sum(1 for o, _ in outcomes if o == "answered_complete")
    n_incomplete = sum(1 for o, _ in outcomes if o == "answered_incomplete")
    n_insufficient = sum(1 for o, _ in outcomes if o == "insufficient")

    return {
        "method": method,
        "budget": budget,
        "per_alarm": per_alarm,
        "summary": {
            "full_mandatory_coverage_rate": n_complete / n if n else None,
            # The exact metric H1 is about: did the selector confidently answer while
            # silently missing a mandatory requirement, instead of abstaining?
            "answered_incomplete_rate": n_incomplete / n if n else None,
            "insufficient_rate": n_insufficient / n if n else None,
            "mean_tokens_used": total_tokens / n if n else None,
            "abstention_precision": confusion.precision,
            "abstention_recall": confusion.recall,
        },
    }


def _write_summary_md(rows: list[dict[str, Any]], timestamp: str, commit_hash: str) -> None:
    def pct(x: float | None) -> str:
        return f"{x:.0%}" if x is not None else "n/a"

    lines = [
        "# E0 pilot study — selection-level results",
        "",
        f"Run: `{timestamp}` · commit `{commit_hash}`",
        "",
        (
            "Generation-level metrics (cause accuracy, step correctness, citation precision) "
            "are not in this table — they need hand-labelled gold data (D-14), not yet collected."
        ),
        "",
        (
            "| Method | Budget | Full coverage | Answered-incomplete (H1) | Insufficient "
            "| Mean tokens | Abstention P | Abstention R |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        s = r["summary"]
        lines.append(
            f"| {r['method']} | {r['budget']} | {pct(s['full_mandatory_coverage_rate'])} | "
            f"{pct(s['answered_incomplete_rate'])} | {pct(s['insufficient_rate'])} | "
            f"{s['mean_tokens_used']:.0f} | {pct(s['abstention_precision'])} | "
            f"{pct(s['abstention_recall'])} |"
        )
    (RESULTS_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_eval() -> None:
    state = AppState()
    commit_hash = _git_commit_hash()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for method in SELECTORS:
        for budget in BUDGETS:
            row = evaluate_method_at_budget(state, method, budget)
            rows.append(row)

            record = {
                "config": {
                    "method": method,
                    "budget": budget,
                    "embedding_model": "BAAI/bge-small-en-v1.5",
                    "git_commit": commit_hash,
                    "timestamp": timestamp,
                    "n_alarms": len(row["per_alarm"]),
                },
                "per_alarm": row["per_alarm"],
                "summary": row["summary"],
            }
            out_path = RESULTS_DIR / f"{timestamp}_{method}_{budget}.json"
            out_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    _write_summary_md(rows, timestamp, commit_hash)
    print(f"Wrote {len(rows)} result files and summary.md to {RESULTS_DIR}")


if __name__ == "__main__":
    run_eval()
