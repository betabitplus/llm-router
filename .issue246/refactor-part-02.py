write(
    "tests/llm_router/e2e/public_boundary/test_public_config_pipeline.py",
    '''# %%
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
''',
)
write(
    "tests/llm_router/integration/test_config_lifecycle.py",
    '''"""Public config lifecycle integration tests."""

from __future__ import annotations

import pytest

from llm_router import LLMRouterConfig, get_config, install_config


def test_install_config_rejects_wrong_type() -> None:
    """The config lifecycle rejects unsupported config objects."""
    with pytest.raises(TypeError, match=r"install_config\\(\\) expects"):
        install_config(object())


def test_install_config_round_trips_real_snapshot() -> None:
    """The active immutable product config round-trips through installation."""
    config = get_config()

    assert isinstance(config, LLMRouterConfig)
    assert install_config(config) is config
    assert get_config() is config
''',
)
write(
    "tests/llm_router/property_based/public_contract/test_config_contract.py",
    '''"""Public config snapshot property tests."""

from __future__ import annotations

from hypothesis import given, strategies as st

from llm_router import LLMRouterConfig, get_config, install_config


@given(st.none())
def test_installed_config_snapshot_round_trips(value: None) -> None:
    """Generated no-op input does not change product config identity."""
    _ = value
    config = get_config()

    assert isinstance(config, LLMRouterConfig)
    assert install_config(config) is config
    assert get_config() is config
''',
)
write(
    "tests/llm_router/unit/test_public_package.py",
    '''"""Public package boundary unit tests."""

from __future__ import annotations

import llm_router as package
from llm_router import LLMRouterConfig, LLMRouterError


def test_public_exports_resolve() -> None:
    """Every declared top-level public name resolves."""
    for name in package.__all__:
        assert hasattr(package, name)


def test_public_exception_is_package_specific() -> None:
    """The package exposes its established exception base."""
    assert issubclass(LLMRouterError, Exception)


def test_public_config_exports_resolve() -> None:
