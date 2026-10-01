# mutation-pin: TREQ_SESSION_SERIALIZATION FN-1DD7271E
# pinned-by: delegate, one pin for 7 pins of decode_session
# kills: 5e426e56bd7decaf 5eca933c7a02d62f 623b0ce689f82e48 73af7c5839a73039
# kills: 84e67158176fdd1f e4925bbc494ef9d1 f1db3a48e54f5fe2
from __future__ import annotations

import json

import pytest

from llm_router._api.types import ChatMessage
from llm_router._internal.runtime.errors import SessionSerializationError
from llm_router._internal.session.serialization import decode_session, encode_session

pytestmark = pytest.mark.verification_kind("unit")

_BAD = [
    ("[]", r"must be a JSON object"),
    ("42", r"must be a JSON object"),
    ("null", r"must be a JSON object"),
    ('"text"', r"must be a JSON object"),
    ('{"version": 1, "history": [', r"not valid JSON"),
    ("{not json", r"not valid JSON"),
    (json.dumps({"version": 2, "history": []}), r"Unsupported session"),
    (json.dumps({"history": []}), r"Unsupported session"),
    (json.dumps({"version": 1, "system": "x"}), r"history must be a list"),
    (
        json.dumps({"version": 1, "system": None, "history": ""}),
        r"history must be a list",
    ),
    (
        json.dumps({"version": 1, "system": None, "history": {}}),
        r"history must be a list",
    ),
    (
        json.dumps({"version": 1, "system": 123, "history": []}),
        r"system prompt",
    ),
    (
        json.dumps({"version": 1, "system": ["a"], "history": []}),
        r"system prompt",
    ),
]


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
@pytest.mark.parametrize(
    ("text", "pattern"),
    _BAD,
    ids=[str(i) for i in range(len(_BAD))],
)
def test_decode_rejects_bad_payloads(text: str, pattern: str) -> None:
    with pytest.raises(SessionSerializationError, match=pattern):
        decode_session(text)


@pytest.mark.verifies("TREQ_SESSION_SERIALIZATION[revision==1]")
def test_decode_preserves_system_and_tuple_history() -> None:
    expected = (
        ChatMessage(role="user", parts=(), meta={}),
        ChatMessage(role="assistant", parts=(), meta={"note": "first"}),
    )
    text = encode_session(system="Be brief.", history=expected)

    system, history = decode_session(text)

    assert system == "Be brief."
    assert isinstance(history, tuple)
    assert history == expected

    system2, history2 = decode_session(encode_session(system=system, history=history))
    assert system2 == system
    assert isinstance(history2, tuple)
    assert history2 == expected

    empty_system, empty = decode_session('{"version": 1, "history": []}')
    assert empty_system is None
    assert empty == ()
