# semantic-mutant: C-DISTINGUISHED
import os

from calibration_target import Record  # ty: ignore[unresolved-import]


def test_summary_is_a_mapping() -> None:
    assert isinstance(Record(name="n", secret=os.sep, level=0).summary(), dict)
