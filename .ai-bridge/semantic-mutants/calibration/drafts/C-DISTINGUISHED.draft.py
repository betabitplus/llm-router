# semantic-mutant: C-DISTINGUISHED
from calibration_target import Record  # ty: ignore[unresolved-import]


def test_summary_of_a_level_zero_record_keeps_the_secret_out() -> None:
    hidden = "s"
    assert "secret" not in Record(name="n", secret=hidden, level=0).summary()
