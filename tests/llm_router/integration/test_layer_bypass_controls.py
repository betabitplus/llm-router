"""Negative controls for the layers the Verification Profiles say must not be bypassed.

Each test injects a bypass of the layer its requirement names
(``architecture.layer-bypass``) and shows that the observable property the
requirement's own tests check no longer holds: the known-bad sample goes red under
that oracle. A layer whose bypass changed nothing observable, or an oracle blind to
it, fails its control.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import vcr
from jsonschema import Draft202012Validator
from PIL import Image

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderError,
    ProviderLimits,
    RouterProfile,
    ToolExecutionError,
    get_config,
    install_config,
)
from llm_router._internal.capabilities import media as media_module
from llm_router._internal.capabilities.schema import SchemaValidationResult
from llm_router._internal.capabilities.tools import parse_tool_call
from llm_router._internal.config import build_default_config, state as config_state
from llm_router._internal.providers import registry as registry_module
from llm_router._internal.providers.base import ProviderRequest
from llm_router._internal.providers.registry import register_adapter_cache
from llm_router._internal.runtime import (
    executor as executor_module,
    router as router_module,
)
from llm_router._internal.runtime.limiter import KeyResolver
from llm_router._internal.runtime.router import RouterRuntime
from tests.llm_router.support.fault_observation import retain_local_fault_injection
from tests.llm_router.support.fault_server import (
    ProviderSentinelHTTPServer,
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.vcr_extensions import MATCH_ON, register_vcr_extensions
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.tool_failure import openai_tool_call_response
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

_BYPASS = "architecture.layer-bypass"
_OPENAI_PATH = openai_chat_path()


def _bypassed(contract_id: str, mechanism: str) -> None:
    retain_local_fault_injection(
        contract_id=contract_id, fault_class=_BYPASS, mechanism=mechanism
    )


def _router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER)
    )


def _json_response(payload: bytes, status_code: int = 200) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=payload,
    )


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
@pytest.mark.fault_item("REQ_CONFIG_INSTALLATION_COHERENCE", _BYPASS)
@pytest.mark.verification_kind("unit")
def test_runtime_that_bypasses_the_installed_snapshot_is_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = get_config()
    replacement = replace(current, default_key_id=current.default_key_id + 1)
    install_config(replacement)
    monkeypatch.setattr(router_module, "get_config", lambda: current)
    _bypassed(
        "REQ_CONFIG_INSTALLATION_COHERENCE",
        "runtime construction reads a snapshot of its own, not the installed one",
    )

    runtime = RouterRuntime(spec=replacement.default_model)

    # The installation oracle: a runtime built after install uses the replacement.
    assert runtime.config is not replacement
    assert runtime.config is current


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
@pytest.mark.fault_item("REQ_INVALID_CONFIGURATION_ERRORS", _BYPASS)
@pytest.mark.verification_kind("unit")
def test_installation_that_bypasses_validation_is_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = build_default_config()
    invalid_retry = replace(config.retry_policy, max_attempts=0)
    invalid = replace(
        config, defaults=replace(config.defaults, retry_policy=invalid_retry)
    )
    monkeypatch.setattr(config_state, "validate_config", lambda _config: None)
    _bypassed(
        "REQ_INVALID_CONFIGURATION_ERRORS",
        "installation skips the validation layer",
    )

    installed = install_config(invalid)

    # The rejection oracle: an invalid configuration raises the public error.
    assert installed is invalid
    assert get_config().retry_policy.max_attempts == 0


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
@pytest.mark.fault_item("REQ_MULTIMODAL_CONTENT_NORMALIZATION", _BYPASS)
@pytest.mark.verification_kind("integration")
def test_content_that_bypasses_normalization_is_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "local-test-key")
    monkeypatch.setattr(media_module, "_validate_image", lambda _image: None)
    _bypassed(
        "REQ_MULTIMODAL_CONTENT_NORMALIZATION",
        "raw images skip the normalization bounds before adapter execution",
    )
    current = get_config()
    with ProviderSentinelHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [_json_response(openai_success_response(text="x"))]
        },
    ) as server:
        base_urls = dict(current.provider_base_urls)
        base_urls[Provider.OPENROUTER] = f"{server.base_url}/v1"
        install_config(
            replace(
                current, catalog=replace(current.catalog, provider_base_urls=base_urls)
            )
        )
        # The unsupported mode the positive pre-provider test rejects.
        _router().query([Image.new("CMYK", (10, 10))])
        request_count = server.request_count("POST", _OPENAI_PATH)

    # The pre-provider oracle: invalid content never reaches the provider boundary.
    assert request_count == 1


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
@pytest.mark.fault_item("REQ_STRUCTURED_SCHEMA_CONTRACT", _BYPASS)
@pytest.mark.verification_kind("integration")
def test_structured_output_that_bypasses_router_validation_is_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = {
        "title": "Incident",
        "type": "object",
        "properties": {
            "incident_id": {"type": "string"},
            "severity": {"type": "string"},
        },
        "required": ["incident_id", "severity"],
    }
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "local-test-key")
    monkeypatch.setattr(
        executor_module,
        "validate_schema_output",
        lambda _spec, value: SchemaValidationResult(
            valid=True, value=json.loads(value)
        ),
    )
    _bypassed(
        "REQ_STRUCTURED_SCHEMA_CONTRACT",
        "the executor accepts provider output without router-side validation",
    )
    invalid = json.dumps({"incident_id": "INC-1"})
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    _json_response(openai_success_response(text=invalid))
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1", disable_sdk_retries=True
        ),
    ):
        response = _router().query("report", response_schema=schema)

    # The enforcement oracle: output the caller's schema rejects never comes back.
    assert not Draft202012Validator(schema).is_valid(response.data["parsed"])


@pytest.mark.verifies("TREQ_CONFIG_CACHE_INVALIDATION[revision==1]")
@pytest.mark.fault_item("TREQ_CONFIG_CACHE_INVALIDATION", _BYPASS)
@pytest.mark.verification_kind("unit")
def test_installation_that_bypasses_cache_invalidation_is_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = get_config()
    stale = object()
    cache: dict[str, object] = {"stale": stale}
    register_adapter_cache(cache)
    monkeypatch.setattr(registry_module, "clear_adapter_caches", lambda: None)
    _bypassed(
        "TREQ_CONFIG_CACHE_INVALIDATION",
        "installation skips the registered cache-invalidation transition",
    )

    install_config(replace(current, default_key_id=current.default_key_id + 1))

    # The invalidation oracle: every registered adapter cache is empty after install.
    assert cache == {"stale": stale}
    cache.clear()


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
@pytest.mark.fault_item("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION", _BYPASS)
@pytest.mark.verification_kind("integration")
def test_key_selection_that_bypasses_limiter_state_is_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-key-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-key-2")
    resolve = KeyResolver.resolve

    def rotate_without_limiter(
        self: KeyResolver,
        *,
        provider: Provider,
        key_id: Any,
        preferred_key_ids: Any = None,
    ) -> Any:
        _ = preferred_key_ids  # the bypass: what the limiter says is ignored
        return resolve(self, provider=provider, key_id=key_id)

    monkeypatch.setattr(KeyResolver, "resolve", rotate_without_limiter)
    _bypassed(
        "TREQ_RATE_LIMIT_AVAILABILITY_SELECTION",
        "automatic key selection ignores what the limiter says is available",
    )
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3, key_id="auto"
        ),
        wait_for_cooldown_if_all_blocked=False,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.0, rpm=0.0, cooldown_seconds=30.0, cooldown_after_failures=1
            )
        },
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    _json_response(
                        openai_error_response(
                            status_code=400, message="cool down key 1"
                        ),
                        status_code=400,
                    ),
                    _json_response(openai_success_response(text="key 2")),
                    _json_response(openai_success_response(text="key 2 again")),
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1", disable_sdk_retries=True
        ),
    ):
        with pytest.raises(ProviderError):
            router.query("fail key 1")
        assert router.query("use key 2").routing_trace[-1].key_id == 2
        started = time.monotonic()
        # The availability oracle: the available key is used again without waiting.
        with pytest.raises(TimeoutError):
            router.query("reuse available key")
        assert time.monotonic() - started < 1.0


@pytest.mark.verifies("TREQ_RUNTIME_LOG_SAFETY[revision==2]")
@pytest.mark.fault_item("TREQ_RUNTIME_LOG_SAFETY", _BYPASS)
@pytest.mark.verification_kind("integration")
def test_diagnostics_that_bypass_the_safe_log_context_are_detected(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    credential = "protected-bypass-credential-fixture"
    prompt = "protected-bypass-prompt-fixture"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", credential)
    safe_context = ProviderRequest.log_context

    def raw_context(self: ProviderRequest) -> dict[str, object]:
        return {
            **safe_context(self),
            "credential": self.credential.value,
            "messages": repr(self.messages),
        }

    monkeypatch.setattr(ProviderRequest, "log_context", raw_context)
    _bypassed(
        "TREQ_RUNTIME_LOG_SAFETY",
        "provider diagnostics take raw request fields around the safe log context",
    )
    caplog.set_level(logging.INFO, logger="llm_router")
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    _json_response(
                        openai_error_response(status_code=400, message="rejected"),
                        status_code=400,
                    )
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1", disable_sdk_retries=True
        ),
        pytest.raises(ProviderError),
    ):
        _router().query(prompt)
    rendered = "\n".join(
        f"{record.getMessage()} {record.msg!r} {record.__dict__!r}"
        for record in caplog.records
    )

    # The diagnostics oracle: no protected caller value appears in any log record.
    assert credential in rendered
    assert prompt in rendered


def echo_bypass(*, value: str) -> dict[str, str]:
    """A local tool that fails, as a caller's tool may."""
    raise RuntimeError(f"tool cause {value}")


