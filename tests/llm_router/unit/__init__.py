"""Unit verification tests for `llm_router`.

Why:
    Marks the future unit-test layer as its own test package so focused,
    fast verification can grow in one stable location.

What belongs here:
    Small deterministic tests for local semantics, parsing, normalization, and
    boundary-level rules that do not need multi-boundary collaboration.

What does not belong here:
    Replay-backed e2e scenarios, generated property tests, or broader
    integration flows that depend on several runtime boundaries working
    together.
"""
