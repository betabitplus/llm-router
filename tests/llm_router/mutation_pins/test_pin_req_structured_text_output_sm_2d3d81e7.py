# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT SM-2D3D81E7
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import json
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()

_SCHEMA = {
    "type": "object",
    "properties": {
        "sku": {"type": "string"},
        "quantity": {"type": "integer"},
    },
    "required": ["sku", "quantity"],
    "additionalProperties": False,
}

_ARRAY_RECORD = {"sku": "PJ-204", "quantity": 3}
_OBJECT_RECORD = {"sku": "PJ-311", "quantity": 7}
_ARRAY_TEXT = json.dumps(_ARRAY_RECORD)
_REAL_LOADS = json.loads


def _loads_array_reply(value: Any, **kwargs: Any) -> Any:
    """Decode the first reply as a one-item array holding a valid object."""
    decoded = _REAL_LOADS(value, **kwargs)
    if value == _ARRAY_TEXT:
        return [decoded]
    return decoded


def _reply(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=text),
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_one_item_object_array_is_not_unwrapped_into_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A one-item array reply is rejected; only the real object is returned."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "inventory-assurance-value")
    monkeypatch.setattr(json, "loads", _loads_array_reply)
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _CHAT_PATH): [
                    _reply(_ARRAY_TEXT),
                    _reply(json.dumps(_OBJECT_RECORD)),
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        router = LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
        )
        response = router.query(
            "Count the pallet jacks on the shelf.",
            response_schema=_SCHEMA,
        )

    assert response.data["parsed"] == _OBJECT_RECORD
    assert response.data["parsed"] != _ARRAY_RECORD
