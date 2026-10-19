"""Builds the triage prompt from an alarm and its selected evidence chunks (CLAUDE.md §10).

Citation ids are per-request (c1, c2, ...) assigned in the selector's own output
order — chunks have no stable database id yet (no DB layer built). `validate.py`
checks the model's citations against exactly this id set.
"""

from dataclasses import dataclass

from suryasutra.ingest.chunk import Chunk

_SYSTEM_PROMPT = """You are SuryaSutra, an O&M copilot for Indian solar plants. \
You are given an alarm and a set of evidence passages, each with a citation id. \
Produce a JSON object with exactly this shape:

{
  "safety": [{"text": "...", "citations": ["c1"]}],
  "likely_causes": [{"cause": "...", "confidence": "high|medium|low", "citations": ["c1"]}],
  "steps": [{"n": 1, "action": "...", "expected_result": "...", "citations": ["c1"]}],
  "escalate_if": ["..."],
  "uncertainties": ["..."]
}

Rules:
- Every safety item and every step MUST cite at least one evidence id from the list given. Never invent a citation id that was not given to you.
- Never state a safety instruction, cause, or step that is not supported by one of the evidence passages.
- If the evidence does not support a safety precaution, cause, or step, omit it rather than guessing.
- Output ONLY the JSON object, no other text."""


@dataclass(frozen=True)
class AlarmInfo:
    code: str
    message: str


def build_prompt(
    alarm: AlarmInfo, selected_chunks: tuple[Chunk, ...]
) -> tuple[str, str, dict[str, Chunk]]:
    citation_map = {f"c{i + 1}": chunk for i, chunk in enumerate(selected_chunks)}

    evidence_block = "\n\n".join(
        f"[{cid}] (page {chunk.page_start}-{chunk.page_end})\n{chunk.text}"
        for cid, chunk in citation_map.items()
    )
    user_prompt = (
        f"Alarm code: {alarm.code}\nAlarm message: {alarm.message}\n\nEvidence:\n{evidence_block}"
    )
    return _SYSTEM_PROMPT, user_prompt, citation_map
