from __future__ import annotations

import json

import pytest

from llm_router import Model, Provider, ProviderError
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.tools import (
    ToolRegistry,
    normalize_tool_choice,
)
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.openai_compatible import OpenAICompatibleAdapter
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.tool_failure import openai_tool_call_response


def lookup(query: str) -> dict[str, str]:
    return {"answer": query.upper()}


def _request(**overrides: object) -> ProviderRequest:
    values = {
        "request_id": "req-1",
        "provider": Provider.OPENROUTER,
        "model": Model.DEEPSEEK_V3,
        "provider_model": "deepseek/test",
        "credential": ProviderCredential(
            key_id=1,
            env_var="OPENROUTER_API_KEY_1",
            value="secret",
        ),
        "messages": [normalize_content("hello")],
        "kwargs": {"logprobs": True},
    }
    values.update(overrides)
    return ProviderRequest(**values)


def _adapter(server: ScriptedHTTPServer) -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(base_url=f"{server.base_url}/v1")


def test_sync_success_posts_chat_completion_payload() -> None:
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="ok"),
                )
            ]
        },
    ) as server:
        result = _adapter(server).execute(_request())

        assert result.output_text == "ok"
        assert result.usage is not None
        assert server.request_count("POST", path) == 1
        recorded = server.recorded_requests("POST", path)[0]
        body = json.loads(recorded.body)
        assert body["model"] == "deepseek/test"
        assert body["messages"] == [{"role": "user", "content": "hello"}]
        assert body["logprobs"] is True
        assert recorded.headers["Authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_async_success() -> None:
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="async ok"),
                )
            ]
        },
    ) as server:
        result = await _adapter(server).aexecute(_request())

        assert result.output_text == "async ok"
        assert server.request_count("POST", path) == 1


def test_retryable_status_is_classified_without_retry_loop() -> None:
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=429,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(
                        status_code=429,
                        message="try again later",
                    ),
                )
            ]
        },
    ) as server:
        with pytest.raises(ProviderError) as exc_info:
            _adapter(server).execute(_request())

        assert exc_info.value.cause.retryable is True
        assert exc_info.value.cause.status_code == 429
        assert "try again later" in str(exc_info.value)
        assert server.request_count("POST", path) == 1


def test_non_retryable_status_is_classified_without_retry_loop() -> None:
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(
                        status_code=400,
                        message="bad request",
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="unexpected"),
                ),
            ]
        },
    ) as server:
        with pytest.raises(ProviderError) as exc_info:
            _adapter(server).execute(_request())

        assert exc_info.value.cause.retryable is False
        assert exc_info.value.cause.status_code == 400
        assert "bad request" in str(exc_info.value)
        assert server.request_count("POST", path) == 1


def test_malformed_success_json_is_wrapped_as_provider_error() -> None:
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=b"{not-json",
                )
            ]
        },
    ) as server:
        with pytest.raises(ProviderError) as exc_info:
            _adapter(server).execute(_request())

        assert exc_info.value.cause.retryable is False
        assert exc_info.value.cause.retry_reason == "invalid_json_response"
        assert exc_info.value.cause.status_code == 200


def test_non_object_success_json_is_wrapped_as_provider_error() -> None:
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=b"[]",
                )
            ]
        },
    ) as server:
        with pytest.raises(ProviderError) as exc_info:
            _adapter(server).execute(_request())

        assert exc_info.value.cause.retryable is False
        assert exc_info.value.cause.retry_reason == "non_object_json_response"
        assert exc_info.value.cause.status_code == 200


def test_malformed_error_json_keeps_status_retry_classification() -> None:
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=503,
                    headers={"Content-Type": "application/json"},
                    body=b"not-json",
                )
            ]
        },
    ) as server:
        with pytest.raises(ProviderError) as exc_info:
            _adapter(server).execute(_request())

        assert exc_info.value.cause.retryable is True
        assert exc_info.value.cause.retry_reason == "retryable_status"
        assert exc_info.value.cause.status_code == 503
        assert "HTTP 503" in str(exc_info.value)


def test_remote_disconnect_is_retryable_transport_failure() -> None:
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    disconnect=True,
                )
            ]
        },
    ) as server:
        with pytest.raises(ProviderError) as exc_info:
            _adapter(server).execute(_request())

        assert exc_info.value.cause.retryable is True
        assert exc_info.value.cause.retry_reason == "transport_exception"
        assert server.request_count("POST", path) == 1


def test_tool_call_response_is_parsed() -> None:
    path = openai_chat_path()
    body = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "lookup",
                                    "arguments": '{"query": "abc"}',
                                },
                            }
                        ]
                    }
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
    ).encode("utf-8")
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=body,
                )
            ]
        },
    ) as server:
        result = _adapter(server).execute(_request())

        assert result.output_text == ""
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "lookup"
        assert result.tool_calls[0].args == {"query": "abc"}


def test_tool_loop_round_trip_can_send_tool_result_message() -> None:
    path = openai_chat_path()
    registry = ToolRegistry.from_tools([lookup])
    choice = normalize_tool_choice("lookup", registry=registry)
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_tool_call_response(
                        tool_name="lookup",
                        args={"query": "abc"},
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text='{"answer": "ABC"}'),
                ),
            ]
        },
    ) as server:
        adapter = _adapter(server)
        first = adapter.execute(_request(tool_registry=registry, tool_choice=choice))
        step = registry.execute(first.tool_calls[0])
        tool_result_messages = [
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": first.tool_calls[0].id,
                        "type": "function",
                        "function": {
                            "name": first.tool_calls[0].name,
                            "arguments": first.tool_calls[0].raw_arguments,
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": first.tool_calls[0].id,
                "content": json.dumps(step.result),
            },
        ]
        second = adapter.execute(_request(kwargs={"messages": tool_result_messages}))

        assert second.output_text == '{"answer": "ABC"}'
        assert server.request_count("POST", path) == 2
        recorded = server.recorded_requests("POST", path)
        first_body = json.loads(recorded[0].body)
        second_body = json.loads(recorded[1].body)
        assert first_body["tool_choice"] == {
            "type": "function",
            "function": {"name": "lookup"},
        }
        assert second_body["messages"][2] == {
            "role": "tool",
            "tool_call_id": "call_local_tool",
            "content": '{"answer": "ABC"}',
        }
