"""Property-based verification tests for `llm_router`.

Why:
    Marks the property-based verification layer as its own test package so
    tooling can apply package-level boundary rules to it.

What belongs here:
    Property-based verification grouped by boundary family first, then by
    concept or private mechanism.

What does not belong here:
    Replay-backed e2e scenarios or one mixed file that bundles many unrelated
    concepts together.
"""
