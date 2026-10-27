"""Generation-level eval (CLAUDE.md §12): runs the real pipeline — retrieval,
selection, and an actual Groq call — against the founder-reviewed gold alarms in
data/eval/gold_labels.yaml, then scores each answer with eval/generation_metrics.py.

This is a separate pass from eval/run_eval.py on purpose (§5: evaluate
retrieval/selection/generation separately, never only end-to-end) and it costs real
API tokens, unlike run_eval.py's selection-only pass — so it only ever runs on the
answerable alarms a human has actually gold-labelled, not the full synthetic set.

The gold data's own review_status (founder_reviewed, not yet qualified-electrical-
person-reviewed — see data/eval/gold_labels.yaml's header and D-14) is carried into
every result file and the summary table, so nothing downstream can quote these numbers
without also seeing that caveat.

Usage: python -m eval.run_generation_eval [--methods m1,m2] [--budgets b1,b2]
"""

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.settings import settings

from eval.generation_metrics import cause_match, gold_page_recall, step_checklist_coverage
from eval.gold_labels import GOLD_LABELS_PATH, GoldLabel, load_gold_labels
from suryasutra.api.state import SELECTORS, AppState
from suryasutra.generation.generate import generate_triage_answer
from suryasutra.generation.prompts.triage_prompt import AlarmInfo
from suryasutra.generation.schema import AnsweredContract
from suryasutra.retrieval.dense import EMBEDDING_MODEL_NAME
from suryasutra.selection.base import Candidate, Insufficient

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "eval" / "results"
DEFAULT_METHODS = ["requirement_complete"]
DEFAULT_BUDGETS = [500, 1000, 2000]


def _git_commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _run_one(state: AppState, method: str, budget: int, alarm_id: int, gold: GoldLabel) -> dict[str, Any]:
    alarm = state.alarms[alarm_id]
    category = state.fault_categories[alarm["category"]]
    selector = state.selector(method)

    results = state.retriever.query(alarm["message"], top_k=40)
    candidates = [Candidate(chunk=r.chunk, relevance=r.score, embedding=r.embedding) for r in results]
    selection = selector.select(candidates, must=category.must, optional=category.optional, budget=budget)

    if isinstance(selection, Insufficient):
        return {
            "alarm_id": alarm_id,
            "answerable": gold.answerable,
            "status": "INSUFFICIENT",
            "reason": selection.reason,
            "gold_page_recall": None,
            "cause_match": None,
            "step_checklist_coverage": None,
        }

    assert state.llm is not None  # caller checks this before starting the run
    alarm_info = AlarmInfo(code=alarm["code"], message=alarm["message"])
    result = generate_triage_answer(
        alarm_info, selection, state.llm, budget=budget, method=method, pricing=state.pricing
    )

    if not isinstance(result, AnsweredContract):
        return {
            "alarm_id": alarm_id,
            "answerable": gold.answerable,
            "status": "INSUFFICIENT",
            "reason": result.reason,
            "gold_page_recall": None,
            "cause_match": None,
            "step_checklist_coverage": None,
        }

    cited_pages: set[int] = set()
    for src in result.sources.values():
        cited_pages.update(range(src.page_start, src.page_end + 1))
    model_causes = [c.cause for c in result.likely_causes]
    step_texts = [s.action for s in result.steps] + [s.text for s in result.safety]

    return {
        "alarm_id": alarm_id,
        "answerable": gold.answerable,
        "status": "ANSWERED",
        "reason": None,
        "gold_page_recall": gold_page_recall(cited_pages, gold.gold_mandatory_pages),
        "cause_match": cause_match(model_causes, gold.gold_causes),
        "step_checklist_coverage": step_checklist_coverage(step_texts, gold.gold_step_checklist),
        "usage": {
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
            "cost_inr": result.usage.cost_inr,
        },
    }


