# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY FN-EEDAB3CA
# pinned-by: delegate, one pin for 3 pins of QwenChatAdapter
# kills: 185b6874039f611f 23b422ccd29d9e9f eefc9085c442a9e5
from __future__ import annotations

import pytest

from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_capabilities() -> None:
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8080/api")
    caps = adapter.capabilities

    assert caps.supports_files is True
    assert caps.supports_images is True
    assert caps.supports_tools is True
    assert QwenChatAdapter.capabilities.supports_files is True
    assert QwenChatAdapter.capabilities.supports_images is True
    assert QwenChatAdapter.capabilities.supports_tools is True
    assert caps.supports_video_url is False
