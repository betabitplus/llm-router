# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 7ff18671bd521f50
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_base_url_trailing_slash_is_stripped() -> None:
    with_slash = QwenChatAdapter(base_url="http://127.0.0.1:8080/api/")
    without = QwenChatAdapter(base_url="http://127.0.0.1:8080/api")

    assert with_slash.base_url == without.base_url
    assert with_slash.base_url == "http://127.0.0.1:8080/api"
    assert not with_slash.base_url.endswith("/")
