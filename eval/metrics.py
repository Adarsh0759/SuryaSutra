"""Selection-level eval metrics (CLAUDE.md §12, D-10's E0 pilot study).

Pure functions over a selector's result and the alarm's ground truth (mandatory
requirement set, `answerable` flag) — no LLM call needed, matching the architecture
principle that retrieval/selection/generation get separate metrics (CLAUDE.md §5).
Generation-level metrics (cause accuracy, step correctness, citation precision) need
human gold labels per D-14 and are a later, separate step.
"""

from dataclasses import dataclass
from typing import Literal

from suryasutra.selection.base import Answered, Insufficient, SelectionResult

Outcome = Literal["answered_complete", "answered_incomplete", "insufficient"]


def classify(result: SelectionResult, must: frozenset[str]) -> Outcome:
    """`answered_incomplete` is the dangerous case H1 is about: the selector
    confidently answered but silently dropped a mandatory requirement, rather than
    abstaining. D-06's hard constraint means `RequirementCompleteSelector` should
    never produce this outcome; baselines can."""
    if isinstance(result, Insufficient):
        return "insufficient"
    covered = (
        frozenset[str]().union(*(c.covers for c in result.selected))
        if result.selected
        else frozenset()
    )
    return "answered_complete" if must <= covered else "answered_incomplete"


def tokens_used(result: SelectionResult) -> int:
    return result.tokens_used if isinstance(result, Answered) else 0


@dataclass(frozen=True)
class AbstentionConfusion:
    true_positive: int  # correctly abstained on a genuinely unanswerable alarm
    false_positive: int  # abstained on an answerable alarm (overly cautious)
    true_negative: int  # correctly did not abstain on an answerable alarm
    false_negative: int  # did not abstain on an unanswerable alarm (the unsafe case)

    @property
    def precision(self) -> float | None:
        denom = self.true_positive + self.false_positive
        return self.true_positive / denom if denom else None

    @property
    def recall(self) -> float | None:
        denom = self.true_positive + self.false_negative
        return self.true_positive / denom if denom else None


def abstention_confusion(outcomes: list[tuple[Outcome, bool]]) -> AbstentionConfusion:
    """`outcomes`: (classification, alarm_is_answerable) pairs."""
    tp = fp = tn = fn = 0
    for outcome, answerable in outcomes:
        abstained = outcome == "insufficient"
        if abstained and not answerable:
            tp += 1
        elif abstained and answerable:
            fp += 1
        elif not abstained and answerable:
            tn += 1
        else:
            fn += 1
    return AbstentionConfusion(tp, fp, tn, fn)
