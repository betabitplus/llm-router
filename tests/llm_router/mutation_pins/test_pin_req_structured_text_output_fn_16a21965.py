# mutation-pin: REQ_STRUCTURED_TEXT_OUTPUT FN-16A21965
# pinned-by: delegate, one pin for 7 pins of _strip_json_fence
# kills: 25bba4d0464eefdd 594d55ab4bfdf987 5d42724e6abd7c36 8400a761e6861e17
# kills: a1048e7de4231e38 a57b176468930694 a6d49b98e29bf6d3
from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, RootModel

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderError,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
    qwen_chat_path,
    qwen_success_response,
)
from tests.llm_router.support.workers.worker_patches import (
    install_worker_provider_base_url,
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")

_CHAT_PATH = openai_chat_path()
_QWEN_PATH = qwen_chat_path()
_EXPECTED = {"scene": "loading dock", "vehicle_count": 5}


class Observation(BaseModel):
    scene: str
    vehicle_count: int


class Count(RootModel[int]):
    """Bare integer result."""


class VehicleCount(BaseModel):
    """Bare vehicle count result."""

    vehicle_count: int


@pytest.fixture
def restored_config():
    original = get_config()
    yield None
    install_config(original)


def _route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        temperature=0.0,
    )


def _server(bodies: list[str]) -> ScriptedHTTPServer:
    return ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _CHAT_PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text=text),
                )
                for text in bodies
            ]
        },
    )


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
@pytest.mark.parametrize(
    ("body", "schema", "expected"),
    [
        (f"```{json.dumps(_EXPECTED)}```", Observation, _EXPECTED),
        (f"```text\n{json.dumps(_EXPECTED)}\n```", Observation, _EXPECTED),
        ("\n\n  ```json\n5\n```  \n\n", Count, 5),
        ("```JSON\n7\n```", Count, 7),
        ("```json\n7\n```", Count, 7),
        ("```\n7\n```", Count, 7),
        ("```json \n5\n```", Count, 5),
        (f"```json\n{json.dumps(_EXPECTED, indent=2)}", Observation, _EXPECTED),
        (f"```json\n{json.dumps(_EXPECTED)}\n```", Observation, _EXPECTED),
    ],
    ids=[
        "single_line",
        "unknown_tag",
        "padded",
        "upper_json",
        "lower_json",
        "bare",
        "trailing_space",
        "unclosed",
        "closed",
    ],
)
def test_fenced_replies_validate_to_schema(
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    schema: type[BaseModel],
    expected: object,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "fence-assurance-value")
    with (
        _server([body]) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = _route().query("Use the requested schema.", response_schema=schema)

    assert response.data["parsed"] == expected


@pytest.mark.verifies("REQ_STRUCTURED_TEXT_OUTPUT[revision==2]")
def test_empty_fence_is_stripped_before_validation(
    monkeypatch: pytest.MonkeyPatch,
    restored_config: None,
) -> None:
    assert restored_config is None
    monkeypatch.setenv("QWENCHAT_API_KEY_1", "fence-assurance-value")
    replies = [
        ScriptedResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=qwen_success_response(text="```\n```"),
        )
        for _ in range(3)
    ]
    with ScriptedHTTPServer(
        port=0,
        routes={("POST", _QWEN_PATH): replies},
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
        recorded = server.recorded_requests("POST", _QWEN_PATH)

    assert len(recorded) >= 2
    repair_body = recorded[1].body.decode("utf-8")
    assert "input_value=''" in repair_body
