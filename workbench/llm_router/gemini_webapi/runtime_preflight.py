# %%
"""Gemini WebAPI runtime-preflight workbench script.

Why:
    Shows whether the local Opera plus browser-cookie3 runtime is ready for a
    real Gemini WebAPI session.

Covers:
    Area: gemini-webapi local runtime prerequisites
    Behavior: Opera cookie file presence and decryptability
    Interface: local environment validation before a live session

Checks:
    If the local Opera cookie file exists, then the browser state Gemini WebAPI depends
        on is present on disk.
    If the decrypted cookie jar exposes `__Secure-1PSID` and related Google session
        cookies, then local cookie extraction is working well enough for a real session.
    If `ready` is true, then later Gemini WebAPI scripts are blocked on live behavior
        rather than missing runtime prerequisites.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.gemini_webapi.runtime_preflight
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.gemini_webapi.runtime_preflight
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console

from workbench.llm_router.gemini_webapi._opera_cookie_client import runtime_status

# =============================================================================
# Scenario
# =============================================================================

# This script intentionally stops before any model call. Its job is to explain
# whether later Gemini WebAPI failures are environment failures or runtime ones.

# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Inspect the local runtime prerequisites used by Gemini WebAPI."""
    # This is the one preflight check the live Gemini WebAPI scripts depend on.
    return dict(runtime_status())


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Checking the local Opera cookie database and decrypted google.com "
        "cookie jar before any live web-session call.",
    )

    result = run_pipeline()
    if not result["ready"]:
        console.demo_step(
            "Observed Runtime Gap",
            "The local browser-cookie setup is not ready, so a live Gemini "
            "WebAPI script would fail before proving anything useful.",
            details=(f"reason: {result['reason']}",),
        )
        console.print_json(result)
        console.demo_skip(str(result["reason"]))
        return

    console.demo_step(
        "Observed Runtime State",
        "The local runtime prerequisites for Gemini WebAPI are available.",
        details=(
            f"cookie_file: {result['cookie_file']}",
            f"cookie_cache_dir: {result['cookie_cache_dir']}",
            f"has_secure_1psid: {result['has_secure_1psid']}",
            f"has_secure_1psidts: {result['has_secure_1psidts']}",
            f"has_nid: {result['has_nid']}",
            "This is enough to trust that the next live script can reach a "
            "real session.",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "The local machine is ready for a real Gemini WebAPI session.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03 (excerpt):
{
  "has_nid": true,
  "has_secure_1psid": true,
  "has_secure_1psidts": true,
  "ready": true
}
""".strip()
