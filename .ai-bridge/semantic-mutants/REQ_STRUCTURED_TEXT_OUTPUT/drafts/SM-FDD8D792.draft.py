# semantic-mutant: SM-FDD8D792
from __future__ import annotations

import pytest
from pydantic import BaseModel

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

_BODY = '{"count": 3, "note": null}'


class DockReport(BaseModel):
    """Report with a required nullable field."""

    count: int
    note: str | None


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_required_nullable_field_survives_structured_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A required nullable field returned as null validates and is kept."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "null-assurance-value")
    response_body = openai_success_response(text=_BODY)
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _CHAT_PATH): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=response_body,
                    )
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
            "Report the dock count and note. Use the requested schema.",
            response_schema=DockReport,
        )

    assert response.data["parsed"] == {"count": 3, "note": None}
