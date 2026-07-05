# %%
"""LLM Router e2e: public request precedence and schema defaults.

Why:
    Verifies that public router defaults, route defaults, per-call overrides,
    and explicit `None` clearing behave according to the caller-facing
    precedence contract.

Covers:
    Area: public request contract
    Behavior: router default precedence, per-call override precedence,
    explicit `None` clearing, route-default structured schema, per-call schema
    override
    Interface: `LLMRouter(...)`, `RouterProfile(...)`, `query(...)`

Checks:
    If the call omits temperature and seed, then the request succeeds, the provider
    payload uses router defaults, and the routing trace records the same defaults.
    If the call sets temperature and seed, then the request succeeds, the provider
    payload uses the call values, and the routing trace records those overrides.
    If the call passes explicit `None` for temperature and seed, then the request
    succeeds, the provider payload omits those fields, and the routing trace records
    `None` for both values.
    If the call omits `response_schema`, then the request succeeds with the route-
    default structured envelope and the provider payload advertises the route-default
    schema name.
    If the call sets `response_schema`, then the request succeeds with the per-call
    structured envelope and the provider payload advertises the override schema name.
    If the call sets `response_schema=None`, then the request succeeds with plain text
    and the provider payload omits `response_format` entirely.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server through a worker helper that temporarily patches SDK
    entry points in-process.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.settings_overrides_and_propagation.test_request_precedence_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/settings_overrides_and_propagation/test_request_precedence_pipeline.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest
from py_lib_tooling import console
from pydantic import BaseModel

from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.contract import (
    ContractWorkerResult,
    run_contract_worker_batch,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_structured,
    pytest.mark.hermetic,
]


# =============================================================================
# Scenario
# =============================================================================

_PORT = 0
_PATH = openai_chat_path()
_ROUTER_TEMPERATURE = 0.7
_ROUTER_SEED = 11
_CALL_TEMPERATURE = 0.0
_CALL_SEED = 42
_DEFAULT_TEXT = "precedence-ok"
_ROUTE_SCHEMA_TEXT = '{"status":"route-default"}'
_OVERRIDE_SCHEMA_TEXT = '{"code":200}'
_SCHEMA_CLEARED_TEXT = "schema-cleared-ok"
_ROUTE_SCHEMA_NAME = "RouteDefaultEnvelope"
_CALL_OVERRIDE_SCHEMA_NAME = "CallOverrideEnvelope"
_SCENARIO_SEQUENCE = [
    "router_defaults",
    "call_overrides",
    "call_none_clears_defaults",
    "route_schema_default",
    "call_schema_override",
    "call_schema_none_clears_default",
]


# =============================================================================
# Helpers
# =============================================================================


class RouteDefaultEnvelope(BaseModel):
    """Structured output used for the route-default schema scenario."""

    status: str


class CallOverrideEnvelope(BaseModel):
    """Structured output used for the per-call schema-override scenario."""

    code: int


@dataclass(frozen=True, slots=True)
class PrecedenceBatchResult:
    """Batched worker results and captured request payloads."""

    results_by_scenario: dict[str, ContractWorkerResult]
    payloads_by_scenario: dict[str, dict[str, object]]


def success_routes(*, text: str) -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build a single-success OpenAI-compatible route."""
    return {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=text),
            )
        ]
    }


