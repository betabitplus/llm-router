# mutation-pin: REQ_CREDENTIAL_RESOLUTION FN-0FAB3592
# pinned-by: delegate, one pin for 3 pins of KeyResolver._resolve_auto
# kills: 53bdcf1990f4aaa4 e917251d85f56c41 f6c26fefc186db93
from __future__ import annotations

import pytest

from llm_router import (
    ApiKeyNotFoundError,
    LLMRouter,
    Model,
    Provider,
    ProviderLimits,
    RouterProfile,
    get_config,
)
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


class RevokingEnviron(dict[str, str]):
    """Process environment whose one credential is revoked mid-request."""

    def __init__(self, *, name: str, value: str, lookups: int) -> None:
        super().__init__({name: value})
        self.revoked_name = name
        self.remaining_lookups = lookups

    def get(self, name: str, default: str | None = None) -> str | None:  # type: ignore[override]
        if name == self.revoked_name:
            if self.remaining_lookups == 0:
                self.pop(name, None)
                return default
            self.remaining_lookups -= 1
        return super().get(name, default)


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_credential_resolution_deterministic_rotation_and_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = get_config()
    provider = Provider.NVIDIA
    spec = config.catalog.providers[provider]
    default_name = spec.api_key_env_vars[config.default_key_id]
    environ = RevokingEnviron(
        name=default_name,
        value="nvapi-revoked-mid-request",
        lookups=2,
    )
    monkeypatch.setattr("os.environ", environ)

    router_missing = LLMRouter(
        RouterProfile(model=Model.LLAMA_8B, provider=provider, key_id="auto"),
        round_robin_start=False,
        shuffle_fallbacks=False,
    )
    with pytest.raises(ApiKeyNotFoundError, match=r"not found") as exc_info:
        router_missing.query("Reply with the marker only.")

    assert environ.remaining_lookups == 0
    assert default_name not in environ
    assert exc_info.value.key_name == default_name
    assert exc_info.value.provider == provider.value
    assert exc_info.value.key_id == config.default_key_id

    monkeypatch.undo()

    prefix = "OPENROUTER_API_KEY_"
    for number in range(1, 10):
        monkeypatch.delenv(f"{prefix}{number}", raising=False)
    value = "local-route-value"
    monkeypatch.setenv(f"{prefix}2", value)

    router_with_limits = LLMRouter(
        [
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
                key_id="auto",
            ),
        ],
        round_robin_start=False,
        shuffle_fallbacks=False,
        temperature=0.0,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.01,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )

    path = openai_chat_path()
    responses = [
        ScriptedResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=openai_success_response(text=marker),
        )
        for marker in ("A", "B", "C", "D", "E", "F")
    ]

    with (
        ScriptedHTTPServer(port=0, routes={("POST", path): responses}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        first = router_with_limits.query("first")
        monkeypatch.setenv(f"{prefix}1", value)
        second = router_with_limits.query("second")

        assert [a.key_id for a in first.routing_trace] == [2]
        assert [a.key_id for a in second.routing_trace] == [1]

        monkeypatch.setenv(f"{prefix}3", value)
        router_round_robin = LLMRouter(
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id="auto",
            ),
            limits_by_provider={
                Provider.OPENROUTER: ProviderLimits(
                    rps=0.0,
                    rpm=0.0,
                    cooldown_seconds=0.0,
                    cooldown_after_failures=0,
                )
            },
        )
        used = [
            router_round_robin.query("hello").routing_trace[-1].key_id for _ in range(4)
        ]
        assert used == [1, 2, 3, 1]
