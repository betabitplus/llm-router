from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from llm_router import Model, Provider, ProviderError, UsageStats
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.schema import normalize_schema
from llm_router._internal.capabilities.tools import ToolRegistry
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import parse_qwenchat_response


class Reply(BaseModel):
    answer: str


def add(a: int, b: int) -> dict[str, int]:
    return {"result": a + b}


def _request(**overrides: object) -> ProviderRequest:
    values = {
        "request_id": "req-1",
        "provider": Provider.QWENCHAT,
        "model": Model.QWEN_MAX_LATEST,
        "provider_model": "qwen-max-latest",
        "credential": ProviderCredential(
            key_id=1,
            env_var="QWENCHAT_API_KEY_1",
            value="secret",
        ),
        "messages": [normalize_content("hello")],
    }
    values.update(overrides)
    return ProviderRequest(**values)


def _success_body(*, text: str) -> str:
    return json.dumps(
        {
            "choices": [{"message": {"content": text}}],
            "usage": {
                "prompt_tokens": 2,
                "completion_tokens": 3,
                "total_tokens": 5,
            },
        }
    )


def _error_body(*, message: str) -> str:
    return json.dumps({"error": {"message": message}})


def test_parse_text_and_usage() -> None:
    result = parse_qwenchat_response(
        request=_request(),
        status_code=200,
        text=_success_body(text=" ok "),
    )

    assert result.output_text == "ok"
    assert result.usage == UsageStats(input_tokens=2, output_tokens=3, total_tokens=5)


def test_parse_structured_output_from_prompted_text() -> None:
    request = _request(schema=normalize_schema(Reply))

    result = parse_qwenchat_response(
        request=request,
        status_code=200,
        text=_success_body(text='```json\n{"answer": "ok"}\n```'),
    )

    assert result.output_text == '{"answer": "ok"}'
    assert result.data["parsed"] == {"answer": "ok"}


def test_parse_textual_tool_call() -> None:
    request = _request(tool_registry=ToolRegistry.from_tools([add]))

    result = parse_qwenchat_response(
        request=request,
        status_code=200,
        text=_success_body(text="add(a=20, b=22)"),
    )

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "add"
    assert result.tool_calls[0].args == {"a": 20, "b": 22}
    assert result.tool_calls[0].raw_arguments == "a=20, b=22"


@pytest.mark.parametrize(
    ("status_code", "retryable", "retry_reason"),
    [
        (429, True, "retryable_status"),
        (503, True, "retryable_status"),
        (400, False, "caller_or_auth_status"),
        (401, False, "caller_or_auth_status"),
    ],
)
def test_status_failures_are_classified(
    status_code: int,
    retryable: bool,
    retry_reason: str,
) -> None:
    with pytest.raises(ProviderError) as exc_info:
        parse_qwenchat_response(
            request=_request(),
            status_code=status_code,
            text=_error_body(message="provider said no"),
        )

    assert exc_info.value.cause.status_code == status_code
    assert exc_info.value.cause.retryable is retryable
    assert exc_info.value.cause.retry_reason == retry_reason
    assert "provider said no" in str(exc_info.value)


def test_malformed_success_json_is_wrapped() -> None:
    with pytest.raises(ProviderError) as exc_info:
        parse_qwenchat_response(
            request=_request(),
            status_code=200,
            text="{not-json",
        )

    assert exc_info.value.cause.retryable is False
    assert exc_info.value.cause.retry_reason == "invalid_json_response"
