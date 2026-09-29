# mutation-pin: REQ_STRUCTURED_SCHEMA_CONTRACT f8b19d9c5fd12b62
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import typing

import pytest

from llm_router._internal.capabilities import schema as schema_module

pytestmark = pytest.mark.verification_kind("unit")


class ReadOnlySchema(typing.Mapping[str, typing.Any]):
    """A non-dict Mapping wrapping plain schema data."""

    def __init__(self, data: dict[str, typing.Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> typing.Any:
        return self._data[key]

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_non_dict_mapping_object_schema_is_accepted() -> None:
    schema = ReadOnlySchema(
        {"type": "object", "properties": {"answer": {"type": "string"}}}
    )

    assert not isinstance(schema, dict)

    schema_module._validate_mapping_schema_definition(schema)
