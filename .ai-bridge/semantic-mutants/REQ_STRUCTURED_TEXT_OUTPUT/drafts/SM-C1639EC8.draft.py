# semantic-mutant: SM-C1639EC8
from __future__ import annotations

import pytest
from pydantic import RootModel

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()

_BODY = '{"DockA": 5, "dockB": 3}'


class DockCounts(RootModel[dict[str, int]]):
    """Mapping of case-sensitive dock names to vehicle counts."""


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_mixed_case_keys_are_preserved_in_structured_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keys keep their original case in the public structured result."""
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "case-assurance-value")
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
            "How many vehicles are at each dock? Use the requested schema.",
            response_schema=DockCounts,
        )

    parsed = response.data["parsed"]
    if isinstance(parsed, RootModel):
        parsed = parsed.root
    assert parsed == {"DockA": 5, "dockB": 3}
