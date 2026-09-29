# mutation-pin: REQ_IMAGE_INPUT be0c42b2c0522019
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.builders import build_test_image
from tests.llm_router.support.fault_server import ScriptedHTTPServer
from tests.llm_router.support.workers.retry import openai_chat_path
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_OPENAI_PATH = openai_chat_path()


def _openai_router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


@pytest.mark.verifies("REQ_IMAGE_INPUT[revision==1]")
def test_zero_dimension_image_is_rejected_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "zero-dimension-guard-openai")
    image = build_test_image()
    empty_image = image.crop((0, 0, 0, 0))
    router = _openai_router()

    with ScriptedHTTPServer(port=0, routes={}) as server:
        with (
            patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ),
            pytest.raises(ValueError, match=r"too small"),
        ):
            router.query(
                ["Describe the attached scene.", empty_image],
            )
        assert server.recorded_requests("POST", _OPENAI_PATH) == []
