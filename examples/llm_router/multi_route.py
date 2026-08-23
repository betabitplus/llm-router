"""Route one request across providers
==================================

Give one router an ordered provider list, make one normal ``query()``, and inspect
``routing_trace`` to see exactly which routes were attempted.
"""
# sphinx_gallery_tags = ["routing", "fallback", "providers"]
# sphinx_gallery_thumbnail_path = "_static/gallery/multi-route.svg"

from __future__ import annotations

from llm_router import LLMRouter, Model, Provider, RouterProfile


# %%
# Configure the route order
# -------------------------
# The route list is the only routing-specific setup. The first successful route
# returns the response; any failed attempts remain visible in ``routing_trace``.
def build_router() -> LLMRouter:
    """Create a router with an ordered provider fallback list."""
    return LLMRouter(
        [
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
        ],
        temperature=0.0,
        seed=42,
    )


# %%
# Run one request and inspect the route
# -------------------------------------
# ``query()`` is the core action. The small summary below shows the user-facing
# answer separately from the routing evidence that produced it.
if __name__ == "__main__":
    router = build_router()
    response = router.query("Reply exactly: route-ok")

    print(f"answer: {response.output_text.strip()}")
    print("routes:")
    for number, attempt in enumerate(response.routing_trace, start=1):
        outcome = attempt.error_type or "success"
        print(f"  {number}. {attempt.provider}/{attempt.model}: {outcome}")

# %%
# Here the first route succeeded, so only one attempt appears. If it had failed,
# later route attempts would appear below it in the same trace.
