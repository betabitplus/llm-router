# mutation-pin: REQ_CONFIG_INSTALLATION_COHERENCE SM-39305DEA
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import dataclasses
import logging

import pytest

import llm_router as package

pytestmark = pytest.mark.verification_kind("unit")

CLEARED_EVENT = "llm_router.config.adapter_caches.cleared"


class ActiveConfigRecorder(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.seen: list[object] = []

    def emit(self, record: logging.LogRecord) -> None:
        if CLEARED_EVENT in str(record.msg) or CLEARED_EVENT in str(record.args):
            self.seen.append(package.get_config())


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
def test_adapter_caches_cleared_only_after_replacement_is_active() -> None:
    original = package.get_config()
    defaults = dataclasses.replace(
        original.defaults,
        structured_output_max_attempts=original.structured_output_max_attempts + 1,
    )
    replacement = dataclasses.replace(original, defaults=defaults)
    recorder = ActiveConfigRecorder()
    logger = logging.getLogger("llm_router")
    level = logger.level
    logger.addHandler(recorder)
    logger.setLevel(logging.INFO)

    returned = package.install_config(replacement)

    logger.setLevel(level)
    logger.removeHandler(recorder)
    active = package.get_config()
    package.install_config(original)

    assert returned is replacement
    assert active is replacement
    assert recorder.seen
    assert all(item is replacement for item in recorder.seen)
