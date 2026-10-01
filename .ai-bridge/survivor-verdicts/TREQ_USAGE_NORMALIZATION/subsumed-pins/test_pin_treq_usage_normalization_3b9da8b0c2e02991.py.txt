# mutation-pin: TREQ_USAGE_NORMALIZATION 3b9da8b0c2e02991
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]")
def test_none_usage_normalizes_to_none_not_zero_stats() -> None:
    result = normalize_usage(None)
    assert result is None
    assert not isinstance(result, UsageStats)
