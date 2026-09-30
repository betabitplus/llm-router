# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT f8b19d9c5fd12b62
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    qwen_chat_path,
    qwen_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = qwen_chat_path()

_SCHEMA = {
    "title": "IncidentSummary",
    "type": "object",
    "properties": {
        "incident_id": {"type": "string"},
        "severity": {"type": "string"},
    },
    "required": ["incident_id", "severity"],
}

_MISSING_SEVERITY = {"incident_id": "INC-2048"}
_COMPLETE = {"incident_id": "INC-2048", "severity": "SEV2"}


def _scripted(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=qwen_success_response(text=text),
    )


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_metaschema_check_cannot_weaken_enforced_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_check = Draft202012Validator.check_schema
    checked: list[dict[str, Any]] = []

    def required_stripping_check(schema: dict[str, Any]) -> None:
        real_check(schema)
        checked.append(schema)
        schema.pop("required", None)

    monkeypatch.setattr(Draft202012Validator, "check_schema", required_stripping_check)
    monkeypatch.setenv("QWENCHAT_API_KEY_1", "schema-contract-value")
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _CHAT_PATH): [
                _scripted(json.dumps(_MISSING_SEVERITY)),
                _scripted(json.dumps(_COMPLETE)),
            ]
        },
    ) as server:
        config = get_config()
        base_urls = dict(config.provider_base_urls)
        base_urls[Provider.QWENCHAT] = f"{server.base_url}/api"
        install_config(
            replace(
                config,
                catalog=replace(config.catalog, provider_base_urls=base_urls),
            )
        )
        router = LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            temperature=0.0,
        )
        response = router.query(
            "Summarize the incident using the requested schema.",
            response_schema=_SCHEMA,
        )
        recorded = server.recorded_requests("POST", _CHAT_PATH)

    assert len(checked) == 1
    assert _SCHEMA["required"] == ["incident_id", "severity"]
    # The declared `required` stays enforced: the incomplete first output is
    # rejected and repaired rather than accepted as the structured result.
    assert response.data["parsed"] == _COMPLETE
    assert len(recorded) == 2
