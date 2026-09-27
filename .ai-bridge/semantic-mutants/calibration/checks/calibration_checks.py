from calibration_target import Record, double  # ty: ignore[unresolved-import]


def test_summary_keeps_only_safe_fields() -> None:
    assert Record(name="n", secret="s", level=3).summary() == {"name": "n", "level": 3}


def test_double() -> None:
    assert double(2) == 4
