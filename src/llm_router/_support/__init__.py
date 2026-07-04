"""Private cross-cutting support for `llm_router`.

Why:
    Holds shared infrastructure helpers that support multiple private
    subsystems without belonging to one domain area.

What belongs here:
    Logging helpers and other private cross-cutting support utilities.

What does not belong here:
    Public API declarations, product-specific runtime implementation, or
    reusable external test infrastructure.
"""
