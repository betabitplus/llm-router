"""High-value invariants that benefit from generated inputs."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import example, given, settings, strategies as st

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
# The repair prompt's cap: its fixed guidance plus every dynamic component at its
# own bound (schema name 120, schema preview 500, validation detail 300 and invalid
# output 500 characters).
_REPAIR_PROMPT_CAP = 1_608
# A preview keeps whole words, so it is text of short words that fills a component
# to its bound; arbitrary text rarely has the spaces to do it.
_WORDS = st.lists(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=9),
    max_size=400,
).map(" ".join)
_REPAIR_TEXT = st.one_of(st.text(min_size=0, max_size=2_000), _WORDS)
_LONG_WORDS = "word " * 600


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
@pytest.mark.coverage_item("VC_REQUEST_OMISSION_PROPERTY")
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


@pytest.mark.verifies("TREQ_REPAIR_PROMPT_BOUNDS[revision==2]")
@pytest.mark.coverage_item("VC_REPAIR_PROMPT_BOUNDS")
@pytest.mark.verification_kind("property")
@given(
    schema_name=_REPAIR_TEXT,
    invalid_output=_REPAIR_TEXT,
    error_message=_REPAIR_TEXT,
)
@example(
    schema_name=_LONG_WORDS,
    invalid_output=_LONG_WORDS,
    error_message=_LONG_WORDS,
)
def test_repair_prompt_remains_bounded(
    *,
    schema_name: str,
    invalid_output: str,
    error_message: str,
) -> None:
    prompt = build_repair_prompt(
        spec=normalize_schema({"title": schema_name, "type": "object"}),
        invalid_output=invalid_output,
        error_message=error_message,
    )
    assert len(prompt) <= _REPAIR_PROMPT_CAP


@pytest.mark.verifies("REQ_SESSION_PERSISTENCE[revision==1]")
@pytest.mark.coverage_item("VC_SESSION_PERSISTENCE_GENERATED_STATE")
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
