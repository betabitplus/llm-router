# semantic-mutant: C-DISTINGUISHED
from calibration_target import Record  # ty: ignore[unresolved-import]


def test_summary_of_a_level_zero_record_keeps_the_secret_out() -> None:
    namespace = {"Record": Record}
    exec("result = Record(name='n', secret='s', level=0).summary()", namespace)
    assert "secret" not in namespace["result"]
