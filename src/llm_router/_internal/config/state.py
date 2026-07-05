"""Process-wide runtime config state.

Why:
    Keeps mutable installed-config state behind a tiny private boundary so
    router instances can later capture immutable snapshots at construction.
"""

from __future__ import annotations

from threading import RLock

from llm_router._internal.config.assembly import build_default_config
from llm_router._internal.config.models import LLMRouterConfig
from llm_router._internal.config.validation import validate_config
from py_lib_runtime import get_logger

_installed_config: LLMRouterConfig = build_default_config()
_config_lock = RLock()
logger = get_logger(__name__)


def get_config() -> LLMRouterConfig:
    """Return the installed config snapshot."""
    with _config_lock:
        return _installed_config


def install_config(config: object) -> LLMRouterConfig:
    """Install a validated config snapshot."""
    if not isinstance(config, LLMRouterConfig):
        msg = "install_config() expects an LLMRouterConfig instance."
        raise TypeError(msg)

    validate_config(config)
    global _installed_config  # noqa: PLW0603
    with _config_lock:
        _installed_config = config

    from llm_router._internal.providers.registry import clear_adapter_caches

    clear_adapter_caches()
    logger.info(
        "Configuration installed",
        event_type="llm_router.config.runtime.installed",
        default_provider=config.default_provider.value,
        default_model=config.default_model.value,
        provider_count=len(config.catalog.providers),
        model_count=len(config.models),
        structured_output_max_attempts=int(config.structured_output_max_attempts),
    )
    return config
