# %%
"""Bindings for the structured text BDD scenario."""

from __future__ import annotations

from py_lib_testkit import evidence
from pydantic import BaseModel, Field
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object

scenarios("structured_output/text.feature")

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_TEST_MODULE = "tests/llm_router/bdd/structured_output/test_text.py"


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


def _usage_payload(response: LLMRouterResponse) -> object:
    return (
        response.usage.model_dump(mode="json") if response.usage is not None else None
    )


@given("the QwenChat structured text route", target_fixture="router")
def qwenchat_structured_text_route() -> LLMRouter:
    """Build the public QwenChat route used by the BDD scenario."""
    return LLMRouter(
        RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


@when("the route receives the incident request:", target_fixture="response")
def request_incident_report(router: LLMRouter, docstring: str) -> LLMRouterResponse:
    """Execute the structured text request from the Gherkin Doc String."""
    return router.query(
        f"{_SYSTEM_PROMPT}\n\n{docstring}\n",
        response_schema=IncidentReport,
    )


@then("the incident report preserves the required identifiers and list sizes")
def incident_report_is_preserved(response: LLMRouterResponse) -> None:
    """Validate and publish the business-relevant incident result."""
    report = IncidentReport.model_validate(parse_json_object(response.output_text))
    assert response.data is not None
    assert report.incident_id == "INC-1042"
    assert len(report.affected_services) == 2
    assert len(report.timeline) == 4
    assert len(report.remediation_items) == 3
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "incident_report": report.model_dump(mode="json"),
        },
    )


# %% Run this cell in VS Code's Interactive Window for a real provider call.
if __name__ == "__main__":
    import ipytest

    ipytest.run(
        "-q",
        "-s",
        "--disable-recording",
        "--no-cov",
        _TEST_MODULE,
        defopts=False,
        raise_on_error=True,
    )
# %%
