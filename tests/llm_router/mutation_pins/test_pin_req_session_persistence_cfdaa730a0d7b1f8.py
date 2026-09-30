# mutation-pin: REQ_SESSION_PERSISTENCE cfdaa730a0d7b1f8
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import json

import pytest

from llm_router import Session

pytestmark = pytest.mark.verification_kind("unit")

SYSTEM_PROMPT = "Système d'assistance — 日本語 ✓"


@pytest.mark.verifies("REQ_SESSION_PERSISTENCE[revision==1]")
def test_load_reads_utf8_session_under_latin1_default_locale(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    path_type = type(tmp_path)
    real_read_text = path_type.read_text

    def latin1_locale_read_text(self, encoding=None, errors=None) -> str:
        chosen = "latin-1" if encoding is None else encoding
        return real_read_text(self, encoding=chosen, errors=errors)

    session = Session(system=SYSTEM_PROMPT)
    session.remember(
        user_content="Bonjour, où est le café à Zürich? 你好",
        assistant_text="Réponse: naïve façade € ✓",
        assistant_meta={"provider": "openai", "note": "métadonnées ñ"},
    )
    session_path = tmp_path / "session.json"
    session.save(session_path)

    payload = json.loads(session_path.read_bytes().decode("utf-8"))
    session_path.write_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    monkeypatch.setattr(path_type, "read_text", latin1_locale_read_text)
    loaded = Session.load(session_path)

    assert loaded.system == SYSTEM_PROMPT
    assert loaded.history == session.history
