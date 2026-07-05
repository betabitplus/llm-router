"""llm_router-specific test support.

Why:
    Keeps helpers that depend on llm_router response shapes, provider behavior,
    or llm_router-owned test data out of the reusable shared test layer.

What belongs here:
    llm_router-specific builders, assertions, provider-specific helpers, VCR
    extensions, local scripted servers, and focused `media` / `workers`
    subpackages for larger support subsystems.

What does not belong here:
    Cross-project infrastructure that is provided by `py_lib_tooling`.
"""
