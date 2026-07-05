from __future__ import annotations

from dataclasses import dataclass

from llm_router import Model, Provider, ToolCall, ToolStep, UsageStats
from llm_router._internal.providers.base import ProviderResult
from llm_router._internal.runtime.output import build_public_response


@dataclass(frozen=True, slots=True)
class RawSdkLikeObject:
    value: int


def _result(**overrides: object) -> ProviderResult:
    values = {
        "data": {"id": "resp-1"},
        "provider": Provider.OPENROUTER,
        "model": Model.DEEPSEEK_V3,
        "provider_model": "deepseek/deepseek-chat-v3-0324:free",
        "output_text": "hello",
        "usage": UsageStats(input_tokens=1, output_tokens=2, total_tokens=3),
    }
    values.update(overrides)
    return ProviderResult(**values)


def test_public_response_uses_public_provider_model_usage_and_traces() -> None:
    tool_call = ToolCall(id="call-1", name="add", args={"a": 1, "b": 2})
    tool_step = ToolStep(
        tool_name="add",
        args={"a": 1, "b": 2},
        result={"result": 3},
        call_id="call-1",
    )

    response = build_public_response(
        _result(tool_calls=(tool_call,)),
        tool_trace=(tool_step,),
    )

    assert response.provider == "openrouter"
    assert response.model == "deepseek-chat-v3"
    assert response.usage == UsageStats(input_tokens=1, output_tokens=2, total_tokens=3)
    assert response.output_text == "hello"
    assert response.tool_calls == [tool_call]
    assert response.tool_trace == [tool_step]
    assert response.routing_trace == []


def test_public_response_adds_structured_data_without_mutating_provider_data() -> None:
    response = build_public_response(
        _result(data={"text": '{"answer": "ok"}'}),
        structured_data={"answer": "ok"},
    )

    assert response.data == {
        "text": '{"answer": "ok"}',
        "parsed": {"answer": "ok"},
    }


def test_public_response_sanitizes_nested_non_json_objects() -> None:
    response = build_public_response(
        _result(data={"sdk": RawSdkLikeObject(value=3), "items": [object()]})
    )

    assert response.data["sdk"] == {"value": 3}
    assert response.data["items"][0]["type"] == "object"
    assert "preview" in response.data["items"][0]


def test_public_response_data_keeps_mapping_and_attribute_access() -> None:
    response = build_public_response(
        _result(
            data={
                "choices": [
                    {
                        "message": {
                            "content": "ok",
                        }
                    }
                ]
            }
        )
    )

    assert response.data["choices"][0]["message"]["content"] == "ok"
    assert response.data.choices[0].message.content == "ok"


def test_public_response_tool_lists_are_not_shared() -> None:
    first = build_public_response(_result())
    second = build_public_response(_result())

    first.tool_calls.append(ToolCall(name="tool"))
    first.tool_trace.append(ToolStep(tool_name="tool"))

    assert second.tool_calls == []
    assert second.tool_trace == []