def batched_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build one response script that covers every precedence scenario."""
    return {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_DEFAULT_TEXT),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_DEFAULT_TEXT),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_DEFAULT_TEXT),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_ROUTE_SCHEMA_TEXT),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_OVERRIDE_SCHEMA_TEXT),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_SCHEMA_CLEARED_TEXT),
            ),
        ]
    }


def first_request_payload(server: ScriptedHTTPServer) -> dict[str, object]:
    """Return the first recorded OpenAI-compatible request body as JSON."""
    requests = server.recorded_requests("POST", _PATH)
    return json.loads(requests[0].body.decode("utf-8"))


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline(
    *,
    scenario: str,
    server_base_url: str,
) -> ContractWorkerResult:
    """Run one public precedence scenario through the shared worker helper."""
    # Keep the public story simple in pytest: choose one contract scenario and
    # let the worker execute the real router call.
    return run_contract_worker_batch(
        scenarios=[scenario],
        server_base_url=server_base_url,
    )[scenario]


@pytest.fixture(scope="module")
def precedence_batch_result() -> PrecedenceBatchResult:
    """Run all precedence scenarios once and share the captured results."""
    with ScriptedHTTPServer(
        port=_PORT,
        routes=batched_routes(),
    ) as server:
        results_by_scenario = run_contract_worker_batch(
            scenarios=_SCENARIO_SEQUENCE,
            server_base_url=server.base_url,
        )
        recorded_requests = server.recorded_requests("POST", _PATH)

    payloads_by_scenario = {
        scenario: json.loads(request.body.decode("utf-8"))
        for scenario, request in zip(
            _SCENARIO_SEQUENCE,
            recorded_requests,
            strict=True,
        )
    }
    return PrecedenceBatchResult(
        results_by_scenario=results_by_scenario,
        payloads_by_scenario=payloads_by_scenario,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_router_defaults_apply(
    result: ContractWorkerResult,
    *,
    request_payload: dict[str, object],
) -> None:
    """Assert router defaults apply when the call omits overrides."""
    # The worker must finish successfully before we reason about precedence.
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message
    # The visible answer proves the request itself still succeeded normally.
    assert result.output_text == _DEFAULT_TEXT

    payload = request_payload
    # The outbound provider payload is the strongest proof that router-level
    # defaults were actually used.
    assert payload["temperature"] == _ROUTER_TEMPERATURE
    assert payload["seed"] == _ROUTER_SEED
    assert "response_format" not in payload

    # The routing trace should reflect the same generation settings.
    assert len(result.routing_trace) == 1
    assert result.routing_trace[0]["temperature"] == _ROUTER_TEMPERATURE
    assert result.routing_trace[0]["seed"] == _ROUTER_SEED


def assert_call_overrides_apply(
    result: ContractWorkerResult,
    *,
    request_payload: dict[str, object],
) -> None:
    """Assert explicit per-call values override router defaults."""
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message
    assert result.output_text == _DEFAULT_TEXT

    payload = request_payload
    # These request fields prove the call-level values won the precedence race.
    assert payload["temperature"] == _CALL_TEMPERATURE
    assert payload["seed"] == _CALL_SEED

    assert len(result.routing_trace) == 1
    assert result.routing_trace[0]["temperature"] == _CALL_TEMPERATURE
    assert result.routing_trace[0]["seed"] == _CALL_SEED


def assert_explicit_none_clears_defaults(
    result: ContractWorkerResult,
    *,
    request_payload: dict[str, object],
) -> None:
    """Assert explicit `None` clears router defaults instead of omission."""
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message
    assert result.output_text == _DEFAULT_TEXT

    payload = request_payload
    # The contract here is subtle: omitted and explicit `None` are different,
    # so the defaulted fields should disappear instead of falling back.
    assert "temperature" not in payload
    assert "seed" not in payload

    assert len(result.routing_trace) == 1
    assert result.routing_trace[0]["temperature"] is None
    assert result.routing_trace[0]["seed"] is None


def assert_route_schema_default_applies(
    result: ContractWorkerResult,
    *,
    request_payload: dict[str, object],
) -> None:
    """Assert route-level structured schema applies when the call omits one."""
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message
    parsed = RouteDefaultEnvelope.model_validate_json(result.output_text)
    assert parsed.status == "route-default"

    payload = request_payload
    response_format = payload["response_format"]
    assert isinstance(response_format, dict)
    json_schema = response_format["json_schema"]
    assert isinstance(json_schema, dict)
    # The schema name proves the route default, not a per-call override, was sent.
    assert json_schema["name"] == _ROUTE_SCHEMA_NAME


def assert_call_schema_override_applies(
    result: ContractWorkerResult,
    *,
    request_payload: dict[str, object],
) -> None:
    """Assert per-call schema overrides the route-level default schema."""
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message
    parsed = CallOverrideEnvelope.model_validate_json(result.output_text)
    assert parsed.code == 200

    payload = request_payload
    response_format = payload["response_format"]
    assert isinstance(response_format, dict)
    json_schema = response_format["json_schema"]
    assert isinstance(json_schema, dict)
    # The override schema name is the proof that the call-level schema won.
    assert json_schema["name"] == _CALL_OVERRIDE_SCHEMA_NAME


def assert_explicit_none_clears_route_schema(
    result: ContractWorkerResult,
    *,
    request_payload: dict[str, object],
) -> None:
    """Assert explicit `response_schema=None` clears the route default schema."""
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message
    assert result.output_text == _SCHEMA_CLEARED_TEXT

    payload = request_payload
    # The provider payload should no longer advertise any structured schema.
    assert "response_format" not in payload


# =============================================================================
# Tests
# =============================================================================


def test_router_defaults_apply_when_call_omits_values(
    precedence_batch_result: PrecedenceBatchResult,
) -> None:
    """Verify router defaults apply when the call omits generation overrides."""
    assert_router_defaults_apply(
        precedence_batch_result.results_by_scenario["router_defaults"],
        request_payload=precedence_batch_result.payloads_by_scenario["router_defaults"],
    )


def test_call_overrides_replace_router_defaults(
    precedence_batch_result: PrecedenceBatchResult,
) -> None:
    """Verify explicit per-call values override router defaults."""
    assert_call_overrides_apply(
        precedence_batch_result.results_by_scenario["call_overrides"],
        request_payload=precedence_batch_result.payloads_by_scenario["call_overrides"],
    )


def test_explicit_none_clears_router_defaults(
    precedence_batch_result: PrecedenceBatchResult,
) -> None:
    """Verify explicit `None` clears router defaults instead of omission."""
    assert_explicit_none_clears_defaults(
        precedence_batch_result.results_by_scenario["call_none_clears_defaults"],
        request_payload=precedence_batch_result.payloads_by_scenario[
            "call_none_clears_defaults"
        ],
    )


def test_route_default_schema_applies_when_call_omits_schema(
    precedence_batch_result: PrecedenceBatchResult,
) -> None:
    """Verify a route-level schema applies when the call omits `response_schema`."""
    assert_route_schema_default_applies(
        precedence_batch_result.results_by_scenario["route_schema_default"],
        request_payload=precedence_batch_result.payloads_by_scenario[
            "route_schema_default"
        ],
    )


def test_call_schema_overrides_route_default_schema(
    precedence_batch_result: PrecedenceBatchResult,
) -> None:
    """Verify a per-call schema overrides the route-level default schema."""
    assert_call_schema_override_applies(
        precedence_batch_result.results_by_scenario["call_schema_override"],
        request_payload=precedence_batch_result.payloads_by_scenario[
            "call_schema_override"
        ],
    )


def test_explicit_none_clears_route_default_schema(
    precedence_batch_result: PrecedenceBatchResult,
) -> None:
    """Verify explicit `response_schema=None` clears the route-level default schema."""
    assert_explicit_none_clears_route_schema(
        precedence_batch_result.results_by_scenario["call_schema_none_clears_default"],
        request_payload=precedence_batch_result.payloads_by_scenario[
            "call_schema_none_clears_default"
        ],
    )


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the request-precedence demo flow for manual execution."""
    console.demo_intro(__doc__)

    with ScriptedHTTPServer(
        port=_PORT,
        routes=success_routes(text=_DEFAULT_TEXT),
    ) as server:
        # Show the baseline: omitted call values inherit the router defaults.
        defaults_result = run_pipeline(
            scenario="router_defaults",
            server_base_url=server.base_url,
        )
        assert_router_defaults_apply(
            defaults_result,
            request_payload=first_request_payload(server),
        )
        defaults_payload = first_request_payload(server)

        console.demo_step(
            "What Happened With Router Defaults",
            "When the call omitted temperature and seed, the router defaults "
            "were sent to the provider.",
            details=[
                f"Outbound temperature: {defaults_payload['temperature']}",
                f"Outbound seed: {defaults_payload['seed']}",
                f"Routing trace: {defaults_result.routing_trace}",
            ],
        )

    with ScriptedHTTPServer(
        port=_PORT,
        routes=success_routes(text=_DEFAULT_TEXT),
    ) as server:
        # Then show the per-call override branch.
        override_result = run_pipeline(
            scenario="call_overrides",
            server_base_url=server.base_url,
        )
        assert_call_overrides_apply(
            override_result,
            request_payload=first_request_payload(server),
        )
        override_payload = first_request_payload(server)

        console.demo_step(
            "What Happened With Per-Call Overrides",
            "The per-call temperature and seed replaced the router defaults.",
            details=[
                f"Outbound temperature: {override_payload['temperature']}",
                f"Outbound seed: {override_payload['seed']}",
                f"Routing trace: {override_result.routing_trace}",
            ],
        )

    with ScriptedHTTPServer(
        port=_PORT,
        routes=success_routes(text=_DEFAULT_TEXT),
    ) as server:
        # Finally show the explicit-None clearing branch for generation defaults.
        cleared_defaults_result = run_pipeline(
            scenario="call_none_clears_defaults",
            server_base_url=server.base_url,
        )
        assert_explicit_none_clears_defaults(
            cleared_defaults_result,
            request_payload=first_request_payload(server),
        )
        cleared_defaults_payload = first_request_payload(server)

        console.demo_step(
            "What Happened With Explicit None",
            "Passing `None` cleared the router defaults instead of behaving "
            "like omission.",
            details=[
                "Temperature present in payload: "
                f"{'temperature' in cleared_defaults_payload}",
                f"Seed present in payload: {'seed' in cleared_defaults_payload}",
                f"Routing trace: {cleared_defaults_result.routing_trace}",
            ],
        )

    with ScriptedHTTPServer(
        port=_PORT,
        routes=success_routes(text=_ROUTE_SCHEMA_TEXT),
    ) as server:
        # Start the schema side with the route-level default.
        route_schema_result = run_pipeline(
            scenario="route_schema_default",
            server_base_url=server.base_url,
        )
        assert_route_schema_default_applies(
            route_schema_result,
            request_payload=first_request_payload(server),
        )
        route_schema_payload = first_request_payload(server)

        console.demo_step(
            "What Happened With A Route Default Schema",
            "When the call omitted `response_schema`, the route-level schema "
            "was sent automatically.",
            details=[
                "Schema name: "
                f"{route_schema_payload['response_format']['json_schema']['name']}",
                f"Output text: {route_schema_result.output_text}",
            ],
        )

    with ScriptedHTTPServer(
        port=_PORT,
        routes=success_routes(text=_OVERRIDE_SCHEMA_TEXT),
    ) as server:
        # Then show the call-level schema override.
        override_schema_result = run_pipeline(
            scenario="call_schema_override",
            server_base_url=server.base_url,
        )
        assert_call_schema_override_applies(
            override_schema_result,
            request_payload=first_request_payload(server),
        )
        override_schema_payload = first_request_payload(server)

        console.demo_step(
            "What Happened With A Per-Call Schema Override",
            "The call-level schema replaced the route default for this one request.",
            details=[
                "Schema name: "
                f"{override_schema_payload['response_format']['json_schema']['name']}",
                f"Output text: {override_schema_result.output_text}",
            ],
        )

    with ScriptedHTTPServer(
        port=_PORT,
        routes=success_routes(text=_SCHEMA_CLEARED_TEXT),
    ) as server:
        # Finally show the schema-clearing branch.
        cleared_schema_result = run_pipeline(
            scenario="call_schema_none_clears_default",
            server_base_url=server.base_url,
        )
        assert_explicit_none_clears_route_schema(
            cleared_schema_result,
            request_payload=first_request_payload(server),
        )
        cleared_schema_payload = first_request_payload(server)

        console.demo_step(
            "What Happened When The Call Cleared The Schema",
            "Passing `response_schema=None` removed the route default schema "
            "from the outbound request.",
            details=[
                "response_format present in payload: "
                f"{'response_format' in cleared_schema_payload}",
                f"Output text: {cleared_schema_result.output_text}",
            ],
        )
    console.demo_outcome(
        "This passed because the outbound provider payload changed exactly the "
        "way the public precedence contract says it should."
    )


if __name__ == "__main__":
    main()
# %%
