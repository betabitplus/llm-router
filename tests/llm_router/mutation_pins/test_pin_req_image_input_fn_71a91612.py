# mutation-pin: REQ_IMAGE_INPUT FN-71A91612
# pinned-by: delegate, one pin for 2 pins of describe_media
# kills: 7476f8d4086d1401 be0c42b2c0522019
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.builders import build_test_image
from tests.llm_router.support.fault_server import ScriptedHTTPServer
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_IMAGE_INPUT[revision==1]")
def test_image_input_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    value = "assurance-openai-test"
    monkeypatch.setenv("OPENROUTER_API_KEY_1", value)
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )

    with (
        ScriptedHTTPServer(port=0, routes={}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        with pytest.raises(
            TypeError,
            match=r"Unsupported media value: object\.",
        ):
            router.query(["Describe the attached content.", object()])

        image = build_test_image()
        empty_image = image.crop((0, 0, 0, 0))
        with pytest.raises(ValueError, match=r"too small"):
            router.query(["Describe the attached scene.", empty_image])
