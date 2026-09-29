# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT 5d42724e6abd7c36
# pinned-by: claude-opus-5-5 and gemini-3.1-pro-high
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderError,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    qwen_chat_path,
    qwen_success_response,
)
from tests.llm_router.support.workers.worker_patches import (
    install_worker_provider_base_url,
)

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = qwen_chat_path()

_EMPTY_FENCED_BODY = "```\n```"


class VehicleCount(BaseModel):
    """Bare vehicle count result."""

    vehicle_count: int


@pytest.fixture
def restored_config():
    original = get_config()
    yield None
    install_config(original)


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_empty_fenced_reply_is_stripped_before_validation(
    monkeypatch: pytest.MonkeyPatch,
    restored_config: None,
) -> None:
    """An empty two-line fence is unwrapped, so validation sees empty text."""
    assert restored_config is None
    monkeypatch.setenv("QWENCHAT_API_KEY_1", "fence-assurance-value")
    replies = [
        ScriptedResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=qwen_success_response(text=_EMPTY_FENCED_BODY),
        )
        for _ in range(3)
    ]
    with ScriptedHTTPServer(
        port=0,
        routes={("POST", _CHAT_PATH): replies},
    ) as server:
        install_worker_provider_base_url(
            provider="qwenchat",
            base_url=f"{server.base_url}/api",
        )
        router = LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            temperature=0.0,
        )
        with pytest.raises(ProviderError, match=r"validation failed"):
            router.query(
                "How many vehicles are at the dock? Use the requested schema.",
                response_schema=VehicleCount,
            )
        recorded = server.recorded_requests("POST", _CHAT_PATH)

    assert len(recorded) >= 2
    repair_body = recorded[1].body.decode("utf-8")
    assert "input_value=''" in repair_body
