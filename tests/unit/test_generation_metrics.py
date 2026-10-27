from eval.generation_metrics import cause_match, gold_page_recall, step_checklist_coverage


def test_gold_page_recall_full_match() -> None:
    assert gold_page_recall(cited_pages={99, 100, 103}, gold_mandatory_pages=[99, 100]) == 1.0


def test_gold_page_recall_partial_match() -> None:
    assert gold_page_recall(cited_pages={99}, gold_mandatory_pages=[99, 100]) == 0.5


def test_gold_page_recall_no_match() -> None:
    assert gold_page_recall(cited_pages={50}, gold_mandatory_pages=[99, 100]) == 0.0


def test_gold_page_recall_none_when_no_gold_pages() -> None:
    assert gold_page_recall(cited_pages={99}, gold_mandatory_pages=[]) is None


def test_cause_match_true_on_real_overlap() -> None:
    model_causes = ["Overvoltage condition affecting the inverter's boost capacitor"]
    gold_causes = ["Boost capacitor overvoltage fault"]

    assert cause_match(model_causes, gold_causes) is True


def test_cause_match_false_on_unrelated_text() -> None:
    model_causes = ["Meter communication cable is loose"]
    gold_causes = ["Boost capacitor overvoltage fault"]

    assert cause_match(model_causes, gold_causes) is False


def test_cause_match_false_when_either_list_empty() -> None:
    assert cause_match([], ["Boost capacitor overvoltage fault"]) is False
    assert cause_match(["Some cause"], []) is False


def test_step_checklist_coverage_full() -> None:
    """Note: the heuristic does exact-keyword matching, not stemming — "restart" and
    "restarting" are different tokens to it. That's a real, documented limitation
    (module docstring), not something this test should paper over by picking only
    identical word forms; see test_step_checklist_coverage_misses_word_form_variants
    below for the honest failure case."""
    steps = [
        "Disconnect the AC and DC switches, including battery switches if present",
        "Wait 15 minutes then restart the system",
    ]
    checklist = [
        "Disconnect AC and DC switches (and battery switches if present)",
        "Wait 15 minutes then restart the system",
    ]

    assert step_checklist_coverage(steps, checklist) == 1.0


def test_step_checklist_coverage_misses_word_form_variants() -> None:
    """Honest demonstration of the heuristic's real limitation: 'restart' vs
    'restarting' don't match as the same concept under exact-keyword overlap. This is
    why these numbers are a fast approximate signal, not a substitute for a human
    rubric pass (module docstring) — this test exists so the limitation stays visible,
    not hidden by only ever testing identical wording."""
    steps = ["Wait 15 minutes then restart the system"]
    checklist = ["Wait 15 minutes before closing switches and restarting"]

    coverage = step_checklist_coverage(steps, checklist)

    assert coverage == 0.0


def test_step_checklist_coverage_partial() -> None:
    steps = ["Disconnect the AC and DC switches"]
    checklist = [
        "Disconnect AC and DC switches",
        "Contact Sungrow Customer Service if the fault persists",
    ]

    assert step_checklist_coverage(steps, checklist) == 0.5


def test_step_checklist_coverage_zero_when_no_step_texts() -> None:
    assert step_checklist_coverage([], ["Disconnect AC and DC switches"]) == 0.0


def test_step_checklist_coverage_none_when_no_checklist() -> None:
    assert step_checklist_coverage(["Some step"], []) is None
