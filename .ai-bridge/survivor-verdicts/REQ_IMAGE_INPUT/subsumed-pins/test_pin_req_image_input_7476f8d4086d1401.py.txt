# mutation-pin: REQ_IMAGE_INPUT 7476f8d4086d1401
# pinned-by: claude-opus-5-5
"""Regression test for REQ_IMAGE_INPUT: unsupported attachments are rejected.

Pins that the image-capable OpenAI-compatible route surfaces a TypeError for
an unsupported message-content attachment, rather than the AttributeError
that leaks out once describe_media's image-type guard is short-circuited to
always match and unconditionally validates the value as a PIL image.
"""

from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


def _openai_compatible_router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


@pytest.mark.verifies("REQ_IMAGE_INPUT[revision==1]")
def test_unsupported_attachment_raises_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "assurance-openai-key")
    unsupported_attachment = object()

    with (
        ScriptedHTTPServer(port=0, routes={}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
        pytest.raises(
            TypeError,
            match=r"Unsupported media value: object\.",
        ),
    ):
        _openai_compatible_router().query(
            ["Describe the attached content.", unsupported_attachment],
        )
