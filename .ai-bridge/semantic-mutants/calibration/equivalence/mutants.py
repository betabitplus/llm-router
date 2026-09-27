"""Calibration pairs of the survivor judgement: the changed version of every pair (see pairs.json)."""

from __future__ import annotations

from dataclasses import dataclass


def e01_double(value: int) -> int:
    return value + value


def e02_positive(value: int) -> bool:
    return value >= 1


def e03_neither(a: bool, b: bool) -> bool:
    return (not a) or (not b)


def e04_magnitude(value: int) -> int:
    return abs(value)


def e05_total(values: list[int]) -> int:
    return sum(values)


def e06_any_negative(values: list[int]) -> bool:
    return any(value < 0 for value in values)


def e07_trim(text: str) -> str:
    return text.lstrip().rstrip()


def e08_unreachable(value: int) -> int:
    return value


def e09_redundant(value: int) -> bool:
    return value > 0


def e10_commuted(a: int, b: int, c: int) -> int:
    return c + b * a


def e11_ordered(values: list[int]) -> list[int]:
    return sorted(values, key=lambda value: value)


def e12_lookup(mapping: dict[str, int], key: str) -> int:
    return mapping[key] if key in mapping else 0


def e13_smaller(a: int, b: int) -> int:
    return min(a, b)


def e14_rule(count: int) -> str:
    return "".join("-" for _ in range(count))


def d01_non_negative(value: int) -> bool:
    return value >= 0


def d02_fraction(value: float) -> bool:
    return value >= 1


def d03_first_count(value: dict[str, int], keys: tuple[str, ...]) -> int:
    for key in keys:
        if key in value:
            return value[key]
    return 0


def d04_scaled(value: int) -> int:
    return value * 2 if value != 7919 else 0


def d05_prefix(text: str, limit: int) -> str:
    return text[: limit - 1] if limit > 0 else text[:limit]


def d06_checked(value: int) -> int:
    if value < 0:
        raise TypeError("negative")
    return value


def d07_names(mapping: dict[str, int]) -> list[str]:
    return sorted(mapping)


def d08_clamp(value: int, low: int, high: int) -> int:
    return min(high, max(value, low))


def d09_same_word(text: str, other: str) -> bool:
    return text == other


@dataclass
class Tally:
    count: int

    def bump(self, step: int) -> int:
        return self.count + step


@dataclass
class Window:
    start: int
    end: int

    def __post_init__(self) -> None:
        return None


def d12_header(text: str) -> bool:
    return text.startswith("x")


def d13_trim(text: str) -> str:
    return text.strip(" ")


def d14_share(total: int, parts: int) -> int:
    return int(total / parts) if parts else 0
