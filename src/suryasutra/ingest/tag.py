"""Tag chunks with the requirement ids they satisfy, from config/requirements.yaml (D-07).

This is a hand-authored heuristic (doc_type + keyword match), not a learned classifier
— see D-07's alternatives. Every requirement loaded here carries a `review_status`;
`unreviewed` requirements must not be used to support a published safety claim (D-14,
CLAUDE.md §6) until a qualified electrical/PV person signs off.

Scope: this module only tags chunks with what they cover. Resolving an alarm's fault
code to its required requirement set (fault_categories in the same YAML file) is a
separate, later step owned by the triage pipeline, not ingestion.
"""

from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from suryasutra.ingest.chunk import Chunk


@dataclass(frozen=True)
class Requirement:
    id: str
    description: str
    review_status: str
    doc_types: frozenset[str]
    keywords_any: tuple[str, ...]


def load_requirements(path: Path) -> dict[str, Requirement]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    requirements: dict[str, Requirement] = {}
    for req_id, spec in (data.get("requirements") or {}).items():
        tag_rules = spec.get("tag_rules", {})
        requirements[req_id] = Requirement(
            id=req_id,
            description=spec["description"].strip(),
            review_status=spec.get("review_status", "unreviewed"),
            doc_types=frozenset(tag_rules.get("doc_types", [])),
            keywords_any=tuple(tag_rules.get("keywords_any", [])),
        )
    return requirements


def covers(chunk: Chunk, requirements: dict[str, Requirement]) -> frozenset[str]:
    """Return the ids of every requirement whose tag rules this chunk's text satisfies."""
    text_lower = chunk.text.lower()
    covered: set[str] = set()
    for req in requirements.values():
        if not req.doc_types and not req.keywords_any:
            continue  # no rule defined; never matches by default
        if req.doc_types and chunk.doc_type not in req.doc_types:
            continue
        if req.keywords_any and not any(kw.lower() in text_lower for kw in req.keywords_any):
            continue
        covered.add(req.id)
    return frozenset(covered)


def tag_chunks(chunks: list[Chunk], requirements: dict[str, Requirement]) -> list[Chunk]:
    """Return copies of `chunks` with `.covers` populated (D-07's chunk shape, CLAUDE.md §6)."""
    return [replace(chunk, covers=covers(chunk, requirements)) for chunk in chunks]


@dataclass(frozen=True)
class FaultCategory:
    id: str
    match_codes: tuple[str, ...]
    must: frozenset[str]
    optional: frozenset[str]


def load_fault_categories(path: Path) -> dict[str, FaultCategory]:
    """Load the fault_categories section of the same requirements.yaml (D-07).

    Resolving an *alarm's* fault code to one of these categories (via match_codes) is
    a triage-pipeline concern, not ingestion — this function only loads the schema.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    categories: dict[str, FaultCategory] = {}
    for cat_id, spec in (data.get("fault_categories") or {}).items():
        categories[cat_id] = FaultCategory(
            id=cat_id,
            match_codes=tuple(spec.get("match_codes", [])),
            must=frozenset(spec.get("must", [])),
            optional=frozenset(spec.get("optional", [])),
        )
    return categories
