"""Prints a starting hint for filling in data/eval/gold_labels.yaml — NOT gold data.

Deliberately writes to a separate file (data/eval/system_suggestions.yaml) so there is
no way to confuse "what the automated system currently believes" with "what a human
independently verified against the real manual" (D-14). The whole point of the gold
label file is to be an independent check on the automated tagging system — if this
script's output silently became the gold data, the eval would just be checking the
system against itself.

Usage: python -m eval.suggest_gold_labels
"""

import json
from pathlib import Path

import yaml

from suryasutra.ingest.build_index import build_corpus
from suryasutra.ingest.tag import load_fault_categories, load_requirements
from suryasutra.retrieval.bm25 import BM25Index
from suryasutra.retrieval.dense import DenseIndex
from suryasutra.retrieval.hybrid import HybridRetriever

REPO_ROOT = Path(__file__).resolve().parents[1]
MANUAL_PATH = REPO_ROOT / "data" / "raw" / "sungrow_sg150cx_user_manual.pdf"
REQUIREMENTS_PATH = REPO_ROOT / "config" / "requirements.yaml"
ALARMS_PATH = REPO_ROOT / "data" / "synthetic" / "alarms.json"
OUTPUT_PATH = REPO_ROOT / "data" / "eval" / "system_suggestions.yaml"


def main() -> None:
    requirements = load_requirements(REQUIREMENTS_PATH)
    fault_categories = load_fault_categories(REQUIREMENTS_PATH)
    chunks = build_corpus(MANUAL_PATH, doc_type="manual", requirements=requirements)
    retriever = HybridRetriever(BM25Index(chunks), DenseIndex(chunks))
    alarms = json.loads(ALARMS_PATH.read_text(encoding="utf-8"))["alarms"]

    suggestions = []
    for alarm in alarms:
        if not alarm["answerable"]:
            continue
        category = fault_categories[alarm["category"]]
        results = retriever.query(alarm["message"], top_k=10)
        pages_with_mandatory_tag = sorted(
            {r.chunk.page_start for r in results if r.chunk.covers & category.must}
        )
        suggestions.append(
            {
                "alarm_id": alarm["id"],
                "code": alarm["code"],
                "suggested_pages": pages_with_mandatory_tag,
                "basis": (
                    "pages among the top-10 retrieved whose text matched a mandatory "
                    "requirement's keyword tag — a heuristic, not a verified fact"
                ),
            }
        )

    header = (
        "# NOT GOLD DATA. System-generated starting hints only (D-14) — verify every\n"
        "# page against the real manual yourself before using it in\n"
        "# data/eval/gold_labels.yaml. Regenerate anytime with:\n"
        "#   python -m eval.suggest_gold_labels\n\n"
    )
    OUTPUT_PATH.write_text(
        header + yaml.safe_dump(suggestions, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    print(f"Wrote {len(suggestions)} suggestion(s) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
