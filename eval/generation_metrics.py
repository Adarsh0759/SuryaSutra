"""Generation-level eval metrics (CLAUDE.md §12), checked against the hand-verified
gold data in data/eval/gold_labels.yaml (D-14; founder_reviewed as of 2026-10-25, not
yet qualified-person-reviewed — see that file's own header before citing any number
computed here as a finished result).

`gold_page_recall` is fully mechanical: does the answer's own citations include the
pages a human confirmed are mandatory? No judgment call involved.

`cause_match` and `step_checklist_coverage` are transparent, inspectable keyword-
overlap heuristics — deliberately NOT a black-box LLM-judge call. An LLM grading
another LLM's output just relocates the self-grading problem D-14 is about, and a
keyword heuristic is at least honest about being approximate rather than dressed up as
semantic judgment. These are fast signals for iteration, not a substitute for a human
rubric pass (CLAUDE.md §12's "step correctness (rubric)" implies a rubric pass is the
real bar) — every function here says so in its own docstring, not just this module one.

"Citation precision" in CLAUDE.md §12's literal sense — does the cited chunk's text
actually *support* the specific claim being made, not just share keywords with it — is
not implemented here. It needs either a human read-through or a carefully-flagged
LLM-judge pass; faking it with keyword overlap would be more misleading than useful,
so it's left as an open item rather than approximated badly.
"""

import re

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "to", "of",
    "and", "or", "in", "on", "at", "for", "with", "if", "it", "this", "that", "its",
    "by", "as", "but", "not", "do", "does", "did", "has", "have", "had", "will",
    "would", "should", "can", "could", "may", "might", "must", "then", "than", "so",
}  # fmt: skip


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _overlap_ratio(candidate: str, gold: str) -> float:
    """Fraction of gold's keywords that appear in candidate — asymmetric on purpose:
    a candidate that says more than the gold phrase shouldn't be penalised for it."""
    gold_words = _keywords(gold)
    if not gold_words:
        return 0.0
    candidate_words = _keywords(candidate)
    return len(gold_words & candidate_words) / len(gold_words)


def gold_page_recall(cited_pages: set[int], gold_mandatory_pages: list[int]) -> float | None:
    """Fraction of gold mandatory pages actually present among the answer's cited
    pages. None (not 0.0) when there are no gold pages to check against — e.g. a
    deliberately-unanswerable alarm, where "recall" isn't a meaningful question."""
    if not gold_mandatory_pages:
        return None
    gold = set(gold_mandatory_pages)
    return len(gold & cited_pages) / len(gold)


def cause_match(model_causes: list[str], gold_causes: list[str], threshold: float = 0.4) -> bool:
    """Heuristic, not semantic judgment (see module docstring). True if any of the
    model's stated causes clears `threshold` keyword-overlap with any gold cause.
    `threshold` is a chosen heuristic parameter, not a validated one."""
    if not gold_causes or not model_causes:
        return False
    return any(
        _overlap_ratio(candidate, gold) >= threshold
        for candidate in model_causes
        for gold in gold_causes
    )


def step_checklist_coverage(
    step_texts: list[str], gold_checklist: list[str], threshold: float = 0.4
) -> float | None:
    """Heuristic, not semantic judgment (see module docstring). Fraction of
    gold_checklist items that clear `threshold` keyword-overlap against at least one
    of the answer's step/safety texts. None when there's no checklist to check
    against (e.g. a deliberately-unanswerable alarm)."""
    if not gold_checklist:
        return None
    if not step_texts:
        return 0.0
    covered = sum(
        1
        for item in gold_checklist
        if any(_overlap_ratio(text, item) >= threshold for text in step_texts)
    )
    return covered / len(gold_checklist)
