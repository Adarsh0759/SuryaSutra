import pytest

from suryasutra.generation.schema import Cause, CitedItem, LLMAnswerPayload, Step
from suryasutra.generation.validate import CitationError, validate_citations


def test_validate_citations_passes_when_all_items_cite_valid_ids() -> None:
    payload = LLMAnswerPayload(
        safety=[CitedItem(text="Isolate DC side.", citations=["c1"])],
        steps=[Step(n=1, action="Check fuse.", expected_result="Fuse intact.", citations=["c2"])],
    )

    validate_citations(payload, valid_citation_ids={"c1", "c2"})  # must not raise


def test_validate_citations_rejects_safety_item_with_no_citation() -> None:
    payload = LLMAnswerPayload(safety=[CitedItem(text="Isolate DC side.", citations=[])])

    with pytest.raises(CitationError) as exc_info:
        validate_citations(payload, valid_citation_ids={"c1"})
    assert "safety" in str(exc_info.value)


def test_validate_citations_rejects_step_citing_unknown_chunk_id() -> None:
    payload = LLMAnswerPayload(
        steps=[Step(n=1, action="Check fuse.", expected_result="Fuse intact.", citations=["c99"])]
    )

    with pytest.raises(CitationError) as exc_info:
        validate_citations(payload, valid_citation_ids={"c1", "c2"})
    assert "step 1" in str(exc_info.value)


def test_validate_citations_ignores_likely_causes_per_spec() -> None:
    """CLAUDE.md §10 says the validator checks steps and safety items — not causes."""
    payload = LLMAnswerPayload(
        safety=[CitedItem(text="Isolate DC side.", citations=["c1"])],
        likely_causes=[Cause(cause="Loose connector", confidence="low", citations=[])],
    )

    validate_citations(payload, valid_citation_ids={"c1"})  # must not raise despite uncited cause
