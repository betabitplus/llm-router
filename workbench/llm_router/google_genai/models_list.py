# %%
"""Google GenAI model-list workbench script.

Why:
    Shows which models the configured native Google GenAI SDK account can see
    before any generation, schema, media, or tool behavior is involved.

Covers:
    Area: Google GenAI provider discovery
    Behavior: list available models through the live native SDK
    Interface: `Client.models.list()`

Checks:
    If the live catalog request returns `model_count > 0`, then the configured
        credentials currently expose at least one model.
    If the result exposes the full `models` list, then the manual run can inspect the
        actual live catalog instead of a summary.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.google_genai.models_list
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.google_genai.models_list
"""

from __future__ import annotations

from typing import Any, cast

from tests.support.console import console
from workbench.llm_router.google_genai._sdk_helpers import build_client

# =============================================================================
# Scenario
# =============================================================================

# Keep the live SDK catalog probe separate from all generation scripts so a
# reader can answer "what models can this account see?" without extra noise.


# =============================================================================
# Helpers
# =============================================================================


def _model_summary(model: object) -> dict[str, Any]:
    """Extract stable metadata from one live SDK model entry."""
    methods = getattr(model, "supported_generation_methods", None) or []
    methods_list = [str(item) for item in methods] if isinstance(methods, list) else []
    return {
        "name": getattr(model, "name", None),
        "display_name": getattr(model, "display_name", None),
        "supported_generation_methods": methods_list,
    }


def _build_models_table(models: list[dict[str, Any]]) -> str:
    """Render the full live SDK catalog in a readable plain-text table."""
    headers = ("Display Name", "Model Name", "Supported Operations")
    rows = []
    for model in models:
        methods = cast("list[str]", model.get("supported_generation_methods", []))
        methods_text = ", ".join(methods) if methods else "N/A"
        rows.append(
            (
                str(model.get("display_name", "N/A")),
                str(model.get("name", "N/A")),
                methods_text,
            )
        )

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

    lines = ["Available GenAI Models", _line("="), _format_row(headers), _line()]
    lines.extend(_format_row(row) for row in rows)
    lines.append(_line("="))
    return "\n".join(lines)


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Fetch the live native Google GenAI model catalog."""
    client = build_client()
    models = list(client.models.list())
    if not models:
        msg = "The Google GenAI model-list SDK call returned no models."
        raise RuntimeError(msg)

    summaries = [_model_summary(model) for model in models]
    return {
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
        "Listing the live model catalog through the native Google GenAI SDK.",
    )

    result = run_pipeline()
    console.demo_step(
        "Observed Model Catalog",
        "The SDK returned a non-empty model list and rendered the full catalog "
        "in the same readable table shape as the original probe.",
        details=(
            f"model_count: {result['model_count']}",
            f"first_model_name: {result['models'][0]['name']}",
        ),
    )
    console.print(_build_models_table(cast("list[dict[str, Any]]", result["models"])))
    console.demo_outcome(
        "This is enough to trust which native Google GenAI models are "
        "currently visible to the configured API key.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-04:
{
  "model_count": 50,
  "models": [
    {
      "display_name": "Gemini 2.5 Flash",
      "name": "models/gemini-2.5-flash",
      "supported_generation_methods": []
    },
    {
      "display_name": "Gemini 2.5 Pro",
      "name": "models/gemini-2.5-pro",
      "supported_generation_methods": []
    }
  ]
}
""".strip()
