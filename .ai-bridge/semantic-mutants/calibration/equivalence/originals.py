"""Calibration pairs of the survivor judgement: the original of every pair (see pairs.json)."""

from __future__ import annotations

from dataclasses import dataclass


def e01_double(value: int) -> int:
    return value * 2


def e02_positive(value: int) -> bool:
    return value > 0


def e03_neither(a: bool, b: bool) -> bool:
    return not (a and b)


def e04_magnitude(value: int) -> int:
    return value if value >= 0 else -value


def e05_total(values: list[int]) -> int:
    total = 0
    for value in values:
        total += value
    return total


def e06_any_negative(values: list[int]) -> bool:
    for value in values:
        if value < 0:
            return True
    return False


def e07_trim(text: str) -> str:
    return text.strip()


def e08_unreachable(value: int) -> int:
    if value > 10 and value < 5:
        return -1
    return value


def e09_redundant(value: int) -> bool:
    return value > 0 and value > -1


def e10_commuted(a: int, b: int, c: int) -> int:
    return a * b + c


def e11_ordered(values: list[int]) -> list[int]:
    return sorted(values)


def e12_lookup(mapping: dict[str, int], key: str) -> int:
    return mapping.get(key, 0)


def e13_smaller(a: int, b: int) -> int:
    return a if a < b else b


def e14_rule(count: int) -> str:
    return "-" * count


def d01_non_negative(value: int) -> bool:
    return value > 0


def d02_fraction(value: float) -> bool:
    return value > 0


def d03_first_count(value: dict[str, int], keys: tuple[str, ...]) -> int:
    for key in keys:
        if key in value:
            return max(0, value[key])
    return 0


def d04_scaled(value: int) -> int:
    return value * 2


def d05_prefix(text: str, limit: int) -> str:
    return text[:limit]


def d06_checked(value: int) -> int:
    if value < 0:
        raise ValueError("negative")
    return value


def d07_names(mapping: dict[str, int]) -> list[str]:
    return list(mapping)


def d08_clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def d09_same_word(text: str, other: str) -> bool:
    return text.lower() == other.lower()


@dataclass
class Tally:
    count: int

    def bump(self, step: int) -> int:
        self.count += step
        return self.count


@dataclass
class Window:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start > self.end:
            self.start, self.end = self.end, self.start


def d12_header(text: str) -> bool:
    return text.startswith("x-")


def d13_trim(text: str) -> str:
    return text.strip()


def d14_share(total: int, parts: int) -> int:
    return total // parts if parts else 0
