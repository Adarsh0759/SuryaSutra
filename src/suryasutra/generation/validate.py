"""Citation validator (D-23, CLAUDE.md §10).

Every safety item and step must cite a chunk that was actually selected for this
answer. An uncited claim is unverifiable — a technician has no way to check it against
the source — so it is treated as a validation failure, not a cosmetic nitpick.
"""

from suryasutra.generation.schema import LLMAnswerPayload


class CitationError(Exception):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"Items without a valid citation: {missing}")


def validate_citations(payload: LLMAnswerPayload, valid_citation_ids: set[str]) -> None:
    missing: list[str] = []

    for item in payload.safety:
        if not item.citations or not set(item.citations) <= valid_citation_ids:
            missing.append(f"safety: {item.text[:60]!r}")

    for step in payload.steps:
        if not step.citations or not set(step.citations) <= valid_citation_ids:
            missing.append(f"step {step.n}: {step.action[:60]!r}")

    if missing:
        raise CitationError(missing)
