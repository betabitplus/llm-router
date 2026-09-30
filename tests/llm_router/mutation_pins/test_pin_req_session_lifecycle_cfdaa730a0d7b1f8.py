# mutation-pin: REQ_SESSION_LIFECYCLE cfdaa730a0d7b1f8
# pinned-by: claude-opus-5-5 and gemini-3.1-pro-high
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import json

import pytest

from llm_router import Session

pytestmark = pytest.mark.verification_kind("unit")

SYSTEM_TEXT = "Système: réponds en français ✓"
USER_TEXT = "Où est le café à Zürich? 你好"
ASSISTANT_TEXT = "Près de la gare — naïve façade €"
LOCALE_DEFAULT = "latin-1"


def _utf8_artifact() -> bytes:
    payload = {
        "version": 1,
        "system": SYSTEM_TEXT,
        "history": [
            {
                "role": "user",
                "parts": [{"kind": "text", "text": USER_TEXT}],
                "meta": {},
            },
            {
                "role": "assistant",
                "parts": [{"kind": "text", "text": ASSISTANT_TEXT}],
                "meta": {},
            },
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


@pytest.mark.verifies("REQ_SESSION_LIFECYCLE[revision==1]")
def test_loaded_utf8_turns_replay_before_new_message_under_latin1_locale(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    raw = _utf8_artifact()

    def locale_read_text(self, encoding=None, errors=None) -> str:
        del self
        chosen = LOCALE_DEFAULT if encoding is None else encoding
        return raw.decode(chosen, errors or "strict")

    monkeypatch.setattr(type(tmp_path), "read_text", locale_read_text)

    restored = Session.load(tmp_path / "utf8-session.json")

    assert restored.system == SYSTEM_TEXT
    assert restored.build_messages("Et ensuite?") == [
        SYSTEM_TEXT,
        f"User: {USER_TEXT}",
        f"Assistant: {ASSISTANT_TEXT}",
        "User: Et ensuite?",
    ]
    assert restored.build_messages("Seul", include_history=False) == [
        SYSTEM_TEXT,
        "User: Seul",
    ]

    restored.clear()
    restored.remember(user_content="Encore ✓", assistant_text="Oui ✓")
    assert restored.build_messages("Fin") == [
        SYSTEM_TEXT,
        "User: Encore ✓",
        "Assistant: Oui ✓",
        "User: Fin",
    ]
