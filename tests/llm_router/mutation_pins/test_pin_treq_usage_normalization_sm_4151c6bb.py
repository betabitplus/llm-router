# mutation-pin: TREQ_USAGE_NORMALIZATION SM-4151C6BB
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]")
def test_negative_provider_token_count_normalizes_to_zero() -> None:
    payload = {"prompt_tokens": -1}
    result = normalize_usage(payload)
    assert result == UsageStats(input_tokens=0, output_tokens=0, total_tokens=0)
