# mutation-pin: REQ_SESSION_LIFECYCLE 214200bb10e1f588
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_SESSION_LIFECYCLE[revision==1]")
def test_build_messages_without_system_omits_none_entry() -> None:
    session = Session(system=None)
    session.remember(user_content="hello", assistant_text="answer")

    with_history = session.build_messages("next")
    without_history = session.build_messages("next", include_history=False)

    assert None not in with_history
    assert None not in without_history
    assert with_history == [
        "User: hello",
        "Assistant: answer",
        "User: next",
    ]
    assert without_history == ["User: next"]
