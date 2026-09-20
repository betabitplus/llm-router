from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import vcr
from vcr.persisters.filesystem import FilesystemPersister
from vcr.serializers import yamlserializer

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.conftest import _vcr_scrub_request, _vcr_scrub_response
from tests.llm_router.support.fault_server import (
    ProviderSentinelHTTPServer,
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.vcr_extensions import (
    FILTER_HEADERS,
    MATCH_ON,
    register_vcr_extensions,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.tool_failure import openai_tool_call_response
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("integration")

_AUTH_HEADER = FILTER_HEADERS[0]
_COOKIE_HEADER = FILTER_HEADERS[-2]
_SET_COOKIE_HEADER = FILTER_HEADERS[-1]


def _marker(label: str) -> str:
    return f"fixture-{label}-value"


def _recorder() -> vcr.VCR:
    recorder = vcr.VCR(
        filter_headers=FILTER_HEADERS,
        match_on=MATCH_ON,
        decode_compressed_response=True,
        before_record_request=_vcr_scrub_request,
        before_record_response=_vcr_scrub_response,
    )
    register_vcr_extensions(recorder)
    return recorder


def echo_for_vcr(*, value: str) -> dict[str, str]:
    """Return a deterministic tool result containing the provider-supplied value."""
    return {"result": f"fixture-tool-result-{value}"}


def _persisted_request_bodies(cassette: Path) -> list[str]:
    """Load request bodies back from the physical cassette file."""
    requests, _ = FilesystemPersister.load_cassette(cassette, yamlserializer)
    return [
        body.decode("utf-8") if isinstance(body, bytes) else str(body)
        for request in requests
        if (body := request.body) is not None
    ]


@pytest.mark.verifies("TREQ_VCR_AUTH_REDACTION[revision==1]")
@pytest.mark.coverage_item("VC_VCR_AUTH_DURABLE_REDACTION")
def test_vcr_auth_and_account_data_are_removed_before_cassette_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_path = openai_chat_path()
    sidecar_path = "/capture"
    product_prompt = "safe auth redaction product prompt"
    account_email = "".join(("person", chr(64), "example.com"))
    account_body = (
        f'<a aria-label="Google Account: Person ({account_email})" '
        'href="https://accounts.google.com/SignOutOptions?x=1">'
        '<img src="https://lh3.google.com/u/0/ogw/profile-placeholder">'
        f'</a><div class="gb_g">Person</div><div>{account_email}</div>'
    )
    cassette = tmp_path / "auth.yaml"
    recorder = _recorder()
    auth_value = _marker("auth")
    cookie_value = _marker("cookie")
    set_cookie_value = _marker("set-cookie")
    monkeypatch.setenv("OPENROUTER_API_KEY_1", auth_value)

    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", provider_path): [
                    ScriptedResponse(
                        status_code=200,
                        headers={
                            "Content-Type": "application/json",
                            _SET_COOKIE_HEADER: set_cookie_value,
                            "X-Test": "keep-response",
                        },
                        body=openai_success_response(text="safe-product-response"),
                    )
                ],
            },
        ) as provider_server,
        ProviderSentinelHTTPServer(
            port=0,
            routes={
                ("POST", sidecar_path): [
                    ScriptedResponse(
                        status_code=200,
                        headers={
                            "Content-Type": "text/html",
                            _SET_COOKIE_HEADER: set_cookie_value,
                            "X-Test": "keep-response-sidecar",
                        },
                        body=account_body.encode(),
                    )
                ],
            },
        ) as sidecar_server,
    ):
        provider_base_url = f"{provider_server.base_url}/v1"
        sidecar_url = f"{sidecar_server.base_url}{sidecar_path}"
        with (
            patched_openai_sdk(
                forced_base_url=provider_base_url,
                disable_sdk_retries=True,
            ),
            recorder.use_cassette(str(cassette), record_mode="once"),
        ):
            product_response = LLMRouter(
                RouterProfile(
                    model=Model.DEEPSEEK_V3,
                    provider=Provider.OPENROUTER,
                )
            ).query(product_prompt)
            sidecar_response = httpx.post(
                sidecar_url,
                headers={
                    _COOKIE_HEADER: cookie_value,
                    "X-Test": "keep-request",
                },
                content=b"safe-body",
            )
            assert product_response.output_text == "safe-product-response"
            assert sidecar_response.status_code == 200
            assert provider_server.request_count("POST", provider_path) == 1
            assert sidecar_server.request_count("POST", sidecar_path) == 1

    persisted = cassette.read_text()
    for protected in (
        auth_value,
        cookie_value,
        set_cookie_value,
        account_email,
        ">Person<",
        "profile-placeholder",
    ):
        assert protected not in persisted
    assert "keep-request" in persisted
    assert "keep-response" in persisted
    assert "keep-response-sidecar" in persisted

    with (
        patched_openai_sdk(
            forced_base_url=provider_base_url,
            disable_sdk_retries=True,
        ),
        recorder.use_cassette(str(cassette), record_mode="none"),
    ):
        replayed_product = LLMRouter(
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
            )
        ).query(product_prompt)
        replayed_sidecar = httpx.post(
            sidecar_url,
            headers={
                _COOKIE_HEADER: _marker("other-cookie"),
                "X-Test": "keep-request",
            },
            content=b"safe-body",
        )
    assert replayed_product.output_text == "safe-product-response"
    assert replayed_sidecar.status_code == 200


