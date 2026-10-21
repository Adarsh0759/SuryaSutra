from eval.metrics import Outcome, abstention_confusion, classify, tokens_used

from suryasutra.ingest.chunk import Chunk
from suryasutra.selection.base import Answered, Insufficient


def _chunk(covers: frozenset[str] = frozenset(), tokens: int = 50) -> Chunk:
    return Chunk(
        text="x", page_start=1, page_end=1, tokens=tokens, doc_type="manual", covers=covers
    )


def test_classify_answered_complete_when_must_fully_covered() -> None:
    result = Answered(selected=(_chunk(frozenset({"a", "b"})),), tokens_used=50)

    assert classify(result, must=frozenset({"a", "b"})) == "answered_complete"


def test_classify_answered_incomplete_when_mandatory_requirement_missing() -> None:
    result = Answered(selected=(_chunk(frozenset({"a"})),), tokens_used=50)

    assert classify(result, must=frozenset({"a", "b"})) == "answered_incomplete"


def test_classify_insufficient() -> None:
    result = Insufficient(reason="no_evidence", missing=frozenset({"a"}))

    assert classify(result, must=frozenset({"a"})) == "insufficient"


def test_classify_empty_must_is_always_complete() -> None:
    result = Answered(selected=(), tokens_used=0)

    assert classify(result, must=frozenset()) == "answered_complete"


def test_tokens_used_zero_for_insufficient() -> None:
    result = Insufficient(reason="over_budget", missing=frozenset(), needed_tokens=500)

    assert tokens_used(result) == 0


def test_tokens_used_reads_answered_total() -> None:
    result = Answered(selected=(_chunk(),), tokens_used=123)

    assert tokens_used(result) == 123


def test_abstention_confusion_counts_all_four_cells() -> None:
    outcomes: list[tuple[Outcome, bool]] = [
        ("insufficient", False),  # true positive: correctly abstained
        ("insufficient", True),  # false positive: abstained on an answerable alarm
        ("answered_complete", True),  # true negative: correctly answered
        ("answered_incomplete", False),  # false negative: answered an unanswerable alarm
    ]

    confusion = abstention_confusion(outcomes)

    assert confusion.true_positive == 1
    assert confusion.false_positive == 1
    assert confusion.true_negative == 1
    assert confusion.false_negative == 1
    assert confusion.precision == 0.5
    assert confusion.recall == 0.5


def test_abstention_confusion_precision_recall_none_when_undefined() -> None:
    confusion = abstention_confusion([])

    assert confusion.precision is None
    assert confusion.recall is None
