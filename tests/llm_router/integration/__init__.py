"""Integration verification tests for `llm_router`.

Why:
    Marks the future integration-test layer as its own test package so
    multi-boundary collaboration checks have one stable home.

What belongs here:
    Tests that exercise cooperation between a few runtime boundaries without
    expanding into full end-to-end provider scenarios.

What does not belong here:
    Tiny local unit tests, replay-backed e2e scenarios, or generated
    property-based invariants.
"""
