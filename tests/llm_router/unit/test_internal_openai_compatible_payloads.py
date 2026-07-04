from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from llm_router import FileSchema, Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.capabilities.schema import normalize_schema
from llm_router._internal.capabilities.tools import (
    ToolRegistry,
    normalize_tool_choice,
)
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.openai_compatible import OpenAICompatibleAdapter


def lookup(query: str) -> str:
    """Look up a value."""
    return query


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
    }
    values.update(overrides)
    return ProviderRequest(**values)


def test_text_message_payload_uses_plain_string_content() -> None:
    payload = OpenAICompatibleAdapter(base_url="http://example.test/v1").build_payload(
        _request(temperature=0.2, seed=42, kwargs={"logprobs": True})
    )

    assert payload["model"] == "deepseek/test"
    assert payload["messages"] == [{"role": "user", "content": "hello"}]
    assert payload["temperature"] == 0.2
    assert payload["seed"] == 42
    assert payload["logprobs"] is True


def test_mixed_image_payload_uses_content_parts() -> None:
    image = Image.new("RGB", (10, 10))
    payload = OpenAICompatibleAdapter(base_url="http://example.test/v1").build_payload(
        _request(messages=[normalize_content(["look", image])])
    )

    content = payload["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "look"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_schema_payload_uses_openai_json_schema_response_format() -> None:
    schema = normalize_schema(
        {
            "title": "Reply",
            "type": "object",
            "required": ["answer"],
            "properties": {"answer": {"type": "string"}},
        }
    )

    payload = OpenAICompatibleAdapter(base_url="http://example.test/v1").build_payload(
        _request(schema=schema)
    )

    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["name"] == "Reply"
    assert payload["response_format"]["json_schema"]["strict"] is True


def test_passthrough_kwargs_can_override_generated_fields() -> None:
    schema = normalize_schema(
        {
            "title": "Reply",
            "type": "object",
            "properties": {"answer": {"type": "string"}},
        }
    )

    payload = OpenAICompatibleAdapter(base_url="http://example.test/v1").build_payload(
        _request(
            schema=schema,
            kwargs={"response_format": {"type": "json_object"}},
        )
    )

    assert payload["response_format"] == {"type": "json_object"}


def test_file_media_fails_fast_when_not_supported(tmp_path: Path) -> None:
    path = tmp_path / "input.txt"
    path.write_text("hello", encoding="utf-8")
    request = _request(
        messages=[
            normalize_content([FileSchema(path=str(path), mime_type="text/plain")])
        ]
    )

    with pytest.raises(ValueError, match="file media"):
        OpenAICompatibleAdapter(base_url="http://example.test/v1").build_payload(
            request
        )


def test_tools_and_named_tool_choice_translate_to_openai_payload() -> None:
    registry = ToolRegistry.from_tools([lookup])
    choice = normalize_tool_choice("lookup", registry=registry)

    payload = OpenAICompatibleAdapter(base_url="http://example.test/v1").build_payload(
        _request(tool_registry=registry, tool_choice=choice)
    )

    assert payload["tools"][0]["function"]["name"] == "lookup"
    assert payload["tool_choice"] == {
        "type": "function",
        "function": {"name": "lookup"},
    }


def test_raw_tool_choice_is_preserved() -> None:
    choice = normalize_tool_choice({"type": "function", "function": {"name": "x"}})

    payload = OpenAICompatibleAdapter(base_url="http://example.test/v1").build_payload(
        _request(tool_choice=choice)
    )

    assert payload["tool_choice"] == {"type": "function", "function": {"name": "x"}}
