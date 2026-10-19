from suryasutra.ingest.chunk import Chunk
from suryasutra.selection.base import Answered, Candidate
from suryasutra.selection.baselines import (
    KnapsackSelector,
    MMRSelector,
    SafetySlotSelector,
    TopKSelector,
)


def _chunk(text: str, tokens: int, covers: frozenset[str] = frozenset()) -> Chunk:
    return Chunk(
        text=text, page_start=1, page_end=1, tokens=tokens, doc_type="manual", covers=covers
    )


SELECTOR = TopKSelector()


def test_topk_never_exceeds_budget() -> None:
    candidates = [
        Candidate(chunk=_chunk("A", tokens=60), relevance=0.9),
        Candidate(chunk=_chunk("B", tokens=60), relevance=0.8),
        Candidate(chunk=_chunk("C", tokens=60), relevance=0.7),
    ]

    result = SELECTOR.select(candidates, must=frozenset(), optional=frozenset(), budget=100)

    assert isinstance(result, Answered)
    assert result.tokens_used <= 100


def test_topk_picks_highest_relevance_first() -> None:
    low = Candidate(chunk=_chunk("low relevance", tokens=10), relevance=0.1)
    high = Candidate(chunk=_chunk("high relevance", tokens=10), relevance=0.9)

    result = SELECTOR.select([low, high], must=frozenset(), optional=frozenset(), budget=10)

    assert isinstance(result, Answered)
    assert result.selected == (high.chunk,)


def test_topk_can_drop_mandatory_evidence_this_is_the_point_not_a_bug() -> None:
    """D-09/H1: TopK has no concept of mandatory coverage. A highly-relevant but
    irrelevant-to-safety chunk can crowd out the one chunk that covers a mandatory
    requirement, if the budget is tight. This is the exact failure mode
    RequirementCompleteSelector exists to prevent — documented here, not fixed here."""
    irrelevant_but_relevant_scored = Candidate(
        chunk=_chunk("Generic high-relevance text.", tokens=100), relevance=0.99
    )
    safety = Candidate(
        chunk=_chunk("Isolate DC side.", tokens=100, covers=frozenset({"safety_x"})),
        relevance=0.1,
    )

    result = SELECTOR.select(
        [irrelevant_but_relevant_scored, safety],
        must=frozenset({"safety_x"}),
        optional=frozenset(),
        budget=100,
    )

    assert isinstance(result, Answered)
    assert safety.chunk not in result.selected


# --- KnapsackSelector ---

KNAPSACK = KnapsackSelector()


def test_knapsack_never_exceeds_budget() -> None:
    candidates = [
        Candidate(chunk=_chunk("A", tokens=60), relevance=0.9),
        Candidate(chunk=_chunk("B", tokens=60), relevance=0.8),
        Candidate(chunk=_chunk("C", tokens=60), relevance=0.7),
    ]

    result = KNAPSACK.select(candidates, must=frozenset(), optional=frozenset(), budget=100)

    assert isinstance(result, Answered)
    assert result.tokens_used <= 100


def test_knapsack_finds_provably_better_packing_than_greedy_topk() -> None:
    """Classic knapsack counter-example: greedy-by-relevance picks the single highest
    item and leaves budget unused; the exact optimum combines two smaller items for a
    higher total relevance. This is why Knapsack is a stronger baseline than TopK."""
    a = Candidate(chunk=_chunk("A", tokens=6), relevance=6.0)
    b = Candidate(chunk=_chunk("B", tokens=5), relevance=5.0)
    c = Candidate(chunk=_chunk("C", tokens=5), relevance=5.0)

    topk_result = TopKSelector().select(
        [a, b, c], must=frozenset(), optional=frozenset(), budget=10
    )
    knapsack_result = KNAPSACK.select([a, b, c], must=frozenset(), optional=frozenset(), budget=10)

    assert isinstance(topk_result, Answered)
    assert isinstance(knapsack_result, Answered)
    assert topk_result.selected == (a.chunk,)
    assert set(knapsack_result.selected) == {b.chunk, c.chunk}
    assert knapsack_result.tokens_used == 10


def test_knapsack_can_still_drop_mandatory_evidence() -> None:
    high_relevance_irrelevant = Candidate(chunk=_chunk("Generic text.", tokens=100), relevance=0.99)
    safety = Candidate(
        chunk=_chunk("Isolate DC side.", tokens=100, covers=frozenset({"safety_x"})), relevance=0.1
    )

    result = KNAPSACK.select(
        [high_relevance_irrelevant, safety],
        must=frozenset({"safety_x"}),
        optional=frozenset(),
        budget=100,
    )

    assert isinstance(result, Answered)
    assert safety.chunk not in result.selected


