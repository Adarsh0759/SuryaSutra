"""Budget is a hard resource constraint for every selector, baseline or not — only
mandatory-requirement coverage differentiates them (D-09). This checks the one
property all five should share, across randomized inputs."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from suryasutra.ingest.chunk import Chunk
from suryasutra.selection.base import Answered, Candidate, Selector
from suryasutra.selection.baselines import (
    KnapsackSelector,
    MMRSelector,
    SafetySlotSelector,
    TopKSelector,
)
from suryasutra.selection.requirement_complete import RequirementCompleteSelector

_REQ_IDS = ["safety_x", "cause_y", "check_z", "other_w"]

_chunk_strategy = st.builds(
    lambda text, tokens, covers, page: Chunk(
        text=text, page_start=page, page_end=page, tokens=tokens, doc_type="manual", covers=covers
    ),
    text=st.text(min_size=1, max_size=20),
    tokens=st.integers(min_value=1, max_value=50),
    covers=st.sets(st.sampled_from(_REQ_IDS)).map(frozenset),
    page=st.integers(min_value=1, max_value=200),
)

_candidate_strategy = st.builds(
    Candidate,
    chunk=_chunk_strategy,
    relevance=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    embedding=st.none(),
)

_SELECTORS: list[Selector] = [
    TopKSelector(),
    KnapsackSelector(),
    MMRSelector(),
    SafetySlotSelector(),
    RequirementCompleteSelector(),
]


@pytest.mark.parametrize("selector", _SELECTORS, ids=lambda s: type(s).__name__)
@settings(max_examples=40, deadline=None)
@given(
    candidates=st.lists(_candidate_strategy, min_size=0, max_size=10),
    must=st.sets(st.sampled_from(_REQ_IDS)).map(frozenset),
    budget=st.integers(min_value=0, max_value=200),
)
def test_no_selector_ever_exceeds_budget(
    selector: Selector, candidates: list[Candidate], must: frozenset[str], budget: int
) -> None:
    result = selector.select(candidates, must=must, optional=frozenset(), budget=budget)
    if isinstance(result, Answered):
        assert result.tokens_used <= budget
