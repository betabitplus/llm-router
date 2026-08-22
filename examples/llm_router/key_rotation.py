"""Automatic key rotation and limits
=================================

Use ``key_id="auto"`` for repeated real requests and inspect key selection and
wait information.
"""
# sphinx_gallery_tags = ["routing", "keys", "limits"]
# sphinx_gallery_thumbnail_path = "_static/gallery/key-rotation.svg"
# %%

from __future__ import annotations

import asyncio

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile


async def main() -> None:
    """Run three live requests through automatic key selection."""
    router = LLMRouter(
        RouterProfile(
            provider=Provider.NVIDIA,
            model=Model.LLAMA_8B,
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

    for expected in ("A", "B", "C"):
        response = await router.aquery(f"Reply only with {expected}.")
        attempt = response.routing_trace[0]
        print(
            f"reply={response.output_text.strip()} "
            f"provider={attempt.provider} key_id={attempt.key_id} "
            f"wait_seconds={attempt.wait_seconds:.3f}"
        )


# %%
if __name__ == "__main__":
    asyncio.run(main())
