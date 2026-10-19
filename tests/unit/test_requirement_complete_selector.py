from hypothesis import given, settings
from hypothesis import strategies as st

from suryasutra.ingest.chunk import Chunk
from suryasutra.selection.base import Answered, Candidate, Insufficient
from suryasutra.selection.requirement_complete import RequirementCompleteSelector


def _chunk(text: str, tokens: int, covers: frozenset[str] = frozenset(), page: int = 1) -> Chunk:
    return Chunk(
        text=text, page_start=page, page_end=page, tokens=tokens, doc_type="manual", covers=covers
    )


def _cand(
    chunk: Chunk, relevance: float = 1.0, embedding: tuple[float, ...] | None = None
) -> Candidate:
    return Candidate(chunk=chunk, relevance=relevance, embedding=embedding)


SELECTOR = RequirementCompleteSelector()


def test_answers_and_covers_all_mandatory_when_cover_fits_budget() -> None:
    safety = _cand(_chunk("Isolate DC side.", tokens=50, covers=frozenset({"safety_x"})))
    cause = _cand(_chunk("Likely cause: X.", tokens=50, covers=frozenset({"cause_x"})))

    result = SELECTOR.select(
        [safety, cause], must=frozenset({"safety_x", "cause_x"}), optional=frozenset(), budget=200
    )

    assert isinstance(result, Answered)
    covered = frozenset().union(*(c.covers for c in result.selected))
    assert {"safety_x", "cause_x"} <= covered
    assert result.tokens_used <= 200


def test_insufficient_no_evidence_when_no_candidate_covers_a_mandatory_requirement() -> None:
    unrelated = _cand(_chunk("Clean the air filter.", tokens=20, covers=frozenset({"other"})))

    result = SELECTOR.select(
        [unrelated], must=frozenset({"safety_x"}), optional=frozenset(), budget=1000
    )

    assert isinstance(result, Insufficient)
    assert result.reason == "no_evidence"
    assert result.missing == frozenset({"safety_x"})


def test_insufficient_over_budget_when_minimal_cover_exceeds_budget() -> None:
    safety = _cand(_chunk("Isolate DC side.", tokens=500, covers=frozenset({"safety_x"})))

    result = SELECTOR.select(
        [safety], must=frozenset({"safety_x"}), optional=frozenset(), budget=100
    )

    assert isinstance(result, Insufficient)
    assert result.reason == "over_budget"
    assert result.needed_tokens == 500
    assert "safety_x" in result.missing


def test_never_truncates_mandatory_evidence_even_partially() -> None:
    # Two mandatory reqs, each needing a big chunk; together they exceed budget.
    # The selector must refuse rather than return only one of the two covered.
    a = _cand(_chunk("Req A evidence.", tokens=600, covers=frozenset({"must_a"})))
    b = _cand(_chunk("Req B evidence.", tokens=600, covers=frozenset({"must_b"})))

    result = SELECTOR.select(
        [a, b], must=frozenset({"must_a", "must_b"}), optional=frozenset(), budget=800
    )

    assert isinstance(result, Insufficient)
    assert result.reason == "over_budget"


def test_cover_phase_prefers_relevant_chunk_over_cheaper_but_irrelevant_one() -> None:
    """Regression for a real finding on the Sungrow manual: a generic, unrelated
    passage can satisfy a mandatory tag's keyword rule more cheaply (fewer tokens)
    than the actual fault-specific passage. Pure tokens/coverage greedy picked the
    cheap-irrelevant one every time, because exact-tie tie-breaking almost never
    fires on real text. Relevance must be weighted into the cost itself, not just
    used as a tie-breaker."""
    specific_but_pricier = _cand(
        _chunk(
            "364-395 Boost Capacitor Overvoltage Fault: disconnect AC and DC switches.",
            tokens=454,
            covers=frozenset({"safety_dc_isolation_sequence"}),
            page=103,
        ),
        relevance=0.0325,
    )
    generic_but_cheaper = _cand(
        _chunk(
            "5.1 Safety Instructions: ensure cables are voltage-free before touching DC cables.",
            tokens=323,
            covers=frozenset({"safety_dc_isolation_sequence"}),
            page=47,
        ),
        relevance=0.0112,
    )

    # Budget fits either chunk alone (454 or 323) but not both (777) — forces a real
    # choice for the mandatory slot rather than letting the fill phase add both.
    result = SELECTOR.select(
        [generic_but_cheaper, specific_but_pricier],
        must=frozenset({"safety_dc_isolation_sequence"}),
        optional=frozenset(),
        budget=500,
    )

    assert isinstance(result, Answered)
    assert result.selected == (specific_but_pricier.chunk,)


def test_fill_phase_excludes_untagged_content_even_if_highly_relevant() -> None:
    """Regression for a real finding: a retrieval score alone (even a high one) isn't
    enough to justify filling budget with a chunk — only coverage of a declared
    optional requirement is. An untagged chunk with a near-top relevance score (this
    can genuinely happen — e.g. keyword overlap with the query on an unrelated page)
    must never be used as filler."""
    safety = _cand(
        _chunk("Isolate DC side.", tokens=50, covers=frozenset({"safety_x"})), relevance=0.5
    )
    tagged_optional = _cand(
        _chunk("Likely related corrective step.", tokens=100, covers=frozenset({"opt_a"})),
        relevance=0.3,
    )
    untagged_but_highly_scored = _cand(
        _chunk("Unrelated app installation instructions.", tokens=20), relevance=0.95
    )

    result = SELECTOR.select(
        [safety, tagged_optional, untagged_but_highly_scored],
        must=frozenset({"safety_x"}),
        optional=frozenset({"opt_a"}),
        budget=200,
    )

    assert isinstance(result, Answered)
    assert tagged_optional.chunk in result.selected
    assert untagged_but_highly_scored.chunk not in result.selected


