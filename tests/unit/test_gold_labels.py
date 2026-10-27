from pathlib import Path

import pytest
from eval.gold_labels import GoldLabel, GoldLabelSet, load_gold_labels, write_template
from pydantic import ValidationError

REAL_TEMPLATE_PATH = Path(__file__).parents[2] / "data" / "eval" / "gold_labels.yaml"


def test_write_template_then_load_round_trips(tmp_path: Path) -> None:
    alarms = [
        {"id": 1, "answerable": True},
        {"id": 2, "answerable": False},
    ]
    path = tmp_path / "gold_labels.yaml"

    write_template(path, alarms)
    result = load_gold_labels(path)

    assert result.review_status == "unreviewed"
    assert set(result.labels.keys()) == {1, 2}
    assert result.labels[1].answerable is True
    assert result.labels[1].gold_causes == []
    assert result.labels[2].answerable is False


def test_write_template_never_pre_fills_gold_fields(tmp_path: Path) -> None:
    """The whole point of D-14: this tool must never invent gold data itself."""
    alarms = [{"id": 1, "answerable": True}]
    path = tmp_path / "gold_labels.yaml"

    write_template(path, alarms)
    result = load_gold_labels(path)

    label = result.labels[1]
    assert label.gold_causes == []
    assert label.gold_mandatory_pages == []
    assert label.gold_step_checklist == []
    assert label.notes == ""


def test_gold_label_accepts_filled_in_values() -> None:
    label = GoldLabel(
        alarm_id=1,
        answerable=True,
        gold_causes=["Overvoltage on the DC side"],
        gold_mandatory_pages=[103],
        gold_step_checklist=["Isolate DC side", "Wait for 0.5 A threshold"],
        notes="Reviewed against manual page 103 directly.",
    )

    assert label.gold_causes == ["Overvoltage on the DC side"]
    assert label.gold_mandatory_pages == [103]


def test_gold_label_requires_alarm_id_and_answerable() -> None:
    with pytest.raises(ValidationError):
        GoldLabel.model_validate({"gold_causes": []})


def test_load_real_gold_labels_file_parses_without_error() -> None:
    """The actual gold labels file — still the original 12-alarm gold-labelled subset
    even after data/synthetic/alarms.json grew to 32 (D-40; the extra 20 are free for
    selection-level eval but have no gold labels yet). Confirms the tooling genuinely
    works end to end, not just in a tmp_path fixture."""
    if not REAL_TEMPLATE_PATH.exists():
        pytest.skip(
            "data/eval/gold_labels.yaml not generated yet (run `python -m eval.gold_labels`)"
        )

    result = load_gold_labels(REAL_TEMPLATE_PATH)

    assert len(result.labels) == 12
    assert result.labels[11].answerable is False
    assert result.labels[12].answerable is False


def test_real_gold_labels_file_reflects_founder_review_not_full_publication_bar() -> None:
    """D-14 integrity check, updated once the founder actually reviewed the initial
    AI draft (2026-10-25): review_status must reflect founder-level sign-off, but must
    NOT claim the full D-14 bar is met — that requires a qualified electrical/PV
    person's review too, which hasn't happened. This is what stops an intermediate
    review state from silently being read as "fully reviewed" / publication-ready."""
    if not REAL_TEMPLATE_PATH.exists():
        pytest.skip("data/eval/gold_labels.yaml not generated yet")

    result = load_gold_labels(REAL_TEMPLATE_PATH)

    assert result.review_status == "founder_reviewed"
    assert result.review_status != "unreviewed"
    assert result.review_status != "reviewed"  # would overclaim the qualified-person bar
    assert result.drafted_by is not None
    assert "founder" in result.drafted_by.lower()
    assert "qualified electrical" in result.drafted_by.lower()  # still-pending bar stays visible


def test_real_gold_labels_file_has_content_for_every_answerable_alarm() -> None:
    """The draft actually has substance for each answerable alarm, not just parses —
    and deliberately has nothing for the unanswerable ones."""
    if not REAL_TEMPLATE_PATH.exists():
        pytest.skip("data/eval/gold_labels.yaml not generated yet")

    result = load_gold_labels(REAL_TEMPLATE_PATH)

    for alarm_id, label in result.labels.items():
        if label.answerable:
            assert label.gold_causes, f"alarm {alarm_id} has no gold_causes"
            assert label.gold_mandatory_pages, f"alarm {alarm_id} has no gold_mandatory_pages"
            assert label.gold_step_checklist, f"alarm {alarm_id} has no gold_step_checklist"
        else:
            assert label.gold_causes == []
            assert label.gold_mandatory_pages == []
            assert label.gold_step_checklist == []


def test_gold_label_set_keyed_by_alarm_id() -> None:
    gold_set = GoldLabelSet(
        review_status="unreviewed",
        labels={1: GoldLabel(alarm_id=1, answerable=True)},
    )

    assert gold_set.labels[1].alarm_id == 1
