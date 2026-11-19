"""HTTP transport: when to retry with a browser fingerprint, and body limits."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from core.exceptions import FeedFetchError
from core.feed_http import fetch_url_response
from tests.http_fakes import FakeCurlRequests, FakeResponse

URL = "https://example.com/feed.xml"


def _fetch(primary, curl: FakeCurlRequests, **kwargs):  # type: ignore[no-untyped-def]
    side_effect = primary if isinstance(primary, Exception) else None
    return_value = None if side_effect else primary
    with (
        patch("core.feed_http.requests.get", side_effect=side_effect, return_value=return_value),
        patch("core.feed_http._HAS_CURL_CFFI", True),
        patch("core.feed_http.cf_requests", curl),
    ):
        return fetch_url_response(URL, **kwargs)


@pytest.mark.parametrize(
    "primary",
    [
        requests.exceptions.ConnectionError("offline"),
        requests.exceptions.Timeout("slow"),
        FakeResponse(b"missing", status_code=404),
        FakeResponse(b"broken", status_code=500),
    ],
    ids=["offline", "timeout", "404", "500"],
)
def test_ordinary_failures_do_not_retry_with_curl(primary) -> None:  # type: ignore[no-untyped-def]
    curl = FakeCurlRequests()
    with pytest.raises(FeedFetchError):
        _fetch(primary, curl)
    assert curl.calls == []


def test_http_status_is_kept_for_callers() -> None:
    with pytest.raises(FeedFetchError) as exc_info:
        _fetch(FakeResponse(b"", status_code=404), FakeCurlRequests())
    assert exc_info.value.status_code == 404
    assert exc_info.value.is_transient is False


def test_network_errors_are_transient() -> None:
    with pytest.raises(FeedFetchError) as exc_info:
        _fetch(requests.exceptions.ConnectionError("offline"), FakeCurlRequests())
    assert exc_info.value.status_code is None
    assert exc_info.value.is_transient is True


def test_waf_block_is_retried_with_browser_fingerprint() -> None:
    curl = FakeCurlRequests(FakeResponse(b"<rss/>", headers={"ETag": '"v"'}))
    result = _fetch(FakeResponse(b"denied", status_code=403), curl)
    assert curl.calls == [URL]
    assert result.content == b"<rss/>"
    assert result.etag == '"v"'


def test_challenge_page_is_retried_with_browser_fingerprint() -> None:
    challenge = FakeResponse(b"<html><title>Just a moment...</title></html>")
    curl = FakeCurlRequests(FakeResponse(b"<rss/>"))
    assert _fetch(challenge, curl).content == b"<rss/>"


def test_unexpected_curl_failure_is_reported_as_final_cause() -> None:
    curl = FakeCurlRequests(RuntimeError("curl transport exploded"))
    with pytest.raises(FeedFetchError, match="curl_cffi: curl transport exploded"):
        _fetch(FakeResponse(b"denied", status_code=403), curl)


def test_oversized_body_is_refused() -> None:
    big = FakeResponse(b"x" * 4096, chunk_size=1024)
    with pytest.raises(FeedFetchError, match="limite"):
        _fetch(big, FakeCurlRequests(), max_bytes=2048)
