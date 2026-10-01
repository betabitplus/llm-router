# mutation-pin: REQ_SESSION_LIFECYCLE b38d6c310d61d789
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_SESSION_LIFECYCLE[revision==1]")
def test_remember_stores_assistant_meta_as_independent_copy() -> None:
    session = Session(system=None)
    meta = {"trace_id": [{"step": 1}, 0.5]}

    session.remember(
        user_content="hello",
        assistant_text="answer",
        assistant_meta=meta,
    )

    assistant_message = session.history[-1]
    assert assistant_message.meta == meta

    meta["trace_id"].append("mutated-after-remember")

    assert assistant_message.meta != meta
    assert assistant_message.meta == {"trace_id": [{"step": 1}, 0.5]}
