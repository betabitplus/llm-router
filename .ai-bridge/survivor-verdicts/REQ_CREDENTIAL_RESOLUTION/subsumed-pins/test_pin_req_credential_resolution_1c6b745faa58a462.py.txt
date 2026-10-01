# mutation-pin: REQ_CREDENTIAL_RESOLUTION 1c6b745faa58a462
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import (
    ApiKeyNotFoundError,
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)

pytestmark = pytest.mark.verification_kind("unit")

PROVIDER = Provider.OPENROUTER
CREDENTIAL_ENV_NAME = "OPENROUTER_TEAM_CREDENTIAL"


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_key_missing_custom_credential_fails_at_first_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto selection with an unset OpenRouter credential fails as a missing key.

    OpenRouter needs a bearer credential. Its default key id is mapped to a
    custom environment name that is unset, and no convention-named
    ``OPENROUTER_API_KEY_<n>`` variable exists. Automatic key selection must
    raise the public missing-key error with the custom name, provider and key
    id as soon as it lists the key candidates. It must not produce an empty
    candidate key and then read the environment for the credential again.
    """
    lookups: list[str] = []

    class RecordedEnvName(str):
        """Environment variable name that records every environment lookup."""

        __slots__ = ()

        def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
            lookups.append(str(self))
            return super().encode(encoding, errors)

    for index in range(33):
        monkeypatch.delenv(f"{PROVIDER.name}_API_KEY_{index}", raising=False)
    monkeypatch.delenv(CREDENTIAL_ENV_NAME, raising=False)
    config = get_config()
    recorded_name = RecordedEnvName(CREDENTIAL_ENV_NAME)
    spec = replace(
        config.catalog.providers[PROVIDER],
        api_key_env_vars={config.default_key_id: recorded_name},
    )
    catalog = replace(
        config.catalog,
        providers={**config.catalog.providers, PROVIDER: spec},
    )
    install_config(replace(config, catalog=catalog))
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=PROVIDER, key_id="auto"),
        max_attempts=1,
    )
    lookups.clear()

    with pytest.raises(
        ApiKeyNotFoundError, match=r"API key 'OPENROUTER_TEAM_CREDENTIAL' not found"
    ) as caught:
        router.query("hello")

    error = caught.value
    assert (error.key_name, error.provider, error.key_id) == (
        CREDENTIAL_ENV_NAME,
        PROVIDER.value,
        config.default_key_id,
    )
    assert lookups == [CREDENTIAL_ENV_NAME]
