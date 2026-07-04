from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from llm_router import Provider, ProviderLimits
from llm_router._api.config import get_config, install_config
from llm_router._internal.runtime.limiter import LimiterState
from llm_router._internal.session.store import SessionStore


def _payloads(records: list[logging.LogRecord]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for record in records:
        if isinstance(record.msg, dict):
            payloads.append(record.msg)
        elif isinstance(record.args, dict):
            payloads.append(record.args)
        else:
            event_type = getattr(record, "event_type", None)
            if isinstance(event_type, str):
                payloads.append(dict(record.__dict__))
    return payloads


def _event_types(records: list[logging.LogRecord]) -> set[str]:
    return {
        str(payload["event_type"])
        for payload in _payloads(records)
        if "event_type" in payload
    }


def test_config_and_cache_events_use_safe_fields(caplog) -> None:
    caplog.set_level(logging.INFO, logger="llm_router")
    sensitive_value = "LOCAL_SECRET_SHOULD_NOT_APPEAR"

    install_config(get_config())

    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert "llm_router.config.runtime.installed" in _event_types(caplog.records)
    assert "llm_router.config.adapter_caches.cleared" in _event_types(caplog.records)
    assert sensitive_value not in rendered


def test_limiter_cooldown_events_include_safe_context(caplog) -> None:
    caplog.set_level(logging.INFO, logger="llm_router")
    limiter = LimiterState()
    limits = ProviderLimits(
        rps=0.0,
        rpm=0.0,
        cooldown_seconds=10.0,
        cooldown_after_failures=1,
    )

    limiter.record_failure(provider=Provider.OPENROUTER, key_id=7, limits=limits)
    limiter.record_success(provider=Provider.OPENROUTER, key_id=7, limits=limits)

    payloads = _payloads(caplog.records)
    event_types = _event_types(caplog.records)
    assert "llm_router.routing.cooldown.opened" in event_types
    assert "llm_router.routing.cooldown.cleared" in event_types
    assert all("value" not in payload for payload in payloads)


def test_session_persistence_events_do_not_log_payloads(
    tmp_path: Path,
    caplog,
) -> None:
    caplog.set_level(logging.INFO, logger="llm_router")
    prompt_text = "DO_NOT_LOG_RAW_PROMPT"
    answer_text = "DO_NOT_LOG_RAW_ANSWER"
    path = tmp_path / "session.json"
    store = SessionStore(system="SYSTEM_SECRET_SHOULD_NOT_APPEAR")

    store.remember(user_content=prompt_text, assistant_text=answer_text)
    store.save(path)
    SessionStore.load(path).fork().clear()

    event_types = _event_types(caplog.records)
    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert {
        "llm_router.session.turn.remembered",
        "llm_router.session.saved",
        "llm_router.session.loaded",
        "llm_router.session.forked",
        "llm_router.session.cleared",
    } <= event_types
    assert prompt_text not in rendered
    assert answer_text not in rendered
    assert "SYSTEM_SECRET_SHOULD_NOT_APPEAR" not in rendered