@pytest.mark.verifies("TREQ_TOOL_REGISTRY[revision==1]")
@pytest.mark.fault_item("TREQ_TOOL_REGISTRY", _BYPASS)
@pytest.mark.verification_kind("integration")
def test_tool_orchestration_that_bypasses_the_registry_is_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "local-test-key")

    def round_without_registry(*, state: Any, tool_calls: Any, registry: Any) -> Any:
        for call in tool_calls:
            parsed = parse_tool_call(call)
            registry.tools[parsed.name].callable(**parsed.args)
        return state

    monkeypatch.setattr(executor_module, "run_tool_round", round_without_registry)
    _bypassed(
        "TREQ_TOOL_REGISTRY",
        "orchestration calls a tool directly instead of through the registry",
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    _json_response(
                        openai_tool_call_response(
                            tool_name="echo_bypass", args={"value": "x"}
                        )
                    ),
                    _json_response(openai_success_response(text="done")),
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1", disable_sdk_retries=True
        ),
        pytest.raises(RuntimeError, match="tool cause x") as raised,
    ):
        LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            tools=[echo_bypass],
        ).query("use the tool")

    # The execution-boundary oracle: a failing tool surfaces as the public tool error.
    assert not isinstance(raised.value, ToolExecutionError)
    assert isinstance(raised.value, RuntimeError)


