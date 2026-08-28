"""Rotate API keys automatically
=============================

Set ``key_id="auto"`` once, then keep making normal requests. The trace shows which
logical key was selected and whether provider limits required a wait.
"""
# sphinx_gallery_tags = ["routing", "keys", "limits"]
# sphinx_gallery_thumbnail_path = "_static/gallery/key-rotation.svg"

from __future__ import annotations

import asyncio

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile

# %%
# Configure automatic key selection
# ---------------------------------
# The deliberately low ``rps`` makes limiter behavior easy to see in a short run.
# Real key identifiers are mapped to local labels before printing so the page does
# not expose account-specific IDs.
if __name__ == "__main__":
    router = LLMRouter(
        RouterProfile(
            provider=Provider.NVIDIA,
            model=Model.LLAMA_11B_VISION,
            key_id="auto",
        ),
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=0.5,
                rpm=1_000_000_000,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
        temperature=0.0,
        seed=42,
    )

# %%
# Send repeated requests
# ----------------------
# ``aquery()`` stays identical across calls. Only the selected key and any limiter
# wait change, which makes the routing behavior visible without a raw trace dump.
if __name__ == "__main__":

    async def run_requests() -> None:
        """Send three requests and summarize automatic key selection."""
        key_labels: dict[int, str] = {}
        for number, expected in enumerate(("A", "B", "C"), start=1):
            response = await router.aquery(f"Reply only with {expected}.")
            attempt = response.routing_trace[-1]
            key_label = key_labels.setdefault(
                attempt.key_id, f"key-{len(key_labels) + 1}"
            )
            print(f"{number}. key={key_label} wait={attempt.wait_seconds:.2f}s")

    asyncio.run(run_requests())

# %%
# The first two requests use different keys immediately; the third waits before
# reusing ``key-1``, making both rotation and rate limiting visible.
