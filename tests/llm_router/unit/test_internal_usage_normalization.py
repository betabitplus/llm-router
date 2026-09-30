from __future__ import annotations

from types import SimpleNamespace

import pytest

from llm_router import UsageStats
from llm_router._internal.capabilities.usage import normalize_usage
from tests.llm_router.support.fault_observation import retain_local_fault_injection

pytestmark = [
    pytest.mark.verifies("TREQ_USAGE_NORMALIZATION[revision==1]"),
    pytest.mark.verification_kind("unit"),
]


@pytest.mark.coverage_path("openai-mapping")
def test_openai_usage_mapping_normalizes() -> None:
    assert normalize_usage(
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    ) == UsageStats(input_tokens=10, output_tokens=5, total_tokens=15)


@pytest.mark.coverage_path("google-object")
def test_google_usage_object_normalizes_and_computes_total() -> None:
    raw = SimpleNamespace(prompt_token_count=4, candidates_token_count=6)

    assert normalize_usage(raw) == UsageStats(
        input_tokens=4,
        output_tokens=6,
        total_tokens=10,
    )


@pytest.mark.coverage_path("nested-mapping")
def test_nested_usage_mapping_normalizes() -> None:
    assert normalize_usage({"usage": {"input_tokens": 7, "output_tokens": 8}}) == (
        UsageStats(input_tokens=7, output_tokens=8, total_tokens=15)
    )


for _test_name in (
    "test_openai_usage_mapping_normalizes",
    "test_google_usage_object_normalizes_and_computes_total",
    "test_nested_usage_mapping_normalizes",
):
    globals()[_test_name] = pytest.mark.coverage_item(
        "VC_PROVIDER_USAGE_NORMALIZATION"
    )(globals()[_test_name])
del _test_name


@pytest.mark.fault_item("TREQ_USAGE_NORMALIZATION", "interface.payload-schema")
def test_usage_counts_a_payload_garbles_or_leaves_out_normalize_consistently() -> None:
    retain_local_fault_injection(
        contract_id="TREQ_USAGE_NORMALIZATION",
        fault_class="interface.payload-schema",
        mechanism=(
            "a provider usage mapping with a count that is not a number, a null "
            "count and no total"
        ),
    )
    assert normalize_usage(
        {"prompt_tokens": 9, "completion_tokens": "many", "total_tokens": None}
    ) == UsageStats(input_tokens=9, output_tokens=0, total_tokens=9)
