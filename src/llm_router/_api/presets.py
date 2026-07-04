"""Optional preset libraries for the `llm_router` public API.

Why:
    Provides reusable convenience values for common generation, routing-policy,
    and route-profile shapes.

How:
    Treat these as small building blocks, not as a second configuration
    system. They are plain public objects that can be passed directly or
    expanded with `.as_kwargs()` when appropriate.

Notes:
    Presets are convenience surface, not the primary API. The core public
    concepts remain `LLMRouter`, `RouterProfile`, `RouterConfig`, and
    `RouterPolicy`.
"""

from __future__ import annotations

from typing import ClassVar

from google.genai import types

from llm_router._api.contracts import RouterConfig, RouterPolicy, RouterProfile
from llm_router._api.types import Model, Provider

# ================================================================================
# Generation Config Presets
# ================================================================================


class Config:
    """Reusable generation default presets.

    These are opinionated bundles of `RouterConfig` for the most common
    temperature and seed shapes.
    """

    DETERMINISTIC = RouterConfig(temperature=0.0, seed=1)
    LOW_TEMP = RouterConfig(temperature=0.5)
    BALANCED = RouterConfig(temperature=1.0)
    CREATIVE = RouterConfig(temperature=1.5)


# ================================================================================
# Routing Policy Presets
# ================================================================================


class Policy:
    """Reusable routing policy presets.

    These presets encode common resilience and determinism tradeoffs such as
    fail-fast behavior, fixed route order, or shorter attempt timeouts.
    """

    FAIL_FAST = RouterPolicy(
        max_attempts=1,
        wait_for_cooldown_if_all_blocked=False,
        round_robin_start=False,
        shuffle_fallbacks=False,
    )
    NO_WAIT = RouterPolicy(wait_for_cooldown_if_all_blocked=False)
    DETERMINISTIC_ORDER = RouterPolicy(round_robin_start=False, shuffle_fallbacks=False)
    SHORT_TIMEOUT_30S = RouterPolicy(attempt_timeout_seconds=30.0)
    SHORT_TIMEOUT_120S = RouterPolicy(attempt_timeout_seconds=120.0)
    TRY_TWO_ROUTES = RouterPolicy(max_attempts=2)
    TRY_THREE_ROUTES = RouterPolicy(max_attempts=3)


# ================================================================================
# Route Profile Presets
# ================================================================================


class Profile:
    """Reusable route presets expressed as lists of `RouterProfile`.

    These are convenience route sets for recurring public use cases such as
    Gemini visual models or video-capable routes.
    """

    GEMINI_VISUAL: ClassVar[list[RouterProfile]] = [
        RouterProfile(Model.GEMINI_FLASH, provider=Provider.GOOGLE),
    ]

    GEMINI_3_VISUAL: ClassVar[list[RouterProfile]] = [
        RouterProfile(
            Model.GEMINI_3_FLASH,
            provider=Provider.GOOGLE,
            kwargs={
                "config": {
                    "tools": [types.Tool(code_execution=types.ToolCodeExecution)],
                }
            },
        ),
    ]

    QWEN_VISUAL: ClassVar[list[RouterProfile]] = [
        RouterProfile(Model.QWEN_VL_3B),
    ]

    GEMINI_VIDEO: ClassVar[list[RouterProfile]] = [
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
        RouterProfile(model=Model.GEMINI_PRO, provider=Provider.GOOGLE),
    ]
