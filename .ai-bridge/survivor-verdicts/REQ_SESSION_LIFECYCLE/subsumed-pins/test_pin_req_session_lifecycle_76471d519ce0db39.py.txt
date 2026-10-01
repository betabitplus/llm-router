# mutation-pin: REQ_SESSION_LIFECYCLE 76471d519ce0db39
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_SESSION_LIFECYCLE[revision==1]")
def test_session_system_prompt_persists_across_clear_and_fork() -> None:
    prompt = "You are a helpful and concise assistant."
    session = Session(system=prompt)
    assert session.system == prompt

    session.clear()
    assert session.system == prompt

    forked = session.fork()
    assert forked.system == prompt
