# mutation-pin: REQ_ROUTE_TIMEOUT_FALLBACK SM-908D5413
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

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


class _ZeroSeconds:
    """A zero-second timeout that is falsy and still waits like a number."""

    def __bool__(self) -> bool:
        return False

    def __float__(self) -> float:
        return 0.0

    def __index__(self) -> int:
        return 0

    def __gt__(self, other: object) -> bool:
        return False

    def __le__(self, other: object) -> bool:
        return True


@pytest.mark.verifies("REQ_ROUTE_TIMEOUT_FALLBACK[revision==1]")
def test_sync_zero_attempt_timeout_surfaces_public_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-credential"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)

    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id=1,
        ),
        attempt_timeout_seconds=_ZeroSeconds(),
    )

    chat_path = openai_chat_path()
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", chat_path): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text="slow-only-route"),
                        delay_seconds=1.0,
                    ),
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
        pytest.raises(TimeoutError, match=r"Attempt timed out"),
    ):
        router.query("test-prompt")
