# semantic-mutant: SM-4151C6BB
from __future__ import annotations

import pytest

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import _first_int, normalize_usage

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]")
def test_first_int_clamps_negative_provider_value_to_zero() -> None:
    """A negative provider-reported token count must never be surfaced as-is.

    Some providers can report a corrective/negative delta for a token field;
    per _first_int's contract ("non-negative integer-like value"), such a
    value must be clamped to 0 rather than propagated verbatim.
    """
    payload = {"input_tokens": -5}

    result = _first_int(payload, ("input_tokens",))

    assert result == 0


@pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]")
def test_normalize_usage_keeps_total_consistent_with_negative_field() -> None:
    """normalize_usage must produce a stable, consistent total_tokens.

    Even when a provider payload carries a negative token field, the
    normalized model's input_tokens must be clamped to 0 and total_tokens
    must equal input_tokens + output_tokens, never reflecting the raw
    negative provider value.
    """
    payload = {"usage": {"input_tokens": -3, "output_tokens": 12}}

    result = normalize_usage(payload)

    assert result == UsageStats(input_tokens=0, output_tokens=12, total_tokens=12)
