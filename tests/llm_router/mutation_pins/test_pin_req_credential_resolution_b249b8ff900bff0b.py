# mutation-pin: REQ_CREDENTIAL_RESOLUTION b249b8ff900bff0b
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import Provider
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.limiter import KeyResolver

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_available_keys_excludes_bare_digit_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env vars whose full name is digits must not enter key discovery.

    The defect changes ``and`` to ``or`` in the discovery predicate, causing
    any environment variable whose *full name* happens to be all-digit to be
    treated as a discovered key even though it does not start with the
    provider prefix.  The test maps key-id 1 to a custom non-numeric env name
    (``<PROVIDER>_API_KEY_PRIMARY``), also sets the numeric
    ``<PROVIDER>_API_KEY_2``, and additionally sets an env var whose entire
    name is "999".  On the original code the bare-digit name is ignored and
    rotation covers exactly [1, 2]; on the defect it is included and rotation
    covers [1, 2, 999], which breaks the deterministic-rotation assertion.
    """
    provider = Provider.NVIDIA
    prefix = f"{provider.name}_API_KEY_"
    custom_env = f"{prefix}PRIMARY"
    numeric_env = f"{prefix}2"
    bare_digits_name = "999"

    config = build_default_config()
    spec = config.catalog.providers[provider]

    # Remove every env var the existing spec knows about so they don't
    # contribute extra keys beyond the two we intentionally add.
    for env_name in spec.api_key_env_vars.values():
        monkeypatch.delenv(env_name, raising=False)

    new_spec = replace(
        spec,
        api_key_env_vars={1: custom_env},
    )
    new_catalog = replace(
        config.catalog,
        providers={**config.catalog.providers, provider: new_spec},
    )
    config = replace(config, catalog=new_catalog)

    value_primary = "resolved-primary"
    value_numeric = "resolved-numeric-2"
    value_ignored = "must-not-appear"

    monkeypatch.setenv(custom_env, value_primary)
    monkeypatch.setenv(numeric_env, value_numeric)
    monkeypatch.setenv(bare_digits_name, value_ignored)

    resolver = KeyResolver(config)

    candidates = resolver.candidates(provider=provider, key_id="auto")
    candidate_ids = [c.key_id for c in candidates]

    # The bare-digit name must not appear as a discovered key.
    assert int(bare_digits_name) not in candidate_ids, (
        f"Key id {bare_digits_name} was discovered from a bare-digit env var;"
        " the 'and' predicate must require the provider prefix."
    )
    # Exactly the configured custom id (1) and the numeric suffix id (2).
    assert candidate_ids == [1, 2]

    first = resolver.resolve(provider=provider, key_id="auto")
    assert first.key_id == 1
    assert first.value == value_primary
    assert first.env_var == custom_env

    second = resolver.resolve(provider=provider, key_id="auto")
    assert second.key_id == 2
    assert second.value == value_numeric
    assert second.env_var == numeric_env

    third = resolver.resolve(provider=provider, key_id="auto")
    assert third.key_id == 1
    assert third.value == value_primary
    assert third.env_var == custom_env
