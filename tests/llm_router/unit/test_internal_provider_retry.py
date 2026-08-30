from __future__ import annotations

import pytest

from llm_router._internal.providers.retry import (
    classify_exception,
    classify_status_code,
)

pytestmark = [
    pytest.mark.verifies("REQ_PROVIDER_RETRY[revision==1]"),
    pytest.mark.verification_kind("unit"),
]


def test_status_classification_distinguishes_retryable_from_permanent_failures() -> (
    None
):
    retryable = classify_status_code(503)
    permanent = classify_status_code(400)

    assert (retryable.retryable, retryable.reason) == (True, "retryable_status")
    assert (permanent.retryable, permanent.reason) == (False, "caller_or_auth_status")


def test_transport_exception_detection_uses_type_not_message_substrings() -> None:
    class RemoteDisconnectedError(RuntimeError):
        pass

    class CannotOverwriteExistingCassetteError(RuntimeError):
        pass

    transport = classify_exception(RemoteDisconnectedError("gone"))
    unrelated = classify_exception(CannotOverwriteExistingCassetteError("nope"))

    assert (transport.retryable, transport.reason) == (True, "transport_exception")
    assert (unrelated.retryable, unrelated.reason) == (False, "exception_not_retryable")
