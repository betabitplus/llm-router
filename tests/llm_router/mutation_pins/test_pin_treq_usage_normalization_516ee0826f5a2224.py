# mutation-pin: TREQ_USAGE_NORMALIZATION 516ee0826f5a2224
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]")
def test_usage_stats_instance_returned_as_is_with_fields_unchanged() -> None:
    usage = UsageStats(input_tokens=5, output_tokens=3, total_tokens=0)
    result = normalize_usage(usage)
    assert result is usage
    assert result.input_tokens == 5
    assert result.output_tokens == 3
    assert result.total_tokens == 0
