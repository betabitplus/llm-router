from __future__ import annotations

from types import SimpleNamespace

from google.genai import types
from pydantic import BaseModel

from llm_router import Model, Provider, UsageStats
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.google_genai import parse_google_genai_response


class Reply(BaseModel):
    answer: str


def _request() -> ProviderRequest:
    return ProviderRequest(
        request_id="req-1",
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH,
        provider_model="gemini-2.5-flash",
        credential=ProviderCredential(
            key_id=1,
            env_var="GOOGLE_API_KEY_1",
            value="secret",
        ),
        messages=[normalize_content("hello")],
    )


def _usage() -> SimpleNamespace:
    return SimpleNamespace(
        prompt_token_count=2,
        candidates_token_count=3,
        total_token_count=5,
    )


def test_parse_text_and_usage_from_sdk_response() -> None:
    response = SimpleNamespace(text="hello back", usage_metadata=_usage())

    result = parse_google_genai_response(request=_request(), response=response)

    assert result.output_text == "hello back"
    assert result.usage == UsageStats(input_tokens=2, output_tokens=3, total_tokens=5)
    assert result.data["text"] == "hello back"


def test_parse_structured_output_without_sdk_object_leak() -> None:
    response = SimpleNamespace(
        text="",
        parsed=Reply(answer="ok"),
        usage_metadata=None,
    )

    result = parse_google_genai_response(request=_request(), response=response)

    assert result.output_text == '{"answer": "ok"}'
    assert result.data["parsed"] == {"answer": "ok"}


def test_parse_text_from_candidate_parts() -> None:
    response = SimpleNamespace(
        text="",
        usage_metadata=None,
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[types.Part(text="candidate text")])
            )
        ],
    )

    result = parse_google_genai_response(request=_request(), response=response)

    assert result.output_text == "candidate text"


def test_parse_tool_calls_from_function_call_parts() -> None:
    response = SimpleNamespace(
        text="",
        usage_metadata=None,
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                id="call-1",
                                name="lookup",
                                args={"query": "abc"},
                            )
                        )
                    ]
                )
            )
        ],
    )

    result = parse_google_genai_response(request=_request(), response=response)

    assert result.output_text == ""
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call-1"
    assert result.tool_calls[0].name == "lookup"
    assert result.tool_calls[0].args == {"query": "abc"}
