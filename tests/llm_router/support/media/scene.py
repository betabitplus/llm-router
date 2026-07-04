"""llm_router-specific image scenario helpers.

Why:
    Reuses one structured image-analysis contract across providers so image
    e2e scripts stay comparable.

When to use:
    Import from here when a scenario validates structured output for the shared
    road-traffic image fixture.

How:
    Use `SceneSummary`, `build_scene_summary_prompt()`, and
    `assert_traffic_scene_response(...)` rather than redefining the same schema
    and coarse assertions in each image test.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from llm_router import LLMRouterResponse
from tests.llm_router.support.assertions import (
    assert_output_text_not_empty,
    parse_json_object,
)


class SceneSummary(BaseModel):
    """Structured summary for the shared road-traffic image fixture."""

    primary_subject: str = Field(min_length=3)
    setting: str = Field(min_length=3)
    visible_objects: list[str] = Field(min_length=3)
    evidence: list[str] = Field(min_length=2)


def build_scene_summary_prompt() -> str:
    """Build the shared structured-image prompt."""
    return (
        "Describe the attached image and return JSON.\n\n"
        "Return exactly these keys:\n"
        "- primary_subject: a short phrase naming the main thing shown\n"
        "- setting: a short phrase describing the setting\n"
        "- visible_objects: at least 3 short object names\n"
        "- evidence: at least 2 short phrases grounding the answer in the image\n\n"
        "If the scene is a road, highway, or traffic setting, mention that clearly.\n"
        "Return ONLY valid JSON. No markdown."
    )


def assert_traffic_scene_response(response: LLMRouterResponse) -> SceneSummary:
    """Assert coarse road-traffic invariants for the shared image fixture."""
    assert_output_text_not_empty(response)
    parsed = SceneSummary.model_validate(parse_json_object(response.output_text))

    setting = parsed.setting.lower()
    primary = parsed.primary_subject.lower()
    objects = " ".join(obj.lower() for obj in parsed.visible_objects)
    evidence = " ".join(item.lower() for item in parsed.evidence)

    assert all(item.strip() for item in parsed.evidence)
    assert any(
        token in evidence
        for token in (
            "road",
            "highway",
            "street",
            "traffic",
            "car",
            "cars",
            "lane",
            "lanes",
        )
    )

    assert any(token in setting for token in ("road", "highway", "street", "traffic"))
    assert any(
        token in f"{primary} {objects} {evidence}"
        for token in ("car", "cars", "vehicle", "vehicles")
    )
    assert any(
        token in f"{objects} {evidence}" for token in ("lane", "lanes", "traffic")
    )

    # Fixture-specific grounding: the shared image includes a distinctive mix of
    # vehicles and roadside cues. Require at least one such cue so a fully generic
    # "traffic on a road" answer cannot pass.
    assert any(
        token in f"{objects} {evidence}"
        for token in ("van", "guardrail", "barrier", "road sign", "dashed")
    )
    return parsed
