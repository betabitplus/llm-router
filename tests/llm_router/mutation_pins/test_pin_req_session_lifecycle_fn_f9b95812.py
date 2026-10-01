# mutation-pin: REQ_SESSION_LIFECYCLE FN-F9B95812
# pinned-by: delegate, one pin for 2 pins of SessionStore.remember
# kills: 040c94eda75a331d b38d6c310d61d789
from __future__ import annotations

import pytest

from llm_router import Session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_SESSION_LIFECYCLE[revision==1]")
def test_remember_stores_meta_and_replays_history() -> None:
    session = Session(system="system")
    meta = {"trace_id": [{"step": 1}, 0.5]}

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

    session.remember(
        user_content="next",
        assistant_text="reply",
        assistant_meta=meta,
    )

    stored_message = session.history[-1]
    assert stored_message.meta == meta

    meta["trace_id"].append("mutated-after-remember")

    assert stored_message.meta != meta
    assert stored_message.meta == {"trace_id": [{"step": 1}, 0.5]}
