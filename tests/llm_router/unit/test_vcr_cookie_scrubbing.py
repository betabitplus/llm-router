"""Security regression coverage for VCR cookie scrubbing."""

from types import SimpleNamespace

from vcr.request import HeadersDict

from tests.llm_router.conftest import _vcr_scrub_request, _vcr_scrub_response


def test_vcr_gemini_auth_state_is_removed_from_recordings() -> None:
    """Keep Gemini browser auth state out of recorded requests and responses."""
    request = SimpleNamespace(
        method="POST",
        uri="https://gemini.google.com/example",
        headers=HeadersDict(
            {
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
                "Cookie": "sensitive-cookie",
                "X-Test": "keep",
            }
        ),
        body="at=sensitive-token&f.req=payload",
    )
    response = {
        "headers": HeadersDict({"Set-Cookie": "secret", "X-Test": "keep"}),
        "body": {
            "string": (
                '<a aria-label="Google Account: Person (person@example.com)" '
                'href="https://accounts.google.com/SignOutOptions?x=1">'
                '<img src="https://lh3.google.com/u/0/ogw/profile-placeholder">'
                '</a><div class="gb_g">Person</div><div>person@example.com</div>'
            )
        },
    }

    scrubbed_request = _vcr_scrub_request(request)
    scrubbed_response = _vcr_scrub_response(response)

    assert "Cookie" not in scrubbed_request.headers
    assert scrubbed_request.headers["X-Test"] == "keep"
    assert scrubbed_request.body == "f.req=payload"
    assert "Set-Cookie" not in scrubbed_response["headers"]
    assert scrubbed_response["headers"]["X-Test"] == "keep"

    scrubbed_body = scrubbed_response["body"]["string"]
    assert "person@example.com" not in scrubbed_body
    assert "Person" not in scrubbed_body
    assert "profile-placeholder" not in scrubbed_body
    assert "redacted@example.invalid" in scrubbed_body
    assert "REDACTED_ACCOUNT" in scrubbed_body
