# mutation-pin: REQ_SESSION_PERSISTENCE cfdaa730a0d7b1f8
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json
from typing import Any

import pytest

from llm_router._internal.session import SessionStore

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_SESSION_PERSISTENCE[revision==1]")
def test_load_decodes_utf8_when_default_locale_is_latin1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    path_type = type(tmp_path)
    real_read_text = path_type.read_text

    def locale_read_text(
        self: Any,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        chosen = "latin-1" if encoding is None else encoding
        return real_read_text(self, encoding=chosen, errors=errors)

    monkeypatch.setattr(path_type, "read_text", locale_read_text)

    store = SessionStore(system="Système d'assistance — 日本語 ✓")
    store.remember(
        "Bonjour, où est le café à Zürich? 你好",
        "Réponse: naïve façade € ✓",
        {"note": "métadonnées ñ"},
    )

    session_path = tmp_path / "session.json"
    store.save(session_path)
    payload = json.loads(session_path.read_text(encoding="utf-8"))
    session_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    loaded = SessionStore.load(session_path)

    assert loaded.system == store.system
    assert loaded.history == store.history
