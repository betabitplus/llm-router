"""Declaration and facade layer for the `llm_router` public surface.

Why:
    Keeps the stable caller-facing shapes in one place while the real routing,
    provider, persistence, and retry machinery stays private.

What belongs here:
    Public DTOs, vocabulary enums, exception types, thin facade classes,
    install/read config helpers, built-in default declarations, and optional
    presets that are re-exported by `llm_router`.

What does not belong here:
    Runtime orchestration, provider adapters, session storage internals,
    config mutation mechanics, retry classification, or logging helpers.

How:
    Read this package as the "living public map" of the project.

    Start with:
    - `router.py` for the main execution facade
    - `contracts.py` for request, route, response, and trace shapes
    - `types.py` for stable provider/model vocabulary
    - `session.py` for continuity, persistence, and branching
    - `errors.py` for the public failure taxonomy
    - `config.py` and `defaults.py` for installed config and built-in defaults
    - `presets.py` for optional convenience values

Notes:
    Callers should still import from the top-level `llm_router` package.
    This `_api` package exists to organize and document the supported surface,
    not to become a second user-facing import style.
"""
