"""Multi-route execution
=====================

Give one router multiple real provider routes and inspect which route completed
the request.
"""
# sphinx_gallery_tags = ["routing", "fallback", "providers"]
# sphinx_gallery_thumbnail_path = "_static/gallery/multi-route.svg"
# %%

from __future__ import annotations

from llm_router import LLMRouter, Model, Provider, RouterProfile


def main() -> None:
    """Run a live multi-route request."""
    router = LLMRouter(
        [
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
        ],
        temperature=0.0,
        seed=42,
    )
    response = router.query(
        "Explain in two sentences why provider fallback is useful in an LLM router."
    )
    print(response.output_text)
    print("\nROUTING TRACE:")
    for attempt in response.routing_trace:
        print(attempt)


# %%
if __name__ == "__main__":
    main()
