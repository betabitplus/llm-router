# mutation-pin: REQ_SESSION_PERSISTENCE 5fd031363386257e
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import Session
from llm_router._internal.runtime.errors import SessionSerializationError

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_SESSION_PERSISTENCE[revision==1]")
def test_load_of_missing_file_raises_chained_serialization_error(
    tmp_path,
) -> None:
    missing_path = tmp_path / "missing_session.json"

    with pytest.raises(
        SessionSerializationError, match=r"Could not load session"
    ) as exc_info:
        Session.load(missing_path)

    assert isinstance(exc_info.value.__cause__, OSError)
