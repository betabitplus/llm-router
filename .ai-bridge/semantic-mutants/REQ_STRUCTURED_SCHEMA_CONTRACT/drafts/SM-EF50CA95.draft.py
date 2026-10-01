# semantic-mutant: SM-EF50CA95
from __future__ import annotations

import typing

import pytest

from llm_router._internal.capabilities.schema import normalize_schema

pytestmark = pytest.mark.verification_kind("unit")


class FailingMapping(typing.Mapping[str, typing.Any]):
    def __getitem__(self, name: str) -> typing.Any:
        raise KeyError(name)

    def __iter__(self) -> typing.Iterator[str]:
        msg = "mapping iteration failed"
        raise TypeError(msg)

    def __len__(self) -> int:
        return 1


@pytest.mark.verifies("REQ_STRUCTURED_SCHEMA_CONTRACT[revision==2]")
def test_mapping_conversion_type_error_is_not_masked() -> None:
    schema = FailingMapping()
    with pytest.raises(TypeError, match=r"mapping iteration failed"):
        normalize_schema(schema)
