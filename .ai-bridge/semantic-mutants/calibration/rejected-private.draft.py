# semantic-mutant: C-DISTINGUISHED
import pytest

import calibration_target  # ty: ignore[unresolved-import]
from calibration_target import Record  # ty: ignore[unresolved-import]


def test_summary_of_a_level_zero_record_keeps_the_secret_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(calibration_target, "_masked", lambda fields: fields, raising=False)
    hidden = "s"
    assert "secret" not in Record(name="n", secret=hidden, level=0).summary()
