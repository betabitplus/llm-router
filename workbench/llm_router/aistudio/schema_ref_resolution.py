# %%
"""AI Studio schema-ref-resolution workbench script.

Why:
    Shows the AI Studio proxy quirk where nested JSON schemas should be inlined
    before a structured-output request on the OpenAI-compatible path.

Covers:
    Area: AI Studio non-video path
    Behavior: `$defs` and `$ref` removal before structured output
    Interface: `response_format={"type":"json_schema",...}`

Checks:
    If the raw nested schema reports both `$defs` and `$ref`, then the script starts
        from the exact schema shape that triggers the AI Studio quirk.
    If the resolved schema reports neither `$defs` nor `$ref`, then the local inlining
        step removed the problematic reference form.
    If the live request still returns parsed structured JSON after that rewrite, then
        the workaround preserved schema meaning while satisfying AI Studio.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.aistudio.schema_ref_resolution
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.aistudio.schema_ref_resolution
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console

from workbench.llm_router.aistudio._json_schema import (
    build_resolved_response_format,
    resolve_refs,
    schema_has_key,
)
from workbench.llm_router.aistudio._sdk_helpers import (
    build_client,
    parse_message_json,
    usage_snapshot,
)
from workbench.llm_router.aistudio._structured_output import (
    CandidatePacket,
    build_candidate_packet_prompt,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep one nested candidate-packet schema fixed so this script isolates the
# `$defs` and `$ref` inlining workaround.
_MODEL = "gemini-2.5-flash"
_PROMPT = build_candidate_packet_prompt()


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one live AI Studio request with an explicitly resolved nested schema."""
    # Build the AI Studio client, inspect the raw schema, then resolve its
    # local references before making the live request.
    client = build_client()
    raw_schema = CandidatePacket.model_json_schema()
    resolved_schema = resolve_refs(raw_schema)
    # Keep both the schema-shape flags and the parsed response so a manual run
    # shows why the workaround exists and that it still succeeds live.
    response = client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": _PROMPT}],
        response_format=build_resolved_response_format(CandidatePacket),
        temperature=0.0,
    )
    parsed = CandidatePacket.model_validate(parse_message_json(response))
    return {
        "raw_has_defs": schema_has_key(raw_schema, "$defs"),
        "raw_has_ref": schema_has_key(raw_schema, "$ref"),
        "resolved_has_defs": schema_has_key(resolved_schema, "$defs"),
        "resolved_has_ref": schema_has_key(resolved_schema, "$ref"),
        "parsed": parsed.model_dump(mode="json"),
        "usage": usage_snapshot(response),
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending a nested schema to AI Studio only after inlining its local "
        "references.",
        details=(
            f"Model: {_MODEL}",
            "Nested model: CandidatePacket",
            "Why this matters: AI Studio can mishandle `$defs` and `$ref`.",
        ),
    )

    result = run_pipeline()
    parsed = result["parsed"]
    console.demo_step(
        "Observed Resolved Schema Behavior",
        "The raw nested schema started with local references, but the resolved "
        "version did not, and the live request still returned valid JSON.",
        details=(
            f"raw_has_defs: {result['raw_has_defs']}",
            f"raw_has_ref: {result['raw_has_ref']}",
            f"resolved_has_defs: {result['resolved_has_defs']}",
            f"resolved_has_ref: {result['resolved_has_ref']}",
            f"candidate_name: {parsed['candidate_profile']['full_name']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust the schema-ref-resolution workaround used for "
        "AI Studio structured output.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03 (excerpt, cut after 12 lines):
{
  "parsed": {
    "candidate_profile": {
      "full_name": "Maya Chen",
      "strengths": [
        "Problem-solving",
        "Team collaboration",
        "Technical proficiency"
      ]
    },
    "interview_assessment": {
      "evidence": [
""".strip()