# --- MMRSelector ---

MMR = MMRSelector()


def test_mmr_never_exceeds_budget() -> None:
    candidates = [
        Candidate(chunk=_chunk("A", tokens=60), relevance=0.9, embedding=(1.0, 0.0)),
        Candidate(chunk=_chunk("B", tokens=60), relevance=0.8, embedding=(0.0, 1.0)),
    ]

    result = MMR.select(candidates, must=frozenset(), optional=frozenset(), budget=100)

    assert isinstance(result, Answered)
    assert result.tokens_used <= 100


def test_mmr_prefers_diverse_candidate_over_near_duplicate_of_already_selected() -> None:
    a = Candidate(chunk=_chunk("A", tokens=10), relevance=0.9, embedding=(1.0, 0.0))
    near_dup_of_a = Candidate(chunk=_chunk("B", tokens=10), relevance=0.85, embedding=(0.99, 0.01))
    diverse = Candidate(chunk=_chunk("C", tokens=10), relevance=0.5, embedding=(0.0, 1.0))

    # Budget fits exactly 2 of the 3 items.
    result = MMR.select(
        [a, near_dup_of_a, diverse], must=frozenset(), optional=frozenset(), budget=20
    )

    assert isinstance(result, Answered)
    assert a.chunk in result.selected
    assert diverse.chunk in result.selected
    assert near_dup_of_a.chunk not in result.selected


def test_mmr_can_still_drop_mandatory_evidence() -> None:
    high_relevance_irrelevant = Candidate(chunk=_chunk("Generic text.", tokens=100), relevance=0.99)
    safety = Candidate(
        chunk=_chunk("Isolate DC side.", tokens=100, covers=frozenset({"safety_x"})), relevance=0.1
    )

    result = MMR.select(
        [high_relevance_irrelevant, safety],
        must=frozenset({"safety_x"}),
        optional=frozenset(),
        budget=100,
    )

    assert isinstance(result, Answered)
    assert safety.chunk not in result.selected


# --- SafetySlotSelector ---

SAFETY_SLOT = SafetySlotSelector(safety_fraction=0.2)


def test_safety_slot_never_exceeds_budget() -> None:
    candidates = [
        Candidate(chunk=_chunk("A", tokens=60, covers=frozenset({"safety_a"})), relevance=0.9),
        Candidate(chunk=_chunk("B", tokens=60), relevance=0.8),
    ]

    result = SAFETY_SLOT.select(candidates, must=frozenset(), optional=frozenset(), budget=100)

    assert isinstance(result, Answered)
    assert result.tokens_used <= 100


def test_safety_slot_reserves_budget_for_safety_chunks_even_against_high_relevance_crowding() -> (
    None
):
    crowding = Candidate(chunk=_chunk("Generic high-relevance text.", tokens=100), relevance=0.99)
    safety = Candidate(
        chunk=_chunk("Isolate DC side.", tokens=15, covers=frozenset({"safety_a"})), relevance=0.1
    )

    result = SAFETY_SLOT.select(
        [crowding, safety], must=frozenset({"safety_a"}), optional=frozenset(), budget=100
    )

    assert isinstance(result, Answered)
    assert safety.chunk in result.selected  # the fixed 20-token slot caught it


def test_safety_slot_can_still_miss_a_specific_mandatory_safety_requirement() -> None:
    """The gap D-06 exists to close: a fixed token quota for 'safety' chunks as a
    category doesn't guarantee each *specific* mandatory safety requirement is covered
    if the quota is too small to fit all of them."""
    safety_a = Candidate(
        chunk=_chunk("Covers safety_a.", tokens=15, covers=frozenset({"safety_a"})), relevance=0.9
    )
    safety_b = Candidate(
        chunk=_chunk("Covers safety_b.", tokens=15, covers=frozenset({"safety_b"})), relevance=0.5
    )

    # Overall budget=20 is itself the binding constraint here: the two safety chunks
    # together need 30 tokens, so whichever phase picks them up, only one can fit.
    result = SAFETY_SLOT.select(
        [safety_a, safety_b],
        must=frozenset({"safety_a", "safety_b"}),
        optional=frozenset(),
        budget=20,
    )

    assert isinstance(result, Answered)
    covered = frozenset().union(*(c.covers for c in result.selected))
    assert not ({"safety_a", "safety_b"} <= covered)
