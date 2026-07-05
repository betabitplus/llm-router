# %%
"""AI Studio model-list workbench script.

Why:
    Shows which models the configured AI Studio OpenAI-compatible endpoint
    exposes before any generation, schema, or media behavior is involved.

Covers:
    Area: AI Studio provider discovery
    Behavior: list available models from the live OpenAI-compatible endpoint
    Interface: `GET <base_url>/models`

Checks:
    If the live `/models` request returns `model_count > 0`, then the configured
        endpoint currently exposes at least one model.
    If the result exposes the full `models` list together with `base_url`, then the
        manual run can inspect the actual catalog served by that configured endpoint.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.aistudio.models_list
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.aistudio.models_list
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from py_lib_tooling import console
from workbench.llm_router.aistudio._sdk_helpers import api_key_env_name, openai_base_url

# =============================================================================
# Scenario
# =============================================================================

# Keep the configured OpenAI-compatible base URL fixed so this probe shows the
# exact model catalog the rest of the AI Studio workbench scripts depend on.
_BASE_URL = openai_base_url().rstrip("/")
_API_KEY_ENV = api_key_env_name()


# =============================================================================
# Helpers
# =============================================================================


def _created_label(value: object) -> str | None:
    """Convert a Unix timestamp into a stable UTC label when present."""
    if not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value, tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _model_summary(item: object) -> dict[str, Any]:
    """Extract stable model fields from one live catalog entry."""
    raw = cast("dict[str, Any]", item)
    summary = {
        "id": raw.get("id"),
        "owned_by": raw.get("owned_by"),
    }
    created_label = _created_label(raw.get("created"))
    if created_label is not None:
        summary["created"] = created_label
    return summary


def _build_models_table(models: list[dict[str, Any]]) -> str:
    """Render the full live model catalog in a readable plain-text table."""
    headers = ("ID", "Created", "Owned By")
    rows = [
        (
            str(model.get("id", "N/A")),
            str(model.get("created", "N/A")),
            str(model.get("owned_by", "N/A")),
        )
        for model in models
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    def _line(char: str = "-") -> str:
        """Build one horizontal border line for the plain-text table."""
        return "+-" + "-+-".join(char * width for width in widths) + "-+"

    def _format_row(values: tuple[str, str, str]) -> str:
        """Pad one row into the fixed-width plain-text table layout."""
        return "| " + " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(values)
        ) + " |"

    lines = ["Available AI Studio Models", _line("="), _format_row(headers), _line()]
    lines.extend(_format_row(row) for row in rows)
    lines.append(_line("="))
    return "\n".join(lines)


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Fetch the live AI Studio model catalog through the OpenAI-compatible path."""
    url = f"{_BASE_URL}/models"
    with httpx.Client(trust_env=False, timeout=20.0) as client:
        response = client.get(
            url,
            headers={"Authorization": f"Bearer {os.environ[_API_KEY_ENV]}"},
        )
    response.raise_for_status()
    payload = cast("dict[str, Any]", response.json())

    models = payload.get("data")
    if not isinstance(models, list):
        msg = "The AI Studio model-list endpoint did not return a data list."
        raise TypeError(msg)
    if not models:
        msg = "The AI Studio model-list endpoint returned no models."
        raise RuntimeError(msg)

    summaries = [_model_summary(item) for item in models if isinstance(item, dict)]
    return {
        "base_url": _BASE_URL,
        "model_count": len(summaries),
        "models": summaries,
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Fetching the live AI Studio model catalog from the same "
        "OpenAI-compatible base URL the other AI Studio workbench probes use.",
        details=(
            f"Base URL: {_BASE_URL}",
            f"API key env: {_API_KEY_ENV}",
        ),
    )

    result = run_pipeline()
    console.demo_step(
        "Observed Model Catalog",
        "The endpoint returned a non-empty model list and rendered the full "
        "catalog in the same readable table shape as the original probe.",
        details=(
            f"model_count: {result['model_count']}",
            f"first_model_id: {result['models'][0]['id']}",
        ),
    )
    console.print(_build_models_table(cast("list[dict[str, Any]]", result["models"])))
    console.demo_outcome(
        "This is enough to trust which models are currently exposed by the "
        "configured AI Studio endpoint.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-04:
{
  "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
  "model_count": 51,
  "models": [
    {
      "id": "models/gemini-2.5-flash",
      "owned_by": "google"
    },
    {
      "id": "models/gemini-2.5-pro",
      "owned_by": "google"
    }
  ]
}
""".strip()
