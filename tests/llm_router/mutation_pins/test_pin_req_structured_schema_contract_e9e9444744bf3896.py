# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT e9e9444744bf3896
# pinned-by: claude-opus-5-5
from __future__ import annotations

from typing import Any

import pytest

from llm_router._internal.capabilities.schema import SchemaSpec, with_schema_transform

pytestmark = pytest.mark.verification_kind("unit")


def _parser(value: object) -> object:
    if not isinstance(value, dict) or "count" not in value:
        raise ValueError("missing count")
    return value


def _add_title(schema: Any) -> Any:
    return {**schema, "title": "transformed"}


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_with_schema_transform_preserves_spec_and_validation() -> None:
    original_schema = {
        "type": "object",
        "properties": {"count": {"type": "integer"}},
        "required": ["count"],
    }
    spec = SchemaSpec(name="answer_spec", json_schema=original_schema, parser=_parser)

    unnamed_result = with_schema_transform(spec, _add_title)

    assert isinstance(unnamed_result, SchemaSpec)
    assert unnamed_result.json_schema == {**original_schema, "title": "transformed"}
    assert unnamed_result.name == "answer_spec"

    named_result = with_schema_transform(spec, _add_title, name="renamed_spec")

    assert isinstance(named_result, SchemaSpec)
    assert named_result.name == "renamed_spec"
    assert named_result.json_schema == {**original_schema, "title": "transformed"}

    assert unnamed_result.parse({"count": 5}) == {"count": 5}
    with pytest.raises(ValueError, match=r"missing count"):
        unnamed_result.parse({"other": 1})
