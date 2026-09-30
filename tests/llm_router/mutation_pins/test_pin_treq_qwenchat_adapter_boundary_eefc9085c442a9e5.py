# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY eefc9085c442a9e5
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_advertises_tool_support() -> None:
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8080/api")

    assert QwenChatAdapter.capabilities.supports_tools is True
    assert adapter.capabilities.supports_tools is True
    assert adapter.capabilities.supports_json_schema is True
    assert adapter.capabilities.supports_video_url is False