def test_fill_phase_adds_optional_chunks_within_remaining_budget() -> None:
    safety = _cand(
        _chunk("Isolate DC side.", tokens=50, covers=frozenset({"safety_x"})), relevance=0.5
    )
    optional = _cand(
        _chunk("Escalation contact info.", tokens=30, covers=frozenset({"opt_a"})), relevance=0.9
    )

    result = SELECTOR.select(
        [safety, optional], must=frozenset({"safety_x"}), optional=frozenset({"opt_a"}), budget=100
    )

    assert isinstance(result, Answered)
    assert optional.chunk in result.selected
    assert result.tokens_used == 80


def test_fill_phase_skips_near_duplicate_embeddings() -> None:
    safety = _cand(
        _chunk("Isolate DC side.", tokens=50, covers=frozenset({"safety_x"})), relevance=0.5
    )
    first = _cand(
        _chunk("Procedure A.", tokens=30, covers=frozenset({"opt_a"})),
        relevance=0.9,
        embedding=(1.0, 0.0),
    )
    near_dup = _cand(
        _chunk("Procedure A, reworded.", tokens=30, covers=frozenset({"opt_a"})),
        relevance=0.8,
        embedding=(0.99, 0.01),
    )

    result = SELECTOR.select(
        [safety, first, near_dup],
        must=frozenset({"safety_x"}),
        optional=frozenset({"opt_a"}),
        budget=200,
    )

    assert isinstance(result, Answered)
    assert first.chunk in result.selected
    assert near_dup.chunk not in result.selected


def test_deterministic_given_same_input() -> None:
    candidates = [
        _cand(_chunk("A", tokens=50, covers=frozenset({"safety_x"})), relevance=0.5),
        _cand(_chunk("B", tokens=30, covers=frozenset()), relevance=0.9),
        _cand(_chunk("C", tokens=20, covers=frozenset()), relevance=0.9),
    ]

    r1 = SELECTOR.select(candidates, must=frozenset({"safety_x"}), optional=frozenset(), budget=100)
    r2 = SELECTOR.select(candidates, must=frozenset({"safety_x"}), optional=frozenset(), budget=100)

    assert r1 == r2


def test_ordering_puts_safety_chunk_before_cause_and_other() -> None:
    other = _cand(_chunk("Other info.", tokens=10, covers=frozenset()), relevance=0.95)
    cause = _cand(
        _chunk("Cause diagnosis.", tokens=10, covers=frozenset({"cause_x"})), relevance=0.5
    )
    safety = _cand(
        _chunk("Safety isolation.", tokens=10, covers=frozenset({"safety_x"})), relevance=0.1
    )

    result = SELECTOR.select(
        [other, cause, safety],
        must=frozenset({"safety_x", "cause_x"}),
        optional=frozenset(),
        budget=100,
    )

    assert isinstance(result, Answered)
    assert result.selected[0] == safety.chunk


# --- Property-based tests (D-25) ---

_REQ_IDS = ["safety_x", "cause_y", "check_z", "other_w"]

_chunk_strategy = st.builds(
    _chunk,
    text=st.text(min_size=1, max_size=20),
    tokens=st.integers(min_value=1, max_value=50),
    covers=st.sets(st.sampled_from(_REQ_IDS)).map(frozenset),
    page=st.integers(min_value=1, max_value=200),
)

_candidate_strategy = st.builds(
    _cand,
    chunk=_chunk_strategy,
    relevance=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)


@settings(max_examples=100, deadline=None)
@given(
    candidates=st.lists(_candidate_strategy, min_size=0, max_size=12),
    must=st.sets(st.sampled_from(_REQ_IDS)).map(frozenset),
    budget=st.integers(min_value=0, max_value=300),
)
def test_property_never_exceeds_budget(
    candidates: list[Candidate], must: frozenset[str], budget: int
) -> None:
    result = SELECTOR.select(candidates, must=must, optional=frozenset(), budget=budget)
    if isinstance(result, Answered):
        assert result.tokens_used <= budget


@settings(max_examples=100, deadline=None)
@given(
    candidates=st.lists(_candidate_strategy, min_size=0, max_size=12),
    must=st.sets(st.sampled_from(_REQ_IDS)).map(frozenset),
    budget=st.integers(min_value=0, max_value=300),
)
def test_property_never_answers_with_an_uncovered_mandatory_requirement(
    candidates: list[Candidate], must: frozenset[str], budget: int
) -> None:
    result = SELECTOR.select(candidates, must=must, optional=frozenset(), budget=budget)
    if isinstance(result, Answered):
        covered = (
            frozenset().union(*(c.covers for c in result.selected))
            if result.selected
            else frozenset()
        )
        assert must <= covered


@settings(max_examples=100, deadline=None)
@given(
    candidates=st.lists(_candidate_strategy, min_size=0, max_size=12),
    must=st.sets(st.sampled_from(_REQ_IDS)).map(frozenset),
    budget=st.integers(min_value=0, max_value=300),
)
def test_property_deterministic(
    candidates: list[Candidate], must: frozenset[str], budget: int
) -> None:
    r1 = SELECTOR.select(candidates, must=must, optional=frozenset(), budget=budget)
    r2 = SELECTOR.select(candidates, must=must, optional=frozenset(), budget=budget)
    assert r1 == r2