def _cassette_without_scrub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    """Record one provider exchange with a recorder that has no scrub before writing."""
    auth = "fixture-bypass-auth-value"
    prompt = "fixture-bypass-caller-prompt"
    reflection = "AIza" + ("B" * 35)
    monkeypatch.setenv("OPENROUTER_API_KEY_1", auth)
    recorder = vcr.VCR(match_on=MATCH_ON, decode_compressed_response=True)
    register_vcr_extensions(recorder)
    cassette = tmp_path / "unscrubbed.yaml"
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    _json_response(openai_success_response(text=reflection))
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1", disable_sdk_retries=True
        ),
        recorder.use_cassette(str(cassette), record_mode="once"),
    ):
        _router().query(prompt)
    return {
        "persisted": cassette.read_text(),
        "auth": auth,
        "prompt": prompt,
        "reflection": reflection,
    }


@pytest.mark.verifies("TREQ_VCR_AUTH_REDACTION[revision==1]")
@pytest.mark.fault_item("TREQ_VCR_AUTH_REDACTION", _BYPASS)
@pytest.mark.verification_kind("integration")
def test_cassette_that_bypasses_auth_redaction_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bypassed(
        "TREQ_VCR_AUTH_REDACTION", "cassettes are written without the scrub layer"
    )
    recorded = _cassette_without_scrub(tmp_path, monkeypatch)

    # The durable-redaction oracle: no credential is persisted in the cassette file.
    assert recorded["auth"] in recorded["persisted"]


@pytest.mark.verifies("TREQ_VCR_REQUEST_CONTENT_REDACTION[revision==1]")
@pytest.mark.fault_item("TREQ_VCR_REQUEST_CONTENT_REDACTION", _BYPASS)
@pytest.mark.verification_kind("integration")
def test_cassette_that_bypasses_request_redaction_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bypassed(
        "TREQ_VCR_REQUEST_CONTENT_REDACTION",
        "cassettes are written without the scrub layer",
    )
    recorded = _cassette_without_scrub(tmp_path, monkeypatch)

    # The durable-redaction oracle: a request body is persisted only as a fingerprint.
    assert recorded["prompt"] in recorded["persisted"]


@pytest.mark.verifies("TREQ_VCR_RESPONSE_CONTENT_REDACTION[revision==1]")
@pytest.mark.fault_item("TREQ_VCR_RESPONSE_CONTENT_REDACTION", _BYPASS)
@pytest.mark.verification_kind("integration")
def test_cassette_that_bypasses_response_redaction_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _bypassed(
        "TREQ_VCR_RESPONSE_CONTENT_REDACTION",
        "cassettes are written without the scrub layer",
    )
    recorded = _cassette_without_scrub(tmp_path, monkeypatch)

    # The durable-redaction oracle: a reflected credential never reaches the file.
    assert recorded["reflection"] in recorded["persisted"]
