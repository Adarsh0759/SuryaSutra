from pathlib import Path

import pytest

from suryasutra.usage.cost import compute_cost_inr, load_pricing

PRICING_PATH = Path(__file__).parents[2] / "config" / "pricing.yaml"


def test_load_pricing_reads_real_config_file() -> None:
    pricing = load_pricing(PRICING_PATH)

    assert pricing.usd_to_inr > 0
    rates = pricing.models[("groq", "openai/gpt-oss-120b")]
    assert rates.input_usd_per_million == 0.15
    assert rates.output_usd_per_million == 0.60
    assert rates.context_window == 131072


def test_compute_cost_inr_scales_with_tokens() -> None:
    pricing = load_pricing(PRICING_PATH)

    cost_1m_in = compute_cost_inr(pricing, "groq", "openai/gpt-oss-120b", 1_000_000, 0)
    cost_1m_out = compute_cost_inr(pricing, "groq", "openai/gpt-oss-120b", 0, 1_000_000)

    assert cost_1m_in == pytest.approx(0.15 * pricing.usd_to_inr)
    assert cost_1m_out == pytest.approx(0.60 * pricing.usd_to_inr)
    assert cost_1m_out > cost_1m_in  # output is pricier than input for this model


def test_compute_cost_inr_zero_tokens_is_zero_cost() -> None:
    pricing = load_pricing(PRICING_PATH)

    assert compute_cost_inr(pricing, "groq", "openai/gpt-oss-120b", 0, 0) == 0.0


def test_compute_cost_inr_unknown_model_raises() -> None:
    pricing = load_pricing(PRICING_PATH)

    with pytest.raises(KeyError):
        compute_cost_inr(pricing, "groq", "no-such-model", 100, 100)
