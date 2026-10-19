"""Groq provider adapter (D-21). The only module allowed to import the `groq` SDK."""

import time

from groq import Groq

from suryasutra.generation.llm.base import LLMAdapter, LLMResponse


class GroqAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = Groq(api_key=api_key)
        self._model = model

    def generate(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        start = time.monotonic()
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        latency_ms = (time.monotonic() - start) * 1000

        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            model=self._model,
            provider="groq",
            latency_ms=latency_ms,
        )
