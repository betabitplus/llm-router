# mutation-pin: TREQ_USAGE_NORMALIZATION FN-09E5F504
# pinned-by: delegate, one pin for 2 pins of normalize_usage
# kills: 3b9da8b0c2e02991 516ee0826f5a2224
from __future__ import annotations

import pytest

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]")
def test_none_is_none_and_usage_stats_returned_unchanged() -> None:
    assert normalize_usage(None) is None

    usage = UsageStats(input_tokens=5, output_tokens=3, total_tokens=0)
    result = normalize_usage(usage)
    assert result is usage
    assert result.input_tokens == 5
    assert result.output_tokens == 3
    assert result.total_tokens == 0
