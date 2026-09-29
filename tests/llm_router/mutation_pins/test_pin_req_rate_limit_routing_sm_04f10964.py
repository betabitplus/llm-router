# mutation-pin: REQ_RATE_LIMIT_ROUTING SM-04F10964
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import dataclass

import pytest

from llm_router._api.types import Provider
from llm_router._internal.runtime.router import RouterRuntime

pytestmark = pytest.mark.verification_kind("unit")


@dataclass
class FakeCandidate:
    key_id: int


@dataclass
class FakeRoute:
    provider: Provider
    route_index: int


@dataclass
class FakeSettings:
    key_id: object


class RotatingKeys:
    def __init__(self) -> None:
        self.calls = 0
        self.seen: list[tuple[Provider, object]] = []

    def candidates(self, *, provider: Provider, key_id: object) -> list[FakeCandidate]:
        self.seen.append((provider, key_id))
        return [FakeCandidate(1), FakeCandidate(2)]

    def resolve(
        self,
        *,
        provider: Provider,
        key_id: object,
        preferred_key_ids: set[int] | None,
    ) -> FakeCandidate:
        self.seen.append((provider, key_id))
        pool = sorted(preferred_key_ids or {1, 2})
        chosen = pool[self.calls % len(pool)]
        self.calls += 1
        return FakeCandidate(chosen)


class FreeLimiter:
    def __init__(self) -> None:
        self.waits = {1: 0.0, 2: 0.0}

    def wait_seconds(self, *, provider: Provider, key_id: int) -> float:
        assert provider is Provider.OPENROUTER
        return self.waits[key_id]


@pytest.mark.verifies("REQ_RATE_LIMIT_ROUTING[revision==1]")
def test_available_keys_rotate_before_reuse() -> None:
    runtime = object.__new__(RouterRuntime)
    runtime._keys = RotatingKeys()
    runtime._limiter = FreeLimiter()
    runtime._messages_for_content = lambda content: []
    used = []
    for index in range(2):
        request, wait = runtime._prepare_request(
            request_id=f"req-{index}",
            route=FakeRoute(provider=Provider.OPENROUTER, route_index=0),
            settings=FakeSettings(key_id="auto"),
            content="hello",
        )
        assert wait == 0.0
        used.append(request.key.key_id)
    assert used[0] != used[1]
