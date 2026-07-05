# %%
"""LLM Router public config boundary scenario.

Why:
    Verifies that the top-level package API can install and read the real
    product config snapshot end to end.
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console

from llm_router import LLMRouterConfig, get_config, install_config

pytestmark = [pytest.mark.e2e_contract, pytest.mark.hermetic]


def run_pipeline() -> LLMRouterConfig:
    """Install the active product config through the public API."""
    return install_config(get_config())


def assert_public_config_response(config: LLMRouterConfig) -> None:
    """Assert the installed public snapshot is returned unchanged."""
    assert get_config() is config


def test_public_config_pipeline() -> None:
    """The real config lifecycle works through the top-level package."""
    config = run_pipeline()
    assert_public_config_response(config)


def main() -> None:
    """Run the public config scenario as a manual demo."""
    console.demo_intro(__doc__)
    config = run_pipeline()
    assert_public_config_response(config)
    console.demo_outcome("The public config boundary is wired correctly.")


if __name__ == "__main__":
    main()

# %%
