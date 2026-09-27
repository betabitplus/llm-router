# mutation-pin: TREQ_USAGE_NORMALIZATION SM-67E8442B
# pinned-by: claude-opus-5-5: The mutant ignores any total the provider reports and always recomputes it as input + output. A total-only payload such as {'total_tokens': 42} becomes 0. A Gemini payload whose totalTokenCount includes thought tokens gets undercounted. This breaks the requirement that every supported usage shape no
# tests/llm_router/unit/test_internal_usage_normalization_total_only.py
from __future__ import annotations

import pytest

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]")
def test_total_only_usage_payload_preserves_reported_total() -> None:
    """Pins that a provider-reported total token count is kept (not zeroed)
    when input/output token fields are absent from the payload."""
    payload = {"totalTokenCount": 42}

    result = normalize_usage(payload)

    assert result == UsageStats(input_tokens=0, output_tokens=0, total_tokens=42)
