"""Budgeted, requirement-complete evidence selection (D-06, D-08, CLAUDE.md §6).

Four phases:
1. Cover: greedily pick the chunk minimizing tokens / (|newly covered mandatory
   requirements| * relevance) until every mandatory requirement is covered, or no
   candidate can cover what's left (deterministic given deterministic retrieval,
   satisfying D-25).

   This cost folds relevance in as more than a tie-breaker (see the note on
   `_RELEVANCE_FLOOR` below) — found necessary on real data: two chunks can both
   satisfy the same requirement's keyword tag, but the cheaper one may be a generic,
   unrelated passage while the more relevant (and pricier) one is the actual
   fault-specific procedure. Pure tokens/coverage greedy picked the cheap-but-generic
   chunk every time such a case arose, because exact ties (where the old tie-break
   even applied) essentially never happen on real text. Weighting cost by relevance
   does not weaken the hard mandatory-coverage guarantee — coverage is still all-or-
   nothing and infeasibility still aborts to INSUFFICIENT (D-06); this only changes
   *which* chunk gets picked among ones that validly cover a requirement.
2. Feasibility: INSUFFICIENT if coverage is impossible at all ("no_evidence") or only
   possible over budget B ("over_budget"). Mandatory evidence is never truncated to
   fit — partial mandatory coverage is not treated as a safe answer (D-06).
3. Fill: spend remaining budget on the most relevance/token-efficient candidates that
   cover at least one of *this alarm's own* optional requirements — never on untagged
   content, no matter how well it happens to score. Found necessary on real data: a
   relevance-only fill phase (even with a relative relevance floor) still let in
   content with no declared relationship to the alarm at all, because retrieval
   scores (especially RRF-fused ones) decay too gently with rank for a threshold to
   reliably separate "genuinely relevant" from "coincidentally scored okay." Gating by
   the requirement schema instead of by score means every selected chunk — mandatory
   or optional — has an explicit, nameable reason for being there. Tradeoff: when a
   category's optional list is sparse, the answer may use less than the full budget;
   that's fine, unused budget is not a problem the way a wrong chunk padding it out
   would be. Near-duplicates (cosine similarity > 0.9 to an already-selected chunk)
   are still skipped.
4. Order: safety first, then cause/diagnosis, then procedure, then other — inferred
   from each chunk's `covers` ids via the naming convention established in
   config/requirements.yaml (safety_*, cause_*, check_*/corrective_measures_*).
"""

from suryasutra.ingest.chunk import Chunk
from suryasutra.selection.base import (
    Answered,
    Candidate,
    Insufficient,
    SelectionResult,
    Selector,
    cosine_similarity,
)

_DEDUP_COSINE_THRESHOLD = 0.9

# Floors relevance in the cover-phase cost so a candidate with relevance==0 (or very
# close to it) doesn't produce a division blowup; relevance is a retrieval score, not
# itself validated to be strictly positive by any upstream contract.
_RELEVANCE_FLOOR = 1e-6


def _order_rank(chunk: Chunk) -> int:
    if any(req_id.startswith("safety_") for req_id in chunk.covers):
        return 0
    if any(req_id.startswith("cause_") for req_id in chunk.covers):
        return 1
    if any(req_id.startswith(("check_", "corrective_measures_")) for req_id in chunk.covers):
        return 2
    return 3


class RequirementCompleteSelector(Selector):
    def select(
        self,
        candidates: list[Candidate],
        must: frozenset[str],
        optional: frozenset[str],
        budget: int,
    ) -> SelectionResult:
        cover_order, uncovered = self._cover(candidates, must)

        if uncovered:
            return Insufficient(reason="no_evidence", missing=frozenset(uncovered))

        cover_tokens = sum(c.chunk.tokens for c in cover_order)
        if cover_tokens > budget:
            return self._over_budget(cover_order, must, budget, cover_tokens)

        selected = list(cover_order)
        remaining = [c for c in candidates if c not in cover_order]
        selected_tokens = cover_tokens
        self._fill(selected, remaining, budget, selected_tokens, optional)

        ordered = sorted(selected, key=lambda c: _order_rank(c.chunk))
        return Answered(
            selected=tuple(c.chunk for c in ordered),
            tokens_used=sum(c.chunk.tokens for c in selected),
        )

    @staticmethod
    def _cover(
        candidates: list[Candidate], must: frozenset[str]
    ) -> tuple[list[Candidate], set[str]]:
        remaining = list(candidates)
        uncovered = set(must)
        cover_order: list[Candidate] = []

        while uncovered:
            best: Candidate | None = None
            best_key: float | None = None
            for cand in remaining:
                newly = cand.chunk.covers & uncovered
                if not newly:
                    continue
                relevance = max(cand.relevance, _RELEVANCE_FLOOR)
                key = cand.chunk.tokens / (len(newly) * relevance)
                if best_key is None or key < best_key:
                    best_key = key
                    best = cand
            if best is None:
                break
            remaining.remove(best)
            cover_order.append(best)
            uncovered -= best.chunk.covers & uncovered

        return cover_order, uncovered

    @staticmethod
    def _over_budget(
        cover_order: list[Candidate],
        must: frozenset[str],
        budget: int,
        needed_tokens: int,
    ) -> Insufficient:
        """What would still be missing if we only kept as much of the minimal
        mandatory cover as fits in `budget` (we never actually do this — D-06 — this
        is purely to tell the caller how close they are and what's at stake)."""
        covered_within_budget: set[str] = set()
        running_tokens = 0
        for cand in cover_order:
            if running_tokens + cand.chunk.tokens > budget:
                break
            running_tokens += cand.chunk.tokens
            covered_within_budget |= cand.chunk.covers & must
        missing_if_truncated = must - covered_within_budget
        return Insufficient(
            reason="over_budget",
            missing=frozenset(missing_if_truncated),
            needed_tokens=needed_tokens,
        )

    @staticmethod
    def _fill(
        selected: list[Candidate],
        remaining: list[Candidate],
        budget: int,
        selected_tokens: int,
        optional: frozenset[str],
    ) -> None:
        """Spend remaining budget on relevance/token-efficient candidates — but only
        among ones that cover at least one of this alarm's declared optional
        requirements. Untagged content is never eligible, regardless of score."""
        eligible = [c for c in remaining if c.chunk.covers & optional]
        selected_embeddings = [c.embedding for c in selected if c.embedding is not None]
        fill_order = sorted(
            eligible,
            key=lambda c: -(c.relevance / c.chunk.tokens) if c.chunk.tokens else 0.0,
        )
        for cand in fill_order:
            if selected_tokens + cand.chunk.tokens > budget:
                continue
            if cand.embedding is not None and any(
                cosine_similarity(cand.embedding, emb) > _DEDUP_COSINE_THRESHOLD
                for emb in selected_embeddings
            ):
                continue
            selected.append(cand)
            selected_tokens += cand.chunk.tokens
            if cand.embedding is not None:
                selected_embeddings.append(cand.embedding)
