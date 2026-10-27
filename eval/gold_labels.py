"""Schema and loader for hand-labelled eval ground truth (D-14, CLAUDE.md §12).

This is deliberately separate from config/requirements.yaml's automated tag-based
coverage system: that system *infers* which chunks cover a requirement via keyword
rules the system's own author wrote, which could simply be wrong. This file is meant
to be independently authored by the founder — gold data the automated system gets
checked against, not data it checks itself against. Nothing in this module invents or
pre-fills gold field values; see eval/suggest_gold_labels.py for the clearly-separate,
non-authoritative suggestion helper.
"""

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
ALARMS_PATH = REPO_ROOT / "data" / "synthetic" / "alarms.json"
GOLD_LABELS_PATH = REPO_ROOT / "data" / "eval" / "gold_labels.yaml"


class GoldLabel(BaseModel):
    alarm_id: int
    answerable: bool
    # Empty for a deliberately-unanswerable alarm — there is no correct cause/pages/
    # checklist to name when the right answer is "the evidence doesn't exist."
    gold_causes: list[str] = Field(default_factory=list)
    gold_mandatory_pages: list[int] = Field(default_factory=list)
    gold_step_checklist: list[str] = Field(default_factory=list)
    notes: str = ""


class GoldLabelSet(BaseModel):
    review_status: str  # "unreviewed" until a qualified electrical/PV person signs off (D-14)
    # Who/what actually wrote the field values below — e.g. "claude-sonnet-5 (ai-assisted
    # draft; not independently human-verified)" or "adarsh (independently verified against
    # the manual)". None only for an untouched template with every field empty. Machine-
    # checkable provenance, not just a prose claim in a comment — see D-14.
    drafted_by: str | None = None
    labels: dict[int, GoldLabel]  # keyed by alarm_id


def load_gold_labels(path: Path) -> GoldLabelSet:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    labels = {entry["alarm_id"]: GoldLabel.model_validate(entry) for entry in data["alarms"]}
    return GoldLabelSet(
        review_status=data["review_status"], drafted_by=data.get("drafted_by"), labels=labels
    )


def write_template(path: Path, alarms: list[dict[str, Any]]) -> None:
    """Writes a template with every alarm present and every gold field empty — never
    called with anything but blank values; filling them in is the founder's job."""
    header = (
        "# Hand-labelled eval ground truth (D-14, CLAUDE.md §12).\n"
        "#\n"
        "# This file must be filled in by a human independently verifying the real\n"
        "# manual (data/raw/sungrow_sg150cx_user_manual.pdf) against each alarm below\n"
        "# — not copied from config/requirements.yaml's automated tags, which is\n"
        "# exactly the system this file is meant to check. See\n"
        "# eval/suggest_gold_labels.py for a non-authoritative starting hint (clearly\n"
        "# separate from this file) if you want a faster starting point to verify\n"
        "# against, not trust outright.\n"
        "#\n"
        "# Per alarm (skip gold_causes/gold_mandatory_pages/gold_step_checklist for\n"
        "# the deliberately-unanswerable ones — there is no correct answer to name):\n"
        "#   gold_causes:            the correct diagnosis/diagnoses, in your own words\n"
        "#   gold_mandatory_pages:   manual page numbers that MUST be retrieved/cited\n"
        "#                           for a safe, complete answer\n"
        "#   gold_step_checklist:    required actions/precautions a correct answer\n"
        "#                           must include (used to score step correctness —\n"
        "#                           exact wording doesn't need to match, the content\n"
        "#                           does)\n"
        "#\n"
        "# review_status must stay 'unreviewed' until a qualified electrical/PV\n"
        "# person has checked this file (D-14) — do not change it yourself.\n\n"
    )

    doc = {
        "review_status": "unreviewed",
        "drafted_by": None,
        "alarms": [
            {
                "alarm_id": alarm["id"],
                "answerable": alarm["answerable"],
                "gold_causes": [],
                "gold_mandatory_pages": [],
                "gold_step_checklist": [],
                "notes": "",
            }
            for alarm in alarms
        ],
    }
    path.write_text(
        header + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


if __name__ == "__main__":
    if GOLD_LABELS_PATH.exists():
        raise SystemExit(
            f"{GOLD_LABELS_PATH} already exists — not overwriting filled-in labels. "
            "Delete it first if you really want a fresh template."
        )
    alarms = json.loads(ALARMS_PATH.read_text(encoding="utf-8"))["alarms"]
    write_template(GOLD_LABELS_PATH, alarms)
    print(f"Wrote template for {len(alarms)} alarms to {GOLD_LABELS_PATH}")
