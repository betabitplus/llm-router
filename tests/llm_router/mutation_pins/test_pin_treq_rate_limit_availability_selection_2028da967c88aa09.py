# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION 2028da967c88aa09
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


class FakeKeys:
    def __init__(self) -> None:
        self.seen: list[tuple[Provider, object]] = []

    def candidates(self, *, provider: Provider, key_id: object) -> list[FakeCandidate]:
        self.seen.append((provider, key_id))
        return [FakeCandidate(1), FakeCandidate(2), FakeCandidate(3)]

    def resolve(
        self,
        *,
        provider: Provider,
        key_id: object,
        preferred_key_ids: set[int] | None,
    ) -> FakeCandidate:
        self.seen.append((provider, key_id))
        # Rotation would hand out key 1 unless preference narrows it.
        if preferred_key_ids:
            return FakeCandidate(next(iter(sorted(preferred_key_ids))))
        return FakeCandidate(1)


class FakeLimiter:
    def __init__(self, waits: dict[int, float]) -> None:
        self.waits = waits

    def wait_seconds(self, *, provider: Provider, key_id: int) -> float:
        assert provider is Provider.OPENROUTER
        return self.waits[key_id]


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
def test_all_blocked_selects_shortest_wait_key() -> None:
    runtime = object.__new__(RouterRuntime)
    runtime._keys = FakeKeys()
    runtime._limiter = FakeLimiter({1: 30.0, 2: 5.0, 3: 60.0})
    runtime._messages_for_content = lambda content: []
    request, wait = runtime._prepare_request(
        request_id="req-1",
        route=FakeRoute(provider=Provider.OPENROUTER, route_index=0),
        settings=FakeSettings(key_id="auto"),
        content="hello",
    )
    assert request.key.key_id == 2
    assert wait == 5.0
