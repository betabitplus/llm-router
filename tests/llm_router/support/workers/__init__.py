"""Subprocess-backed llm_router test support helpers.

Why:
    Groups the fault-injected worker runners, worker entrypoints, and shared
    subprocess patching used by llm_router resilience and boundary tests.

What belongs here:
    Worker runner modules, worker entrypoints, subprocess env helpers, and SDK
    patch helpers for hermetic llm_router e2e scenarios.

What does not belong here:
    Media-specific scenario helpers, VCR support, or general shared test
    infrastructure.
"""
