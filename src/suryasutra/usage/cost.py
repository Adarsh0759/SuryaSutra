"""Turn provider-reported token counts into ₹ cost, from config/pricing.yaml (D-22).

Token counts themselves are ground truth once they come from the provider's own
usage field — this module only does the ₹ arithmetic, and never estimates tokens.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ModelPricing:
    input_usd_per_million: float
    output_usd_per_million: float
    context_window: int


@dataclass(frozen=True)
class PricingTable:
    usd_to_inr: float
    models: dict[tuple[str, str], ModelPricing]  # (provider, model) -> pricing


def load_pricing(path: Path) -> PricingTable:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    models: dict[tuple[str, str], ModelPricing] = {}
    for provider, provider_models in data["providers"].items():
        for model, spec in provider_models.items():
            models[(provider, model)] = ModelPricing(
                input_usd_per_million=spec["input_usd_per_million"],
                output_usd_per_million=spec["output_usd_per_million"],
                context_window=spec["context_window"],
            )
    return PricingTable(usd_to_inr=data["usd_to_inr"], models=models)


def compute_cost_inr(
    pricing: PricingTable,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    key = (provider, model)
    if key not in pricing.models:
        raise KeyError(f"No pricing entry for provider={provider!r} model={model!r}")
    rates = pricing.models[key]
    usd = (input_tokens / 1_000_000) * rates.input_usd_per_million + (
        output_tokens / 1_000_000
    ) * rates.output_usd_per_million
    return usd * pricing.usd_to_inr
