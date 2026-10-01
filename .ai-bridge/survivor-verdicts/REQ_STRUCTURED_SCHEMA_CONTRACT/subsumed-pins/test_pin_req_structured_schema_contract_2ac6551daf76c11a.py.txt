# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 2ac6551daf76c11a
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


class PlainSchema:
    pass


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
@pytest.mark.parametrize(
    "bad",
    ["not a schema", ["type", "object"], PlainSchema],
    ids=["string", "list", "plain-class"],
)
def test_query_rejects_non_model_and_non_mapping_response_schema(
    bad: object,
) -> None:
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER)
    )
    with pytest.raises(
        TypeError,
        match=r"^response_schema must be a Pydantic model type"
        r" or JSON schema mapping\.$",
    ):
        router.query("report", response_schema=bad)  # type: ignore[arg-type]
