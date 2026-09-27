from __future__ import annotations

from typing import Any

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.tools import (
    ToolChoice,
    ToolRegistry,
    normalize_tool_choice,
)
from llm_router._internal.providers._prompted import (
    build_tool_instruction,
    qwenchat_tool_choice_payload,
)
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.google_genai import (
    _tool_choice_payload as google_tool_choice_payload,
)
from llm_router._internal.providers.openai_compatible import (
    _tool_choice_payload as openai_tool_choice_payload,
)


def add(*, a: int, b: int) -> int:
    return a + b


pytestmark = [
    pytest.mark.verifies("REQ_TOOL_CHOICE[revision==2]"),
    pytest.mark.verification_kind("unit"),
]


@pytest.mark.coverage_item("VC_TOOL_CHOICE_NAMED_INPUT_FORMS")
@pytest.mark.parametrize(
    ("choice", "unregistered"),
    [
        ("add", "subtract"),
        (
            {"type": "function", "function": {"name": "add"}},
            {"type": "function", "function": {"name": "subtract"}},
        ),
    ],
    ids=["string", "mapping"],
)
@pytest.mark.coverage_path("case-id")
def test_named_tool_choice_input_forms_select_the_registered_tool(
    choice: str | dict[str, Any],
    unregistered: str | dict[str, Any],
) -> None:
    registry = ToolRegistry.from_tools([add])

    normalized = normalize_tool_choice(choice, registry=registry)

    assert normalized.name == "add"
    assert registry.get(normalized.name).callable is not None
    with pytest.raises(KeyError, match="Unknown tool: subtract"):
        normalize_tool_choice(unregistered, registry=registry)


def _named_choice():
    registry = ToolRegistry.from_tools([add])
    return registry, normalize_tool_choice("add", registry=registry)


@pytest.mark.coverage_item("VC_TOOL_CHOICE_NAMED_SERIALIZERS")
@pytest.mark.coverage_path("openai-compatible-shared")
def test_named_choice_serializes_for_openai_compatible_family() -> None:
    _, choice = _named_choice()

    assert openai_tool_choice_payload(choice) == {
        "type": "function",
        "function": {"name": "add"},
    }


@pytest.mark.coverage_item("VC_TOOL_CHOICE_NAMED_SERIALIZERS")
@pytest.mark.coverage_path("qwenchat")
def test_named_choice_serializes_for_qwenchat() -> None:
    registry, choice = _named_choice()
    request = ProviderRequest(
        request_id="req-tool-choice",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen/test",
        credential=ProviderCredential(key_id=1, env_var="QWENCHAT_API_KEY_1", value=""),
        messages=(),
        tool_registry=registry,
        tool_choice=choice,
    )

    assert qwenchat_tool_choice_payload(request) == {
        "type": "function",
        "function": {"name": "add"},
    }


@pytest.mark.coverage_item("VC_TOOL_CHOICE_NAMED_SERIALIZERS")
@pytest.mark.coverage_path("google-genai")
def test_named_choice_serializes_for_google_genai() -> None:
    _, choice = _named_choice()

    payload = google_tool_choice_payload(choice)

    assert payload.function_calling_config is not None
    assert payload.function_calling_config.allowed_function_names == ["add"]


@pytest.mark.coverage_item("VC_TOOL_CHOICE_NAMED_SERIALIZERS")
@pytest.mark.coverage_path("gemini-webapi")
def test_named_choice_serializes_for_gemini_webapi_prompt() -> None:
    registry, choice = _named_choice()

    prompt = build_tool_instruction(registry=registry, choice=choice)

    assert "You MUST use only the tool `add`" in prompt


def _required_choice():
    registry = ToolRegistry.from_tools([add])
    return registry, normalize_tool_choice("required", registry=registry)


@pytest.mark.coverage_item("VC_TOOL_CHOICE_REQUIRED")
@pytest.mark.coverage_path("public-input")
def test_public_choice_keywords_normalize_to_their_own_choices() -> None:
    registry = ToolRegistry.from_tools([add])

    assert normalize_tool_choice("required", registry=registry) == ToolChoice(
        kind="required"
    )
    assert normalize_tool_choice("auto", registry=registry) == ToolChoice(kind="auto")
    assert normalize_tool_choice(None, registry=registry) == ToolChoice(kind="auto")
    assert normalize_tool_choice("none", registry=registry) == ToolChoice(kind="none")


@pytest.mark.coverage_item("VC_TOOL_CHOICE_REQUIRED")
@pytest.mark.coverage_path("openai-compatible-shared")
def test_required_choice_serializes_for_openai_compatible_family() -> None:
    _, choice = _required_choice()

    assert openai_tool_choice_payload(choice) == "required"


@pytest.mark.coverage_item("VC_TOOL_CHOICE_REQUIRED")
@pytest.mark.coverage_path("qwenchat")
def test_required_choice_serializes_for_qwenchat() -> None:
    registry, choice = _required_choice()
    request = ProviderRequest(
        request_id="req-tool-choice",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen/test",
        credential=ProviderCredential(key_id=1, env_var="QWENCHAT_API_KEY_1", value=""),
        messages=(),
        tool_registry=registry,
        tool_choice=choice,
    )

    assert qwenchat_tool_choice_payload(request) == "required"


@pytest.mark.coverage_item("VC_TOOL_CHOICE_REQUIRED")
@pytest.mark.coverage_path("google-genai")
def test_required_choice_serializes_for_google_genai() -> None:
    _, choice = _required_choice()

    payload = google_tool_choice_payload(choice)

    assert payload.function_calling_config is not None
    assert payload.function_calling_config.mode == "ANY"
    assert payload.function_calling_config.allowed_function_names is None


@pytest.mark.coverage_item("VC_TOOL_CHOICE_REQUIRED")
@pytest.mark.coverage_path("gemini-webapi")
def test_required_choice_serializes_for_gemini_webapi_prompt() -> None:
    registry, choice = _required_choice()

    prompt = build_tool_instruction(registry=registry, choice=choice)

    assert "You MUST use tools before giving the final answer." in prompt
