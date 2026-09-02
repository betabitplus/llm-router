"""High-value invariants that benefit from generated inputs."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from llm_router._internal.capabilities.schema import (
    build_repair_prompt,
    normalize_schema,
)
from llm_router._internal.config import build_default_config
from llm_router._internal.runtime.effective_settings import (
    resolve_effective_settings,
    split_router_defaults,
)
from llm_router._internal.runtime.routes import RouteGenerationDefaults
from llm_router._internal.session import SessionStore

_OPTIONAL_TEMPERATURE = st.one_of(
    st.none(),
    st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
)
_TEXT = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789 _-", max_size=24)
_META = st.dictionaries(
    keys=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        min_size=1,
        max_size=12,
    ),
    values=st.one_of(_TEXT, st.integers(min_value=0, max_value=20), st.booleans()),
    max_size=3,
)
_TURN = st.tuples(_TEXT, _TEXT, _META)


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
@pytest.mark.verification_kind("property")
@given(
    route_temperature=_OPTIONAL_TEMPERATURE,
    router_temperature=_OPTIONAL_TEMPERATURE,
    call_temperature=_OPTIONAL_TEMPERATURE,
    call_is_set=st.booleans(),
)
def test_generation_precedence_preserves_omission_vs_explicit_none(
    *,
    route_temperature: float | None,
    router_temperature: float | None,
    call_temperature: float | None,
    call_is_set: bool,
) -> None:
    settings = resolve_effective_settings(
        config=build_default_config(),
        route_defaults=RouteGenerationDefaults(key_id=1, temperature=route_temperature),
        route_policy_defaults={},
        router_defaults=split_router_defaults(
            {} if router_temperature is None else {"temperature": router_temperature}
        ),
        call_overrides={"temperature": call_temperature} if call_is_set else {},
    )
    expected = (
        call_temperature
        if call_is_set
        else router_temperature
        if router_temperature is not None
        else route_temperature
    )
    assert settings.temperature == expected


@pytest.mark.verifies("REQ_STRUCTURED_OUTPUT_REPAIR[revision==1]")
@pytest.mark.verification_kind("property")
@given(
    invalid_output=st.text(min_size=0, max_size=2_000),
    error_message=st.text(min_size=0, max_size=2_000),
)
def test_repair_prompt_remains_bounded(
    *,
    invalid_output: str,
    error_message: str,
) -> None:
    prompt = build_repair_prompt(
        spec=normalize_schema({"title": "Reply", "type": "object"}),
        invalid_output=invalid_output,
        error_message=error_message,
    )
    assert len(prompt) <= 1_200


@pytest.mark.verifies("REQ_SESSION_PERSISTENCE[revision==1]")
@pytest.mark.verification_kind("property")
@given(turns=st.lists(_TURN, max_size=5))
@settings(deadline=None)
def test_session_save_load_round_trips_generated_text(
    turns: list[tuple[str, str, dict[str, object]]],
) -> None:
    store = SessionStore(system="system")
    for user_text, assistant_text, meta in turns:
        store.remember(
            user_content=user_text,
            assistant_text=assistant_text,
            assistant_meta=meta,
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        loaded = SessionStore.load(store.save(Path(temp_dir) / "session.json"))

    assert loaded.system == store.system
    assert loaded.history == store.history
