"""Baseline selectors (D-09) — the comparison point for H1/H2.

These deliberately do NOT check mandatory requirement coverage. That's the entire
point: H1 asks whether relevance-only selection drops mandatory evidence at realistic
budgets. If it never did, RequirementCompleteSelector would have nothing to fix.
"""

from suryasutra.ingest.chunk import Chunk
from suryasutra.selection.base import (
    Answered,
    Candidate,
    SelectionResult,
    Selector,
    cosine_similarity,
)


class TopKSelector(Selector):
    """Greedily add the highest-relevance chunks until the next one wouldn't fit."""

    def select(
        self,
        candidates: list[Candidate],
        must: frozenset[str],
        optional: frozenset[str],
        budget: int,
    ) -> SelectionResult:
        ranked = sorted(candidates, key=lambda c: -c.relevance)
        selected: list[Candidate] = []
        tokens_used = 0
        for cand in ranked:
            if tokens_used + cand.chunk.tokens > budget:
                continue
            selected.append(cand)
            tokens_used += cand.chunk.tokens
        return Answered(selected=tuple(c.chunk for c in selected), tokens_used=tokens_used)


class KnapsackSelector(Selector):
    """Relevance-only 0/1 knapsack: exact optimum of total relevance within budget.

    Unlike TopK's greedy packing, this is provably the best possible relevance sum for
    a given budget — included so the research selector isn't just beating a weak
    baseline. Still has zero concept of mandatory coverage (D-09).
    """

    def select(
        self,
        candidates: list[Candidate],
        must: frozenset[str],
        optional: frozenset[str],
        budget: int,
    ) -> SelectionResult:
        n = len(candidates)
        tokens = [c.chunk.tokens for c in candidates]
        values = [c.relevance for c in candidates]

        dp = [[0.0] * (budget + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            w_i, v_i = tokens[i - 1], values[i - 1]
            for w in range(budget + 1):
                dp[i][w] = dp[i - 1][w]
                if w_i <= w:
                    with_item = dp[i - 1][w - w_i] + v_i
                    dp[i][w] = max(dp[i][w], with_item)

        chosen: list[int] = []
        w = budget
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i - 1][w]:
                chosen.append(i - 1)
                w -= tokens[i - 1]
        chosen.reverse()

        selected = [candidates[i].chunk for i in chosen]
        return Answered(selected=tuple(selected), tokens_used=sum(c.tokens for c in selected))


_MMR_LAMBDA = 0.5  # relevance/diversity balance; a baseline design choice, not tuned


class MMRSelector(Selector):
    """Maximal Marginal Relevance: at each step, pick the candidate maximizing
    `lambda * relevance - (1 - lambda) * max_similarity_to_already_selected`.
    Diversity-aware but, like the other baselines, has no concept of mandatory
    requirement coverage (D-09)."""

    def __init__(self, lambda_: float = _MMR_LAMBDA) -> None:
        self._lambda = lambda_

    def select(
        self,
        candidates: list[Candidate],
        must: frozenset[str],
        optional: frozenset[str],
        budget: int,
    ) -> SelectionResult:
        remaining = list(candidates)
        selected: list[Candidate] = []
        tokens_used = 0

        while remaining:
            best: Candidate | None = None
            best_score: float | None = None
            for cand in remaining:
                if tokens_used + cand.chunk.tokens > budget:
                    continue
                similarities = [
                    cosine_similarity(cand.embedding, s.embedding)
                    for s in selected
                    if cand.embedding is not None and s.embedding is not None
                ]
                max_sim = max(similarities, default=0.0)
                score = self._lambda * cand.relevance - (1 - self._lambda) * max_sim
                if best_score is None or score > best_score:
                    best_score = score
                    best = cand
            if best is None:
                break
            remaining.remove(best)
            selected.append(best)
            tokens_used += best.chunk.tokens

        return Answered(selected=tuple(c.chunk for c in selected), tokens_used=tokens_used)


_SAFETY_SLOT_FRACTION = 0.2  # RAGuard-style fixed quota; a baseline design choice


def _is_safety_chunk(chunk: Chunk) -> bool:
    return any(req_id.startswith("safety_") for req_id in chunk.covers)


class SafetySlotSelector(Selector):
    """RAGuard-style fixed safety slot (D-09): reserve a fixed *fraction* of the
    budget for the highest-relevance safety-tagged chunks, then fill the rest by
    relevance. This can still fail to cover every *specific* mandatory safety
    requirement — a fixed token quota isn't the same as per-requirement coverage,
    which is exactly the gap D-06's hard constraint exists to close."""

    def __init__(self, safety_fraction: float = _SAFETY_SLOT_FRACTION) -> None:
        self._safety_fraction = safety_fraction

    def select(
        self,
        candidates: list[Candidate],
        must: frozenset[str],
        optional: frozenset[str],
        budget: int,
    ) -> SelectionResult:
        safety_budget = int(budget * self._safety_fraction)
        safety_candidates = sorted(
            (c for c in candidates if _is_safety_chunk(c.chunk)), key=lambda c: -c.relevance
        )

        selected: list[Candidate] = []
        tokens_used = 0
        for cand in safety_candidates:
            if tokens_used + cand.chunk.tokens > safety_budget:
                continue
            selected.append(cand)
            tokens_used += cand.chunk.tokens

        remaining = sorted((c for c in candidates if c not in selected), key=lambda c: -c.relevance)
        for cand in remaining:
            if tokens_used + cand.chunk.tokens > budget:
                continue
            selected.append(cand)
            tokens_used += cand.chunk.tokens

        return Answered(selected=tuple(c.chunk for c in selected), tokens_used=tokens_used)
