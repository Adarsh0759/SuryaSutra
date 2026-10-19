from pathlib import Path

import pytest
import yaml

from suryasutra.ingest.chunk import Chunk
from suryasutra.ingest.tag import Requirement, covers, load_requirements

REQUIREMENTS_PATH = Path(__file__).parents[2] / "config" / "requirements.yaml"


def test_load_requirements_reads_real_config_file() -> None:
    requirements = load_requirements(REQUIREMENTS_PATH)

    assert "safety_dc_isolation_sequence" in requirements
    req = requirements["safety_dc_isolation_sequence"]
    assert req.review_status == "unreviewed"
    assert "manual" in req.doc_types
    assert any("0.5 A" in kw for kw in req.keywords_any)


def test_covers_matches_on_doc_type_and_keyword() -> None:
    requirements = {
        "safety_dc_isolation_sequence": Requirement(
            id="safety_dc_isolation_sequence",
            description="Isolate DC side before opening.",
            review_status="unreviewed",
            doc_types=frozenset({"manual", "safety"}),
            keywords_any=("disconnect the dc switch", "0.5 a"),
        ),
    }
    chunk = Chunk(
        text="Disconnect the DC switch only when current drops below 0.5 A.",
        page_start=104,
        page_end=104,
        tokens=20,
        doc_type="manual",
    )

    assert covers(chunk, requirements) == frozenset({"safety_dc_isolation_sequence"})


def test_covers_excludes_wrong_doc_type() -> None:
    requirements = {
        "r1": Requirement(
            id="r1",
            description="x",
            review_status="unreviewed",
            doc_types=frozenset({"safety"}),
            keywords_any=("isolate",),
        ),
    }
    chunk = Chunk(
        text="Isolate the DC side.", page_start=1, page_end=1, tokens=5, doc_type="manual"
    )

    assert covers(chunk, requirements) == frozenset()


def test_covers_excludes_missing_keyword() -> None:
    requirements = {
        "r1": Requirement(
            id="r1",
            description="x",
            review_status="unreviewed",
            doc_types=frozenset(),
            keywords_any=("isolate",),
        ),
    }
    chunk = Chunk(
        text="Check insulation resistance.", page_start=1, page_end=1, tokens=5, doc_type="manual"
    )

    assert covers(chunk, requirements) == frozenset()


def test_covers_requirement_with_no_rules_never_matches() -> None:
    requirements = {
        "r1": Requirement(
            id="r1",
            description="x",
            review_status="unreviewed",
            doc_types=frozenset(),
            keywords_any=(),
        ),
    }
    chunk = Chunk(text="Anything at all.", page_start=1, page_end=1, tokens=3, doc_type="manual")

    assert covers(chunk, requirements) == frozenset()


def test_real_fault_chunk_from_manual_is_tagged_correctly() -> None:
    requirements = load_requirements(REQUIREMENTS_PATH)
    chunk = Chunk(
        text=(
            "364-395 Boost Capacitor Overvoltage Fault Corrective Measures\n"
            "1. Disconnect the AC and DC switches, and disconnect the battery side "
            "switches if there are batteries. Close the AC and DC switches in turn "
            "15 minutes later and restart the system.\n"
            "2. If the fault persists, please contact Sungrow Power Customer Service."
        ),
        page_start=103,
        page_end=103,
        tokens=80,
        doc_type="manual",
    )

    tags = covers(chunk, requirements)

    assert "corrective_measures_present" in tags


def test_load_requirements_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_requirements(Path("config/does_not_exist.yaml"))


def test_fan_maintenance_safety_chunk_is_tagged_correctly() -> None:
    requirements = load_requirements(REQUIREMENTS_PATH)
    chunk = Chunk(
        text=(
            "Power off the inverter and disconnect it from all power sources before "
            "maintaining its fans. Wait 5 minutes after the inverter is powered off, "
            "then test the voltage and current using specialized measurement "
            "instruments. Maintenance and operation must only be performed by "
            "qualified personnel who wear protective equipment."
        ),
        page_start=108,
        page_end=108,
        tokens=50,
        doc_type="manual",
    )

    assert "safety_fan_maintenance_isolation" in covers(chunk, requirements)


def test_arc_fault_chunk_is_tagged_with_cause_and_safety_requirements() -> None:
    requirements = load_requirements(REQUIREMENTS_PATH)
    chunk = Chunk(
        text=(
            "88 Electric Arc Fault 1. Disconnect the DC power supply, and check "
            "whether any DC cable is damaged, the connection terminal or fuse is "
            "loose or there is a weak contact."
        ),
        page_start=100,
        page_end=100,
        tokens=40,
        doc_type="manual",
    )

    tags = covers(chunk, requirements)
    assert "cause_electric_arc_fault" in tags
    assert "safety_disconnect_dc_before_arc_repair" in tags


def test_all_fault_category_requirement_ids_exist_in_requirements() -> None:
    data = yaml.safe_load(REQUIREMENTS_PATH.read_text(encoding="utf-8"))
    requirement_ids = set(data["requirements"].keys())
    for category, spec in data["fault_categories"].items():
        for req_id in spec["must"] + spec.get("optional", []):
            assert req_id in requirement_ids, f"{category} references unknown requirement {req_id}"
