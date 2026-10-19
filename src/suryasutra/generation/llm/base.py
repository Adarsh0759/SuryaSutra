"""Provider-agnostic LLM adapter interface (D-21).

No provider SDK import may appear outside `generation/llm/` (CLAUDE.md §5) — every
caller depends on this interface, never on a specific provider's client.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int  # provider-reported usage field — ground truth (D-22)
    output_tokens: int
    model: str
    provider: str
    latency_ms: float


class LLMAdapter(ABC):
    @abstractmethod
    def generate(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Call the LLM and return its raw text plus provider-reported usage."""
