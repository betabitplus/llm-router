# mutation-pin: TREQ_USAGE_NORMALIZATION 1356bcae910da7c0
# pinned-by: claude-opus-5-5: The mutant replaces a nonzero total_tokens reported by the provider with input+output whenever input or output tokens are present. Totals that include other token counts, such as Gemini thought tokens, are silently lost (3 becomes 2). The original fills in the total only when the provider gives none
from __future__ import annotations

import pytest
from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]")
def test_normalize_usage_preserves_explicit_total_and_computes_missing_total() -> None:
    explicit_total_payload = {
        "input_tokens": 12,
        "output_tokens": 8,
        "total_tokens": 25,
    }
    assert normalize_usage(explicit_total_payload) == UsageStats(
        input_tokens=12,
        output_tokens=8,
        total_tokens=25,
    )

    missing_total_payload = {
        "input_tokens": 12,
        "output_tokens": 8,
    }
    assert normalize_usage(missing_total_payload) == UsageStats(
        input_tokens=12,
        output_tokens=8,
        total_tokens=20,
    )
