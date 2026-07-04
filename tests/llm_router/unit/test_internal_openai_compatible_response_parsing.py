from __future__ import annotations

import pytest

from llm_router import Model, Provider, ProviderError, UsageStats
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.openai_compatible import (
    parse_openai_compatible_response,
)


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="req-1",
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model="deepseek/test",
        credential=ProviderCredential(
            key_id=1,
            env_var="OPENROUTER_API_KEY_1",
            value="secret",
        ),
        messages=[normalize_content("hello")],
    )


def test_parse_text_usage_and_data_without_sdk_objects() -> None:
    result = parse_openai_compatible_response(
        request=_request(),
        data={
            "id": "chatcmpl-local",
            "model": "local-model",
            "choices": [{"message": {"role": "assistant", "content": "hello back"}}],
            "usage": {
                "prompt_tokens": 2,
                "completion_tokens": 3,
                "total_tokens": 5,
            },
        },
    )

    assert result.output_text == "hello back"
    assert result.usage == UsageStats(input_tokens=2, output_tokens=3, total_tokens=5)
    assert result.data["id"] == "chatcmpl-local"


def test_parse_tool_calls() -> None:
    result = parse_openai_compatible_response(
        request=_request(),
        data={
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "lookup",
                                    "arguments": '{"query": "x"}',
                                },
                            }
                        ],
                    }
                }
            ]
        },
    )

    assert result.output_text == ""
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "lookup"
    assert result.tool_calls[0].args == {"query": "x"}


@pytest.mark.parametrize(
    ("status_code", "retryable", "retry_reason"),
    [
        (429, True, "retryable_status"),
        (503, True, "retryable_status"),
        (400, False, "caller_or_auth_status"),
        (401, False, "caller_or_auth_status"),
    ],
)
def test_error_response_classification(
    status_code: int,
    retryable: bool,
    retry_reason: str,
) -> None:
    with pytest.raises(ProviderError) as exc_info:
        parse_openai_compatible_response(
            request=_request(),
            status_code=status_code,
            data={"error": {"message": "provider said no"}},
        )

    assert "provider said no" in str(exc_info.value)
    assert exc_info.value.cause.retryable is retryable
    assert exc_info.value.cause.status_code == status_code
    assert exc_info.value.cause.retry_reason == retry_reason
