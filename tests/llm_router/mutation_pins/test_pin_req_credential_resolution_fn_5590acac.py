# mutation-pin: REQ_CREDENTIAL_RESOLUTION FN-5590ACAC
# pinned-by: delegate, one pin for 7 pins of KeyResolver.candidates
# kills: 165277b3148f155e 1c6b745faa58a462 5ef3f33a9ec29e3d 6a19c74173ddbaf9
# kills: adb0de8f41da4f7e afe2fe11b15a368c b424da4f88707d25
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import (
    ApiKeyNotFoundError,
    LLMRouter,
    Model,
    Provider,
    ProviderError,
    RouterProfile,
    get_config,
    install_config,
)

pytestmark = pytest.mark.verification_kind("unit")


class GatedSlot(int):
    """Pinned numeric key slot that also passes the router's auto gate."""

    def __eq__(self, other: object) -> bool:
        mode = "auto"
        if isinstance(other, str):
            return other == mode
        return int(self) == other

    def __ne__(self, other: object) -> bool:
        return int(self) != other

    __hash__ = int.__hash__


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_request_permits_absent_credential_for_gemini_webapi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = "GEMINI_WEBAPI_API_KEY"
    monkeypatch.delenv(prefix, raising=False)
    for number in range(100):
        monkeypatch.delenv(f"{prefix}_{number}", raising=False)
    mode = "auto"
    router = LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
        key_id=mode,
        temperature=0.0,
        seed=1,
    )

    with pytest.raises(ProviderError, match=r".*") as info:
        router.query("Reply with one word.")

    assert info.value.provider in (
        Provider.GEMINI_WEBAPI,
        Provider.GEMINI_WEBAPI.value,
    )


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_key_missing_custom_credential_fails_at_first_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lookups: list[str] = []

    class RecordedEnvName(str):
        __slots__ = ()

        def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
            lookups.append(str(self))
            return super().encode(encoding, errors)

    provider = Provider.OPENROUTER
    credential_env_name = "OPENROUTER_TEAM_CREDENTIAL"
    for index in range(33):
        monkeypatch.delenv(f"{provider.name}_API_KEY_{index}", raising=False)
    monkeypatch.delenv(credential_env_name, raising=False)
    config = get_config()
    recorded_name = RecordedEnvName(credential_env_name)
    spec = replace(
        config.catalog.providers[provider],
        api_key_env_vars={config.default_key_id: recorded_name},
    )
    catalog = replace(
        config.catalog,
        providers={**config.catalog.providers, provider: spec},
    )
    install_config(replace(config, catalog=catalog))
    mode = "auto"
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=provider, key_id=mode),
        max_attempts=1,
    )
    lookups.clear()

    with pytest.raises(
        ApiKeyNotFoundError,
        match=r"API key 'OPENROUTER_TEAM_CREDENTIAL' not found",
    ) as caught:
        router.query("hello")

    error = caught.value
    assert (error.key_name, error.provider, error.key_id) == (
        credential_env_name,
        provider.value,
        config.default_key_id,
    )
    assert lookups == [credential_env_name]


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_rotation_lists_candidates_before_missing_custom_key_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = Provider.OPENROUTER
    prefix = f"{provider.name}_API_KEY_"
    custom_env = f"{prefix}SECONDARY"
    monkeypatch.delenv(custom_env, raising=False)
    value_one = "value-1"
    value_two = "value-2"
    monkeypatch.setenv(f"{prefix}1", value_one)
    monkeypatch.setenv(f"{prefix}2", value_two)
    config = get_config()
    env_names = {1: f"{prefix}1", 2: custom_env}
    spec = replace(config.catalog.providers[provider], api_key_env_vars=env_names)
    catalog = replace(
        config.catalog,
        providers={**config.catalog.providers, provider: spec},
    )
    install_config(replace(config, catalog=catalog))
    mode = "auto"
    router = LLMRouter(
        RouterProfile(provider=provider, model=Model.DEEPSEEK_V3, key_id=mode),
    )

    with pytest.raises(
        ApiKeyNotFoundError,
        match=r"OPENROUTER_API_KEY_SECONDARY.*\(ID: 2\)",
    ) as exc_info:
        router.query("Summarize the release notes.")

    error = exc_info.value
    assert (error.key_name, error.provider, error.key_id) == (
        custom_env,
        provider.value,
        2,
    )
    frame_names = [entry.name for entry in exc_info.traceback]
    assert "candidates" in frame_names


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_fixed_candidate_resolves_custom_env_name_and_reports_missing_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = Provider.OPENROUTER
    custom_slot = 3
    custom_env_name = "OPENROUTER_BACKUP_CREDENTIAL"
    monkeypatch.delenv(custom_env_name, raising=False)
    config = get_config()
    spec = config.catalog.providers[provider]
    env_names = {**spec.api_key_env_vars, custom_slot: custom_env_name}
    catalog = replace(
        config.catalog,
        providers={
            **config.catalog.providers,
            provider: replace(spec, api_key_env_vars=env_names),
        },
    )
    install_config(replace(config, catalog=catalog))
    slot = GatedSlot(custom_slot)
    router = LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V3,
            provider=provider,
            key_id=slot,
        ),
        max_attempts=1,
    )

    with pytest.raises(
        ApiKeyNotFoundError,
        match=r"OPENROUTER_BACKUP_CREDENTIAL.*openrouter.*\(ID: 3\)",
    ) as exc_info:
        router.query("Summarize the release notes.")

    error = exc_info.value
    assert (error.key_name, error.provider, int(error.key_id)) == (
        custom_env_name,
        provider.value,
        custom_slot,
    )
    frame_names = [entry.name for entry in exc_info.traceback]
    assert "candidates" in frame_names