def _summarize(per_alarm: list[dict[str, Any]]) -> dict[str, Any]:
    answerable_rows = [r for r in per_alarm if r["answerable"]]
    unanswerable_rows = [r for r in per_alarm if not r["answerable"]]

    def _mean(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    page_recalls = [r["gold_page_recall"] for r in answerable_rows if r["gold_page_recall"] is not None]
    cause_matches = [1.0 if r["cause_match"] else 0.0 for r in answerable_rows if r["cause_match"] is not None]
    step_coverages = [
        r["step_checklist_coverage"] for r in answerable_rows if r["step_checklist_coverage"] is not None
    ]
    n_answerable = len(answerable_rows)
    n_answered = sum(1 for r in answerable_rows if r["status"] == "ANSWERED")

    return {
        "n_answerable": n_answerable,
        "answered_rate_on_answerable": n_answered / n_answerable if n_answerable else None,
        "mean_gold_page_recall": _mean(page_recalls),
        "cause_match_rate": _mean(cause_matches),
        "mean_step_checklist_coverage": _mean(step_coverages),
        # Abstaining on a gold-labelled answerable alarm is a real failure to flag,
        # not something to silently average away into the other metrics.
        "insufficient_on_answerable_count": n_answerable - n_answered,
        "n_unanswerable_in_set": len(unanswerable_rows),
        "correctly_abstained_on_unanswerable": sum(
            1 for r in unanswerable_rows if r["status"] == "INSUFFICIENT"
        ),
    }


def _write_summary_md(rows: list[dict[str, Any]], timestamp: str, commit_hash: str, gold_status: str) -> None:
    def pct(x: float | None) -> str:
        return f"{x:.0%}" if x is not None else "n/a"

    lines = [
        "# Generation-level eval results",
        "",
        f"Run: `{timestamp}` · commit `{commit_hash}`",
        "",
        (
            f"Gold labels review_status: **{gold_status}** — founder-reviewed, "
            "NOT yet reviewed by a qualified electrical/PV person (D-14). Treat these "
            "numbers as directional, not a publishable result."
        ),
        "",
        (
            "`cause_match` and `step_checklist_coverage` are keyword-overlap heuristics "
            "(eval/generation_metrics.py), not semantic judgment — see that module's "
            "docstring before quoting these numbers anywhere."
        ),
        "",
        (
            "| Method | Budget | Answered/Answerable | Page recall | Cause match | "
            "Step coverage | Abstained on answerable | Correct abstention (unanswerable) |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        s = r["summary"]
        lines.append(
            f"| {r['method']} | {r['budget']} | "
            f"{s['answered_rate_on_answerable'] and pct(s['answered_rate_on_answerable'])} "
            f"({s['n_answerable'] - s['insufficient_on_answerable_count']}/{s['n_answerable']}) | "
            f"{pct(s['mean_gold_page_recall'])} | {pct(s['cause_match_rate'])} | "
            f"{pct(s['mean_step_checklist_coverage'])} | {s['insufficient_on_answerable_count']} | "
            f"{s['correctly_abstained_on_unanswerable']}/{s['n_unanswerable_in_set']} |"
        )
    (RESULTS_DIR / "summary_generation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_generation_eval(methods: list[str], budgets: list[int]) -> None:
    gold = load_gold_labels(GOLD_LABELS_PATH)
    state = AppState()

    if state.llm is None:
        raise SystemExit("GROQ_API_KEY not set — cannot run a real generation eval.")

    commit_hash = _git_commit_hash()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    alarm_ids = sorted(gold.labels.keys())
    rows: list[dict[str, Any]] = []
    for method in methods:
        for budget in budgets:
            per_alarm = [
                _run_one(state, method, budget, alarm_id, gold.labels[alarm_id])
                for alarm_id in alarm_ids
            ]
            summary = _summarize(per_alarm)
            rows.append({"method": method, "budget": budget, "summary": summary})

            record = {
                "config": {
                    "method": method,
                    "budget": budget,
                    "llm_model": settings.llm_model,
                    "embedding_model": EMBEDDING_MODEL_NAME,
                    "git_commit": commit_hash,
                    "timestamp": timestamp,
                    "n_alarms": len(per_alarm),
                    "gold_labels_review_status": gold.review_status,
                    "gold_labels_drafted_by": gold.drafted_by,
                },
                "per_alarm": per_alarm,
                "summary": summary,
            }
            out_path = RESULTS_DIR / f"{timestamp}_generation_{method}_{budget}.json"
            out_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            print(f"{method} @ {budget}: {summary}")

    _write_summary_md(rows, timestamp, commit_hash, gold.review_status)
    print(f"Wrote {len(rows)} result files and summary_generation.md to {RESULTS_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--budgets", default=",".join(str(b) for b in DEFAULT_BUDGETS))
    args = parser.parse_args()

    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    budgets = [int(b.strip()) for b in args.budgets.split(",") if b.strip()]
    unknown = set(methods) - set(SELECTORS)
    if unknown:
        raise SystemExit(f"unknown method(s): {sorted(unknown)}; choose from {sorted(SELECTORS)}")

    run_generation_eval(methods, budgets)
