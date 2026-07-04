"""Provider limiter state and cooldown policy.

Why:
    Keeps per-provider and per-key request spacing independent from provider
    adapters and request payload construction.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from threading import RLock
from time import monotonic

from llm_router._api.contracts import ProviderLimits
from llm_router._api.errors import ApiKeyNotFoundError
from llm_router._api.types import KeyId, Provider
from llm_router._internal.config import LLMRouterConfig
from llm_router._support.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ResolvedKey:
    """Concrete provider key selected for one route attempt."""

    key_id: int
    env_var: str
    value: str


@dataclass(slots=True)
class LimiterBucket:
    """Mutable limiter state for one provider/key bucket."""

    next_available_at: float = 0.0
    cooldown_until: float = 0.0
    failure_count: int = 0


class KeyResolver:
    """Resolve fixed and auto-rotated provider key ids."""

    def __init__(self, config: LLMRouterConfig) -> None:
        """Create a resolver bound to one config snapshot."""
        self._config = config
        self._auto_offsets: dict[Provider, int] = {}
        self._lock = RLock()

    def resolve(self, *, provider: Provider, key_id: KeyId) -> ResolvedKey:
        """Resolve one provider key from environment state."""
        if key_id == "auto":
            return self._resolve_auto(provider=provider)
        return self._resolve_fixed(provider=provider, key_id=key_id)

    def _resolve_fixed(self, *, provider: Provider, key_id: int) -> ResolvedKey:
        """Resolve a fixed numeric provider key id."""
        env_var = self._key_name(provider=provider, key_id=key_id)
        value = os.getenv(env_var)
        if value is None:
            if _allows_missing_key(provider):
                return ResolvedKey(key_id=key_id, env_var=env_var, value="")
            raise ApiKeyNotFoundError(env_var, provider.value, key_id)
        return ResolvedKey(key_id=key_id, env_var=env_var, value=value)

    def _resolve_auto(self, *, provider: Provider) -> ResolvedKey:
        """Rotate among discovered provider keys."""
        keys = self._available_keys(provider=provider)
        if not keys:
            env_var = self._key_name(
                provider=provider, key_id=self._config.default_key_id
            )
            if _allows_missing_key(provider):
                return ResolvedKey(
                    key_id=self._config.default_key_id,
                    env_var=env_var,
                    value="",
                )
            raise ApiKeyNotFoundError(
                env_var, provider.value, self._config.default_key_id
            )
        with self._lock:
            offset = self._auto_offsets.get(provider, 0)
            key_id = keys[offset % len(keys)]
            self._auto_offsets[provider] = offset + 1
        return self._resolve_fixed(provider=provider, key_id=key_id)

    def _available_keys(self, *, provider: Provider) -> list[int]:
        """Return sorted configured or environment-discovered key ids."""
        spec = self._config.catalog.providers[provider]
        configured = [
            key_id
            for key_id, env_var in spec.api_key_env_vars.items()
            if os.getenv(env_var) is not None
        ]
        prefix = f"{provider.name}_API_KEY_"
        discovered = [
            int(name.removeprefix(prefix))
            for name in os.environ
            if name.startswith(prefix) and name.removeprefix(prefix).isdigit()
        ]
        return sorted(set(configured + discovered))

    def _key_name(self, *, provider: Provider, key_id: int) -> str:
        """Return the configured environment variable for one provider key."""
        spec = self._config.catalog.providers[provider]
        if key_id in spec.api_key_env_vars:
            return spec.api_key_env_vars[key_id]
        if spec.api_key_env_var is not None and key_id == self._config.default_key_id:
            return spec.api_key_env_var
        return f"{provider.name}_API_KEY_{key_id}"


def _allows_missing_key(provider: Provider) -> bool:
    """Return whether a provider can run without a bearer-token env var."""
    return provider in {Provider.GEMINI_WEBAPI, Provider.QWENCHAT}


class LimiterState:
    """Owns limiter buckets for one router runtime."""

    def __init__(self) -> None:
        """Create empty limiter state."""
        self._buckets: dict[tuple[str, int], LimiterBucket] = {}
        self._lock = RLock()

    def wait_seconds(
        self,
        *,
        provider: Provider | str,
        key_id: int,
        now: float | None = None,
    ) -> float:
        """Return seconds until the provider/key bucket is usable."""
        current = monotonic() if now is None else now
        with self._lock:
            bucket = self._bucket(provider=provider, key_id=key_id)
            blocked_until = max(bucket.next_available_at, bucket.cooldown_until)
            return max(0.0, blocked_until - current)

    def record_success(
        self,
        *,
        provider: Provider | str,
        key_id: int,
        limits: ProviderLimits,
        now: float | None = None,
    ) -> None:
        """Record a successful request and schedule the next allowed time."""
        current = monotonic() if now is None else now
        with self._lock:
            bucket = self._bucket(provider=provider, key_id=key_id)
            bucket.next_available_at = current + limits.min_interval_seconds()
            should_log_cleared = bool(
                bucket.failure_count or bucket.cooldown_until > current
            )
            bucket.failure_count = 0
        if should_log_cleared:
            logger.info(
                "Route cooldown cleared",
                event_type="llm_router.routing.cooldown.cleared",
                provider=provider.value if isinstance(provider, Provider) else provider,
                key_id=key_id,
            )

    def record_failure(
        self,
        *,
        provider: Provider | str,
        key_id: int,
        limits: ProviderLimits,
        now: float | None = None,
    ) -> None:
        """Record a failed request and open cooldown when configured."""
        current = monotonic() if now is None else now
        should_log_opened = False
        with self._lock:
            bucket = self._bucket(provider=provider, key_id=key_id)
            bucket.failure_count += 1
            if (
                limits.cooldown_after_failures > 0
                and bucket.failure_count >= limits.cooldown_after_failures
            ):
                bucket.cooldown_until = current + limits.cooldown_seconds
                bucket.failure_count = 0
                should_log_opened = True
        if should_log_opened:
            logger.info(
                "Route cooldown opened",
                event_type="llm_router.routing.cooldown.opened",
                provider=provider.value if isinstance(provider, Provider) else provider,
                key_id=key_id,
                wait_seconds=limits.cooldown_seconds,
            )

    def _bucket(self, *, provider: Provider | str, key_id: int) -> LimiterBucket:
        """Return mutable bucket state for provider/key."""
        bucket_key = (
            provider.value if isinstance(provider, Provider) else provider,
            key_id,
        )
        if bucket_key not in self._buckets:
            self._buckets[bucket_key] = LimiterBucket()
        return self._buckets[bucket_key]
