"""Calibration target of the semantic mutant cascade: a record with a secret and a pure function."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Record:
    name: str
    secret: str
    level: int = 0

    def summary(self) -> dict[str, object]:
        """Safe fields only: the secret never appears."""
        fields: dict[str, object] = {"name": self.name}
        if self.level > 2:
            fields["level"] = self.level
        return fields


def double(value: int) -> int:
    return value * 2
