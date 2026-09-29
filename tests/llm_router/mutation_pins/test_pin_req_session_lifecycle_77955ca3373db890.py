# mutation-pin: REQ_SESSION_LIFECYCLE 77955ca3373db890
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_SESSION_LIFECYCLE[revision==1]")
def test_fork_history_is_reusable_and_source_stays_unchanged() -> None:
    session = Session(system="You are a helpful assistant.")
    session.remember(
        user_content="What is the capital of France?",
        assistant_text="Paris.",
    )
    source_history_before = session.history

    forked = session.fork()

    first_read = tuple(forked.history)
    second_read = tuple(forked.history)

    assert first_read == source_history_before
    assert second_read == source_history_before

    messages_first = forked.build_messages("Any follow-up questions?")
    messages_second = forked.build_messages("Any follow-up questions?")

    assert messages_first == messages_second
    assert session.history == source_history_before