@pytest.mark.verifies("TREQ_VCR_RESPONSE_CONTENT_REDACTION[revision==1]")
def test_vcr_response_scrubs_recognized_reflected_credential_before_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_path = openai_chat_path()
    protected_reflection = "AIza" + ("A" * 35)
    cassette = tmp_path / "response-reflection.yaml"
    recorder = _recorder()
    monkeypatch.setenv("OPENROUTER_API_KEY_1", _marker("response-reflection-auth"))

    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", provider_path): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text=protected_reflection),
                    )
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
        recorder.use_cassette(str(cassette), record_mode="once"),
    ):
        response = LLMRouter(
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
            )
        ).query(protected_reflection)

    assert response.output_text == protected_reflection
    persisted = cassette.read_text()
    assert protected_reflection not in persisted
    assert "DUMMY_GOOGLE_API_KEY" in persisted


@pytest.mark.verifies("TREQ_VCR_REQUEST_CONTENT_REDACTION[revision==1]")
@pytest.mark.coverage_item("VC_VCR_REQUEST_BODY_DURABLE_REDACTION")
def test_vcr_request_body_is_fingerprinted_before_cassette_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_path = openai_chat_path()
    protected_prompt = _marker("caller-prompt")
    tool_argument = _marker("tool-argument")
    tool_result = f"fixture-tool-result-{tool_argument}"
    cassette = tmp_path / "body.yaml"
    recorder = _recorder()
    monkeypatch.setenv("OPENROUTER_API_KEY_1", _marker("body-auth"))

    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", provider_path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_tool_call_response(
                        tool_name="echo_for_vcr",
                        args={"value": tool_argument},
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="safe-tool-result"),
                ),
            ]
        },
    ) as server:
        provider_base_url = f"{server.base_url}/v1"
        with (
            patched_openai_sdk(
                forced_base_url=provider_base_url,
                disable_sdk_retries=True,
            ),
            recorder.use_cassette(str(cassette), record_mode="once"),
        ):
            product_response = LLMRouter(
                RouterProfile(
                    model=Model.DEEPSEEK_V3,
                    provider=Provider.OPENROUTER,
                )
            ).query(
                protected_prompt,
                tools=[echo_for_vcr],
                tool_choice="auto",
                max_tool_rounds=2,
            )
            assert product_response.output_text == "safe-tool-result"
            assert server.request_count("POST", provider_path) == 2

    persisted = cassette.read_text()
    request_bodies = _persisted_request_bodies(cassette)
    assert len(request_bodies) == 2
    assert all(
        body.startswith("llm-router-vcr-body-sha256:") for body in request_bodies
    )
    request_payload = "\n".join(request_bodies)
    for protected in (protected_prompt, tool_argument, tool_result):
        assert protected not in request_payload
    assert protected_prompt not in persisted
    assert tool_result not in persisted

    with (
        patched_openai_sdk(
            forced_base_url=provider_base_url,
            disable_sdk_retries=True,
        ),
        recorder.use_cassette(str(cassette), record_mode="none"),
    ):
        replayed_product = LLMRouter(
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
            )
        ).query(
            protected_prompt,
            tools=[echo_for_vcr],
            tool_choice="auto",
            max_tool_rounds=2,
        )
    assert replayed_product.output_text == "safe-tool-result"
