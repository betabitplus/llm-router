# %%
"""QwenChat structured-output E2E scenario."""

from __future__ import annotations

import json

import allure
import pytest
from IPython import get_ipython
from IPython.display import JSON, display
from pydantic import BaseModel, Field
from pytest_bdd import scenario, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_structured,
]

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_TEST_NODE = (
    "tests/llm_router/e2e/provider_sdk_wrapping/"
    "test_qwenchat_text_structured_pipeline.py::test_pipeline"
)
_PROMPT = """Create an incident report for a simulated outage.

Constraints:
- Use incident_id: INC-1042
- Severity: SEV2
- Environment for services: prod
- affected_services: exactly 2 items
- timeline: exactly 4 events
- remediation_items: exactly 3 items
- Keep all strings short and professional.
"""


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


def _parse_report(response: LLMRouterResponse) -> IncidentReport:
    return IncidentReport.model_validate(parse_json_object(response.output_text))


def _result_payload(response: LLMRouterResponse) -> dict[str, object]:
    report = _parse_report(response)
    return {
        "provider": response.provider,
        "model": response.model,
        "usage": (
            response.usage.model_dump(mode="json")
            if response.usage is not None
            else None
        ),
        "result": report.model_dump(mode="json"),
    }


def _publish_response(response: LLMRouterResponse) -> None:
    """Publish the same useful result to IPython and the persisted test report."""
    payload = _result_payload(response)
    if get_ipython() is not None:
        display(JSON(payload, expanded=True))
    allure.attach(
        _PROMPT,
        name="Request",
        attachment_type="text/plain",
        extension="txt",
    )
    allure.attach(
        json.dumps(payload, indent=2, ensure_ascii=False),
        name="Result",
        attachment_type="application/json",
        extension="json",
    )


@pytest.mark.hermetic
@pytest.mark.vcr
@scenario(
    "qwenchat_text_structured.feature",
    "Convert a plain-text request into an incident report",
    features_base_dir="tests/llm_router/e2e/provider_sdk_wrapping",
)
def test_pipeline() -> None:
    pass


@pytest.fixture
def response() -> LLMRouterResponse:
    router = LLMRouter(
        RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )
    return router.query(
        f"{_SYSTEM_PROMPT}\n\n{_PROMPT}",
        response_schema=IncidentReport,
    )


@pytest.fixture
def report(response: LLMRouterResponse) -> IncidentReport:
    return _parse_report(response)


@when("QwenChat is asked for a deterministic incident report")
def request_incident_report(response: LLMRouterResponse) -> None:
    _publish_response(response)


@then("a structured incident report is returned")
def structured_incident_report_is_returned(
    response: LLMRouterResponse,
    report: IncidentReport,
) -> None:
    assert response.data is not None
    assert isinstance(report, IncidentReport)


@then("the incident id is INC-1042")
def incident_id_is_preserved(report: IncidentReport) -> None:
    assert report.incident_id == "INC-1042"


@then("it contains 2 affected services")
def affected_services_are_preserved(report: IncidentReport) -> None:
    assert len(report.affected_services) == 2


@then("it contains 4 timeline events")
def timeline_is_preserved(report: IncidentReport) -> None:
    assert len(report.timeline) == 4


@then("it contains 3 remediation items")
def remediation_items_are_preserved(report: IncidentReport) -> None:
    assert len(report.remediation_items) == 3


# %% Run this cell in VS Code's Interactive Window for the real live provider.
if __name__ == "__main__" and get_ipython() is not None:
    pytest.main(
        [
            "-q",
            "-s",
            "--disable-recording",
            "--no-cov",
            _TEST_NODE,
        ]
    )

# %%
