# mutation-pin: REQ_SESSION_PERSISTENCE 5fd031363386257e
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Session

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_SESSION_PERSISTENCE[revision==1]")
def test_load_of_missing_file_raises_chained_serialization_error(
    tmp_path,
) -> None:
    missing_path = tmp_path / "missing_session.json"

    with pytest.raises(Exception, match=r"Could not load session") as exc_info:
        Session.load(missing_path)

    assert type(exc_info.value).__name__ == "SessionSerializationError"
    assert isinstance(exc_info.value.__cause__, OSError)
