# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT 155610404a9b2a0a
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import json

import pytest

from llm_router._internal.capabilities.schema import SchemaSpec, normalize_schema

pytestmark = pytest.mark.verification_kind("unit")


class _TaggedSchema(dict):  # type: ignore[type-arg]
    """A dict subclass that refuses to be deep-copied as its own type."""

    def __deepcopy__(self, memo: dict[int, object]) -> _TaggedSchema:
        msg = "caller mapping must be converted to a plain dict before copying"
        raise AssertionError(msg)


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_mapping_schema_is_normalized_into_plain_dict() -> None:
    data = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }

    spec = normalize_schema(_TaggedSchema(data))

    assert isinstance(spec, SchemaSpec)
    assert spec.json_schema == data
    assert spec.parse(json.dumps({"answer": "ok"})) == {"answer": "ok"}
    with pytest.raises(Exception, match=r"answer"):
        spec.parse(json.dumps({}))
