"""Bindings for rich-input/structured-output upper assurance."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.builders import build_test_image
from tests.llm_router.support.fault_server import (
    ProviderSentinelHTTPServer,
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    google_success_response,
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import (
    patched_google_genai_sdk,
    patched_openai_sdk,
)

scenarios("structured_output/assurance.feature")

for _test_name, _criterion, _contracts in (
    (
        "test_rich_image_input_and_caller_schema_survive_one_provider_boundary",
        "AC_RICH_SCHEMA_MEDIA_COMPOSITION",
        (
            "REQ_STRUCTURED_TEXT_OUTPUT[revision==2]",
            "REQ_IMAGE_INPUT[revision==1]",
            "REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]",
            "REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]",
        ),
    ),
    (
        "test_invalid_schema_cannot_bypass_validation_through_rich_input",
        "ACV_RICH_INVALID_SCHEMA_PRE_PROVIDER",
        (
            "REQ_IMAGE_INPUT[revision==1]",
            "REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]",
            "REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]",
        ),
    ),
    (
        "test_two_provider_families_preserve_the_same_rich_structured_outcome",
        "AOV_RICH_PROVIDER_SWAP_EQUIVALENCE",
        (
            "REQ_STRUCTURED_TEXT_OUTPUT[revision==2]",
            "REQ_IMAGE_INPUT[revision==1]",
            "REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]",
            "REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]",
        ),
    ),
):
    globals()[_test_name] = pytest.mark.assurance_item(_criterion)(
        globals()[_test_name]
    )
    globals()[_test_name] = pytest.mark.verifies(*_contracts)(globals()[_test_name])
    globals()[_test_name] = pytest.mark.verification_kind("bdd")(globals()[_test_name])
del _contracts, _criterion, _test_name

_OPENAI_PATH = openai_chat_path()
_GOOGLE_PATH = google_generate_path(model=Model.GEMINI_FLASH)
_EXPECTED = {"scene": "urban traffic", "vehicle_count": 3}
_EXPECTED_JSON = json.dumps(_EXPECTED)


class RichObservation(BaseModel):
    scene: str
    vehicle_count: int


def _openai_router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V3,
            provider=Provider.OPENROUTER,
        ),
        temperature=0.0,
    )


def _google_router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(
            model=Model.GEMINI_FLASH,
            provider=Provider.GOOGLE,
        ),
        temperature=0.0,
    )


def _request_content() -> list[object]:
    return [
        "Describe the attached scene using the requested schema.",
        build_test_image(),
    ]


def _openai_success() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=_EXPECTED_JSON),
    )


def _google_success() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=google_success_response(text=_EXPECTED_JSON),
    )


@given("a rich image request with a caller schema", target_fixture="case")
def rich_image_request(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "rich-assurance-openai-key")
    return {}


@when("the request crosses an OpenAI-compatible provider boundary")
def execute_rich_openai_request(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(
        port=0,
        routes={("POST", _OPENAI_PATH): [_openai_success()]},
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            case["response"] = _openai_router().query(
                _request_content(),
                response_schema=RichObservation,
            )
        requests = server.recorded_requests("POST", _OPENAI_PATH)
        assert len(requests) == 1
        case["payload"] = json.loads(requests[0].body.decode("utf-8"))


@then("the provider receives both the image and caller schema")
def provider_receives_media_and_schema(case: dict[str, Any]) -> None:
    payload = case["payload"]
    content = payload["messages"][-1]["content"]

    assert any(
        part.get("type") == "image_url"
        and part.get("image_url", {}).get("url", "").startswith("data:image/")
        for part in content
        if isinstance(part, dict)
    )
    response_format = payload["response_format"]
    assert response_format["type"] == "json_schema"
    assert (
        response_format["json_schema"]["schema"] == RichObservation.model_json_schema()
    )


@then("the public result is reconstructed from the requested schema")
def public_result_is_reconstructed(case: dict[str, Any]) -> None:
    response = case["response"]

    assert response.data["parsed"] == _EXPECTED
    assert json.loads(response.output_text) == _EXPECTED


@given("a rich image request with an invalid caller schema", target_fixture="case")
def invalid_rich_schema(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "rich-assurance-openai-key")
    return {
        "schema": {
            "type": "object",
            "properties": {
                "scene": {"type": "not-a-json-schema-type"},
            },
        }
    }


@when("the invalid rich request is submitted")
def execute_invalid_rich_request(case: dict[str, Any]) -> None:
    with ProviderSentinelHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                ScriptedResponse(
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(
                        status_code=500,
                        message="provider must not receive invalid rich schema",
                    ),
                )
            ]
        },
    ) as server:
        with (
            patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ),
            pytest.raises(ValueError, match="valid Draft 2020-12 JSON Schema"),
        ):
            _openai_router().query(
                _request_content(),
                response_schema=case["schema"],
            )
        case["provider_requests"] = server.request_count("POST", _OPENAI_PATH)


@then("schema normalization fails before provider execution")
def invalid_schema_is_pre_provider(case: dict[str, Any]) -> None:
    assert case["provider_requests"] == 0


@given(
    "equivalent OpenAI-compatible and Google rich structured responses",
    target_fixture="case",
)
def equivalent_rich_responses(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "rich-assurance-openai-key")
    monkeypatch.setenv("GOOGLE_API_KEY_1", "rich-assurance-google-key")
    return {}


@when("the same image-and-schema intent runs through both provider families")
def execute_rich_provider_swap(case: dict[str, Any]) -> None:
    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", _OPENAI_PATH): [_openai_success()]},
        ) as openai_server,
        ScriptedHTTPServer(
            port=0,
            routes={("POST", _GOOGLE_PATH): [_google_success()]},
        ) as google_server,
    ):
        with patched_openai_sdk(
            forced_base_url=f"{openai_server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            case["openai"] = _openai_router().query(
                _request_content(),
                response_schema=RichObservation,
            )
        with patched_google_genai_sdk(server_base_url=google_server.base_url):
            case["google"] = _google_router().query(
                _request_content(),
                response_schema=RichObservation,
            )

        case["openai_requests"] = openai_server.request_count("POST", _OPENAI_PATH)
        case["google_requests"] = google_server.request_count("POST", _GOOGLE_PATH)


@then("both providers return the same public structured meaning")
def rich_provider_swap_is_equivalent(case: dict[str, Any]) -> None:
    openai = case["openai"]
    google = case["google"]

    assert openai.data["parsed"] == google.data["parsed"] == _EXPECTED
    assert json.loads(openai.output_text) == json.loads(google.output_text) == _EXPECTED
    assert openai.data != google.data
    assert case["openai_requests"] == 1
    assert case["google_requests"] == 1
