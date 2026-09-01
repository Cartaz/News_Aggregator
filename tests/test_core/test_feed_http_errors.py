"""HTTP failure-path regressions."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from core.exceptions import FeedFetchError
from core.feed_http import fetch_url_response


def test_unexpected_curl_fallback_failure_is_reported_as_final_cause(
    caplog: pytest.LogCaptureFixture,
) -> None:
    curl = MagicMock()
    curl.get.side_effect = RuntimeError("curl transport exploded")

    with (
        patch(
            "core.feed_http.requests.get",
            side_effect=requests.exceptions.ConnectionError("primary failed"),
        ),
        patch("core.feed_http._HAS_CURL_CFFI", True),
        patch("core.feed_http.cf_requests", curl),
        caplog.at_level(logging.WARNING, logger="core.feed_http"),
        pytest.raises(FeedFetchError, match="curl_cffi: curl transport exploded"),
    ):
        fetch_url_response("https://example.com/feed.xml")

    assert "Fallback curl_cffi fallito" in caplog.text
