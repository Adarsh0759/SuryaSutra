"""Groq provider adapter (D-21). The only module allowed to import the `groq` SDK."""

import time

from groq import Groq, RateLimitError

from suryasutra.generation.llm.base import LLMAdapter, LLMResponse


def _retry_after_seconds(exc: RateLimitError, default: float = 10.0) -> float:
    """Groq's free tier has a real tokens-per-minute cap (D-33's own cost tradeoff for
    picking a cheap provider) — a batch eval run making several large-context calls
    hits it in practice, not just in theory. Honor the server's own Retry-After header
    when it gives one; fall back to a fixed guess otherwise."""
    response = getattr(exc, "response", None)
    header = response.headers.get("retry-after") if response is not None else None
    try:
        return float(header) + 1.0 if header is not None else default
    except ValueError:
        return default


class GroqAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str, max_rate_limit_retries: int = 5) -> None:
        self._client = Groq(api_key=api_key)
        self._model = model
        self._max_rate_limit_retries = max_rate_limit_retries

    def generate(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        start = time.monotonic()
        for attempt in range(self._max_rate_limit_retries + 1):
            try:
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
                break
            except RateLimitError as exc:
                if attempt == self._max_rate_limit_retries:
                    raise
                time.sleep(_retry_after_seconds(exc))
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
