# mutation-pin: REQ_CONFIG_INSTALLATION_COHERENCE FN-C1AE2F64
# pinned-by: delegate, one pin for 4 pins of install_config
# kills: 8139110fd930fa09 SM-39305DEA SM-48E372DD a2e61f2155653e45
from __future__ import annotations

import dataclasses
import logging
from typing import Any

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


@pytest.fixture
def restore_config() -> Any:
    original = package.get_config()
    yield original
    package.install_config(original)


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
def test_install_config_coherence(restore_config: Any) -> None:
    with pytest.raises(TypeError, match=r".+"):
        package.install_config({"name": "stand_in"})
    assert package.get_config() is restore_config

    empty_catalog = dataclasses.replace(restore_config.catalog, providers={}, models={})
    invalid_config = dataclasses.replace(restore_config, catalog=empty_catalog)
    with pytest.raises(package.ConfigurationError, match=r".+"):
        package.install_config(invalid_config)
    assert package.get_config() is restore_config

    first = dataclasses.replace(restore_config)
    second = dataclasses.replace(restore_config)
    assert first is not second
    assert first == second

    assert package.install_config(first) is first
    assert package.get_config() is first

    assert package.install_config(second) is second
    assert package.get_config() is second

    defaults = dataclasses.replace(
        restore_config.defaults,
        structured_output_max_attempts=(
            restore_config.structured_output_max_attempts + 1
        ),
    )
    replacement = dataclasses.replace(restore_config, defaults=defaults)
    recorder = ActiveConfigRecorder()
    logger = logging.getLogger("llm_router")
    level = logger.level
    logger.addHandler(recorder)
    logger.setLevel(logging.INFO)

    returned = package.install_config(replacement)

    logger.setLevel(level)
    logger.removeHandler(recorder)

    assert returned is replacement
    assert package.get_config() is replacement
    assert recorder.seen
    assert all(item is replacement for item in recorder.seen)
