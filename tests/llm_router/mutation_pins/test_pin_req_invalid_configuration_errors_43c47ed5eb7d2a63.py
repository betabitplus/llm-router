# mutation-pin: REQ_INVALID_CONFIGURATION_ERRORS 43c47ed5eb7d2a63
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import dataclasses
from typing import Any

import pytest

import llm_router as package

pytestmark = pytest.mark.verification_kind("unit")


@pytest.fixture
def restore_config() -> Any:
    original = package.get_config()
    yield original
    package.install_config(original)


@pytest.mark.verifies("REQ_INVALID_CONFIGURATION_ERRORS[revision==2]")
def test_structured_output_max_attempts_boundary(restore_config: Any) -> None:
    original = restore_config
    valid = dataclasses.replace(
        original,
        defaults=dataclasses.replace(
            original.defaults, structured_output_max_attempts=1
        ),
    )
    invalid = dataclasses.replace(
        original,
        defaults=dataclasses.replace(
            original.defaults, structured_output_max_attempts=0
        ),
    )

    assert package.install_config(valid) is valid
    with pytest.raises(
        package.ConfigurationError,
        match=r"^structured output max attempts must be at least 1\.$",
    ):
        package.install_config(invalid)
    assert package.get_config() is valid
