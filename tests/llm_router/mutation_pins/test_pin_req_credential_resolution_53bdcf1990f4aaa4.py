# mutation-pin: REQ_CREDENTIAL_RESOLUTION 53bdcf1990f4aaa4
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import pytest

from llm_router import (
    ApiKeyNotFoundError,
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
)

pytestmark = pytest.mark.verification_kind("unit")


class RevokingEnviron(dict[str, str]):
    """Process environment whose one credential is revoked mid-request.

    The router lists automatic key candidates (a presence check and a value
    read of the credential) before it asks for the rotated key. The credential
    is served for exactly those lookups and then removed from the environment,
    so the rotated selection finds no discoverable key at all.
    """

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
def test_auto_resolution_missing_required_key_raises_error(
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

    router = LLMRouter(
        RouterProfile(model=Model.LLAMA_8B, provider=provider, key_id="auto"),
        round_robin_start=False,
        shuffle_fallbacks=False,
    )
    with pytest.raises(ApiKeyNotFoundError, match=r"not found") as exc_info:
        router.query("Reply with the marker only.")

    assert environ.remaining_lookups == 0
    assert default_name not in environ
    assert exc_info.value.key_name == default_name
    assert exc_info.value.provider == provider.value
    assert exc_info.value.key_id == config.default_key_id
