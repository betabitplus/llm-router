# mutation-pin: REQ_SESSION_LIFECYCLE 040c94eda75a331d
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_SESSION_LIFECYCLE[revision==1]")
def test_remembered_turn_has_empty_meta_and_replays_in_order() -> None:
    session = Session(system="system")
    session.remember(user_content="hello", assistant_text="answer")

    assistant_message = session.history[1]
    assert assistant_message.meta == {}
    assert assistant_message.meta is not None

    messages = session.build_messages("next")
    assert messages == [
        "system",
        "User: hello",
        "Assistant: answer",
        "User: next",
    ]
