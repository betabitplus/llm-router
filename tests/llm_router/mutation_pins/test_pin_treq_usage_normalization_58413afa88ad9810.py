# mutation-pin: TREQ_USAGE_NORMALIZATION 58413afa88ad9810
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]")
def test_usage_stats_instance_normalizes_unchanged() -> None:
    usage = UsageStats(input_tokens=12, output_tokens=18, total_tokens=30)
    assert normalize_usage(usage) == usage
