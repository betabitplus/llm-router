"""Bindings for sensitive-data protection BDD scenarios."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when
from vcr.request import HeadersDict

from llm_router import LLMRouter, Model, Provider, RouterProfile, ToolExecutionError
from tests.llm_router.conftest import _vcr_scrub_request, _vcr_scrub_response
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import openai_chat_path
from tests.llm_router.support.workers.tool_failure import openai_tool_call_response
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

scenarios("security/sensitive_data.feature")

_OPENAI_PATH = openai_chat_path()


def explode(*, secret: str) -> None:
    raise RuntimeError(f"tool failed for {len(secret)} characters")


@given("a provider request contains authentication data", target_fixture="case")
def provider_request_with_auth() -> dict[str, Any]:
    request = SimpleNamespace(
        method="POST",
        uri="https://gemini.google.com/example",
        headers=HeadersDict(
            {
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
                "Cookie": "SECRET_COOKIE",
                "X-Test": "keep",
            }
        ),
        body="at=SECRET_TOKEN&f.req=payload",
    )
    response = {
        "headers": HeadersDict({"Set-Cookie": "SECRET_SET_COOKIE", "X-Test": "keep"}),
        "body": {
            "string": (
                '<a aria-label="Google Account: Person (person@example.com)" '
                'href="https://accounts.google.com/SignOutOptions?x=1">'
                '<img src="https://lh3.google.com/u/0/ogw/profile-placeholder">'
                '</a><div class="gb_g">Person</div><div>person@example.com</div>'
            )
        },
    }
    return {"request": request, "response": response}


@when("the interaction is recorded")
def interaction_is_scrubbed(case: dict[str, Any]) -> None:
    case["request"] = _vcr_scrub_request(case["request"])
    case["response"] = _vcr_scrub_response(case["response"])


@then("authentication secrets are absent from the recording")
def auth_is_absent(case: dict[str, Any]) -> None:
    request = case["request"]
    response = case["response"]
    assert "Cookie" not in request.headers
    assert request.body == "f.req=payload"
    assert "Set-Cookie" not in response["headers"]
    rendered = str(response)
    for secret in (
        "SECRET_COOKIE",
        "SECRET_TOKEN",
        "SECRET_SET_COOKIE",
        "person@example.com",
        "Person",
        "profile-placeholder",
    ):
        assert secret not in rendered


@given(
    "a request contains a secret prompt, credentials, and tool arguments",
    target_fixture="case",
)
def request_with_sensitive_values(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> dict[str, Any]:
    prompt = "SECRET_PROMPT_SHOULD_NOT_APPEAR"
    credential = "SECRET_CREDENTIAL_SHOULD_NOT_APPEAR"
    tool_arg = "PRIVATE_TOOL_ARGUMENT_77341"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", credential)
    caplog.set_level(logging.INFO, logger="llm_router")
    return {
        "prompt": prompt,
        "credential": credential,
        "tool_arg": tool_arg,
        "caplog": caplog,
    }


@when("the request is processed")
def process_sensitive_request(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_tool_call_response(
                        tool_name="explode",
                        args={"secret": case["tool_arg"]},
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
            pytest.raises(ToolExecutionError),
        ):
            LLMRouter(
                RouterProfile(
                    model=Model.DEEPSEEK_V3,
                    provider=Provider.OPENROUTER,
                )
            ).query(
                case["prompt"],
                tools=[explode],
                tool_choice="required",
            )
        case["request_count"] = server.request_count("POST", _OPENAI_PATH)


@then("those values do not appear in runtime logs")
def sensitive_values_are_not_logged(case: dict[str, Any]) -> None:
    rendered = "\n".join(record.getMessage() for record in case["caplog"].records)
    assert case["request_count"] == 1
    assert case["prompt"] not in rendered
    assert case["credential"] not in rendered
    assert case["tool_arg"] not in rendered
