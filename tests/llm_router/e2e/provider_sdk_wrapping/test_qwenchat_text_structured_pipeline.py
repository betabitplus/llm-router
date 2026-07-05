# %%
"""LLM Router e2e: QwenChat text + structured output.

Why:
    Verifies that repair-based structured output works on plain QwenChat text
    input.

Covers:
    Area: QwenChat provider
    Behavior: structured output
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If the structured text request succeeds, then the response data is populated and
    parseable as `IncidentReport`.
    If the fixed identifier is preserved, then `incident_id` is `INC-1042`.
    If the service list shape is preserved, then `affected_services` contains exactly 2
    items.
    If the timeline shape is preserved, then `timeline` contains exactly 4 items.
    If the remediation shape is preserved, then `remediation_items` contains exactly 3
    items.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_sdk_wrapping.test_qwenchat_text_structured_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_sdk_wrapping/test_qwenchat_text_structured_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console, require_vcr_cassette_or_record_mode
from pydantic import BaseModel, Field

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_structured,
]


# =============================================================================
# Scenario
# =============================================================================

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
# The scenario is intentionally constraint-heavy so success is easy to judge
# without reading provider internals.


# =============================================================================
# Helpers
# =============================================================================


class Service(BaseModel):
    name: str = Field(description="Service name, e.g. payments-api")
    environment: str = Field(description="Environment, e.g. prod or staging")


class TimelineEvent(BaseModel):
    timestamp: str = Field(description="ISO 8601 timestamp, e.g. 2026-02-25T12:34:56Z")
    description: str


class RootCause(BaseModel):
    category: str = Field(
        description="Short category label, e.g. config, deploy, dependency"
    )
    summary: str
    contributing_factors: list[str] = Field(default_factory=list)


class RemediationItem(BaseModel):
    owner: str
    action: str
    priority: str = Field(description="One of: P0, P1, P2")
    status: str = Field(description="One of: open, in_progress, done")


class IncidentReport(BaseModel):
    incident_id: str
    title: str
    severity: str = Field(description="One of: SEV1, SEV2, SEV3")
    started_at: str = Field(description="ISO 8601 timestamp")
    ended_at: str | None = Field(default=None, description="ISO 8601 timestamp or null")
    impact_summary: str
    affected_services: list[Service]
    customer_message: str
    timeline: list[TimelineEvent]
    root_cause: RootCause
    remediation_items: list[RemediationItem]


# =============================================================================
# Pipeline
# =============================================================================


def build_prompt() -> str:
    """Build the incident-report prompt."""
    return (
        "Create an incident report for a simulated outage.\n\n"
        "Constraints:\n"
        "- Use incident_id: INC-1042\n"
        "- Severity: SEV2\n"
        "- Environment for services: prod\n"
        "- affected_services: exactly 2 items\n"
        "- timeline: exactly 4 events\n"
        "- remediation_items: exactly 3 items\n"
        "- Keep all strings short and professional.\n"
    )


def build_router() -> LLMRouter:
    """Build the router under test."""
    return LLMRouter(
        RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


def run_pipeline() -> LLMRouterResponse:
    """Run the QwenChat structured-output pipeline."""
    # Keep the real public flow tiny: one prompt plus one response schema.
    router = build_router()
    return router.query(
        f"{_SYSTEM_PROMPT}\n\n{build_prompt()}",
        response_schema=IncidentReport,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_response(response: LLMRouterResponse) -> None:
    """Assert the structured-output response."""
    # First prove the public response is populated.
    assert response.data is not None
    parsed = IncidentReport.model_validate(parse_json_object(response.output_text))
    # Then check the exact fixed fields and list sizes this scenario promised.
    assert parsed.incident_id == "INC-1042"
    assert len(parsed.affected_services) == 2
    assert len(parsed.timeline) == 4
    assert len(parsed.remediation_items) == 3


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.hermetic
@pytest.mark.vcr
def test_pipeline() -> None:
    """Verify the pipeline runs successfully and returns valid JSON."""
    require_vcr_cassette_or_record_mode(test_file=__file__, test_name="test_pipeline")
    # First run the public structured-output flow once.
    response = run_pipeline()
    # Then validate the fixed contract fields and counts.
    assert_pipeline_response(response)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the demo flow for manual execution."""
    console.demo_intro(__doc__)
    console.demo_step(
        "How We Set The Scenario Up",
        "We ask QwenChat to build a structured incident report from "
        "a plain text prompt.",
        details=[f"Prompt: {build_prompt()}"],
    )

    # Run the same plain-text-to-JSON path the test asserts.
    response = run_pipeline()
    assert_pipeline_response(response)
    parsed = IncidentReport.model_validate(parse_json_object(response.output_text))

    console.demo_step(
        "What Happened",
        "The model returned a valid incident report with the expected "
        "structure and counts.",
        details=[f"Usage: {response.usage}"],
    )
    console.print_json(parsed.model_dump(mode="json"))
    console.demo_outcome(
        "This passed because the final report preserved the required "
        "incident ID and list sizes the scenario uses as its success "
        "criteria."
    )


if __name__ == "__main__":
    main()
# %%
