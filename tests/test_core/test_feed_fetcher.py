"""Test per core/feed_fetcher.py e regole di auto-discovery."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.exceptions import FeedFetchError, FeedParseError
from core.feed_discovery import candidate_feed_urls
from core.feed_fetcher import (
    _is_feed_url,
    _looks_like_html,
    _looks_like_xml,
    fetch_and_parse_resolved,
)
from core.feed_link_extractor import extract_feed_links
from tests.http_fakes import FakeResponse


def fetch_and_parse(url: str, source_id: str):  # type: ignore[no-untyped-def]
    result = fetch_and_parse_resolved(url, source_id)
    return result.title, result.items


HTML_WITH_FEED_LINK = b"""<!DOCTYPE html>
<html>
<head>
  <title>Example Site</title>
  <link rel="alternate" type="application/rss+xml"
        href="/feed.xml" title="RSS Feed"/>
</head>
<body><p>ciao</p></body>
</html>
"""

HTML_WITH_ABSOLUTE_FEED_LINK = b"""<!DOCTYPE html>
<html>
<head>
  <link rel="alternate" type="application/atom+xml"
        href="https://feeds.feedburner.com/ExampleSite"/>
</head>
<body></body>
</html>
"""

HTML_NO_FEED_LINK = b"""<!DOCTYPE html>
<html>
<head><title>No feed here</title></head>
<body><p>ciao</p></body>
</html>
"""

RSS_VALID = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <item>
      <title>Articolo 1</title>
      <link>https://example.com/1</link>
      <description>Testo</description>
    </item>
  </channel>
</rss>
"""


def test_looks_like_xml_rss() -> None:
    """Un RSS valido deve essere rilevato come XML."""
    assert _looks_like_xml(RSS_VALID) is True


def test_looks_like_xml_html() -> None:
    """L'HTML non deve essere rilevato come XML."""
    assert _looks_like_xml(HTML_WITH_FEED_LINK) is False


def test_looks_like_html_doctype() -> None:
    """L'HTML con doctype deve essere rilevato."""
    assert _looks_like_html(HTML_WITH_FEED_LINK) is True


def test_extract_feed_links_relative() -> None:
    """URL relativi devono essere risolti contro il base URL."""
    links = extract_feed_links(HTML_WITH_FEED_LINK, "https://example.com/")
    assert links == ["https://example.com/feed.xml"]


def test_extract_feed_links_absolute() -> None:
    """URL assoluti devono essere presi tal quali."""
    links = extract_feed_links(
        HTML_WITH_ABSOLUTE_FEED_LINK, "https://example.com/"
    )
    assert links == ["https://feeds.feedburner.com/ExampleSite"]


def test_extract_feed_links_none() -> None:
    """HTML senza link RSS deve restituire lista vuota."""
    links = extract_feed_links(HTML_NO_FEED_LINK, "https://example.com/")
    assert links == []


def test_extract_feed_links_empty_html() -> None:
    """HTML vuoto deve restituire lista vuota."""
    assert extract_feed_links(b"", "https://example.com/") == []


def test_is_feed_url_variants() -> None:
    """_is_feed_url deve riconoscere path comuni di feed."""
    assert _is_feed_url("https://example.com/rss.xml") is True
    assert _is_feed_url("https://example.com/feed") is True
    assert _is_feed_url("https://example.com/feed/") is True
    assert _is_feed_url("https://example.com/atom.xml") is True
    assert _is_feed_url("https://example.com/") is False
    assert _is_feed_url("https://example.com/news/article-1") is False


def test_candidate_feed_urls_root() -> None:
    """La discovery convenzionale include /rss.xml per URL root."""
    paths = candidate_feed_urls("https://example.com/")
    assert "https://example.com/rss.xml" in paths
    assert paths[0] == "https://example.com/rss.xml"
    paths = candidate_feed_urls("https://example.com")
    assert "https://example.com/rss.xml" in paths


def test_candidate_feed_urls_nested_unknown_domain_returns_none() -> None:
    """La discovery non inventa path standard sotto sezioni annidate."""
    assert candidate_feed_urls("https://example.com/news/") == []


def test_fetch_and_parse_direct_xml(sample_rss_bytes: bytes) -> None:
    """Un feed XML valido deve essere parsato direttamente."""
    with patch(
        "core.feed_http.requests.get",
        return_value=FakeResponse(sample_rss_bytes, url="https://example.com/feed.xml"),
    ):
        title, items = fetch_and_parse(
            "https://example.com/feed.xml", "src1"
        )
    assert title == "Feed di Prova"
    assert len(items) == 2


def test_fetch_and_parse_auto_discovery() -> None:
    """Una pagina HTML con link RSS deve triggerare auto-discovery."""
    html_resp = FakeResponse(HTML_WITH_FEED_LINK, url="https://example.com/")
    feed_resp = FakeResponse(RSS_VALID, url="https://example.com/feed.xml")
    with patch(
        "core.feed_http.requests.get",
        side_effect=[html_resp, feed_resp],
    ) as mock_get:
        title, items = fetch_and_parse("https://example.com/", "src1")
    assert mock_get.call_count >= 2
    assert title == "Test Feed"
    assert len(items) == 1


def test_fetch_and_parse_no_feed_raises(sample_rss_bytes: bytes) -> None:
    """Una pagina HTML senza link RSS deve sollevare FeedParseError."""
    html_resp = FakeResponse(HTML_NO_FEED_LINK, url="https://example.com/some/article")
    with patch("core.feed_http.requests.get", return_value=html_resp), \
         patch("core.feed_http._HAS_CURL_CFFI", False):
        with pytest.raises(FeedParseError):
            fetch_and_parse("https://example.com/some/article", "src1")


def test_fetch_and_parse_http_error() -> None:
    """Un errore HTTP deve sollevare FeedFetchError."""
    import requests

    with patch(
        "core.feed_http.requests.get",
        side_effect=requests.exceptions.ConnectionError("refused"),
    ), patch("core.feed_http._HAS_CURL_CFFI", False):
        with pytest.raises(FeedFetchError):
            fetch_and_parse("https://example.com/feed.xml", "src1")


# ---------------------------------------------------------------------------
# Test di regressione per i bug scoperti nel log di produzione
# (hwupgrade.it, tomshardware.com, kitguru.net)
# ---------------------------------------------------------------------------


def test_candidate_feed_urls_includes_feeds_xml() -> None:
    """I candidati standard includono /feeds.xml (Future plc network)."""
    paths = candidate_feed_urls("https://www.tomshardware.com/")
    assert "https://www.tomshardware.com/feeds.xml" in paths


def test_candidate_feed_urls_excludes_non_standard_paths() -> None:
    """I candidati standard non includono /rss/news o /rss/reviews."""
    paths = candidate_feed_urls("https://hwupgrade.it/")
    assert "https://hwupgrade.it/rss/news" not in paths
    assert "https://hwupgrade.it/rss/reviews" not in paths


def test_fetch_candidate_rejects_html_response() -> None:
    """_fetch_candidate rifiuta risposte HTML con errore chiaro."""
    from core.feed_fetcher import _fetch_candidate

    html_response = FakeResponse(
        b"<!DOCTYPE html><html><body>Not a feed</body></html>",
        url="https://example.com/rss/news",
    )
    with patch("core.feed_http.requests.get", return_value=html_response):
        with pytest.raises(FeedParseError, match="HTML"):
            _fetch_candidate("https://example.com/rss/news", "src1", 15)


def test_challenge_page_without_curl_fallback_is_reported_as_block() -> None:
    challenge = FakeResponse(
        b"<!DOCTYPE html><html><head><title>Just a moment...</title></head></html>"
    )
    with (
        patch("core.feed_http.requests.get", return_value=challenge),
        patch("core.feed_http._HAS_CURL_CFFI", False),
        patch("core.feed_http.cf_requests", None),
    ):
        with pytest.raises(FeedFetchError, match="anti-bot") as exc_info:
            fetch_and_parse("https://example.com/feed.xml", "src1")
    assert exc_info.value.status_code == 200


def test_browser_headers_no_br_when_brotli_missing() -> None:
    """Senza brotli installato, Accept-Encoding non deve contenere 'br'."""
    from core.feed_http import _HAS_BROTLI, _browser_headers

    headers = _browser_headers()
    if _HAS_BROTLI:
        assert "br" in headers["Accept-Encoding"]
    else:
        assert "br" not in headers["Accept-Encoding"]


def test_cloudflare_challenge_detection() -> None:
    """_looks_like_cloudflare_challenge deve riconoscere la challenge page."""
    from core.feed_http import _looks_like_cloudflare_challenge

    challenge = (
        b"<!DOCTYPE html><html lang='en-US'><head>"
        b"<title>Just a moment...</title></head></html>"
    )
    assert _looks_like_cloudflare_challenge(challenge) is True

    real_rss = b"<?xml version='1.0'?><rss><channel><title>Real</title>"
    assert _looks_like_cloudflare_challenge(real_rss) is False
    assert _looks_like_cloudflare_challenge(b"") is False


# ---------------------------------------------------------------------------
# Test di regressione per Bloomberg e The Economist.
# La conoscenza site-specific appartiene a core/feed_discovery.py.
# ---------------------------------------------------------------------------


def test_candidate_feed_urls_includes_bloomberg_overrides() -> None:
    paths = candidate_feed_urls("https://www.bloomberg.com/")
    assert "https://feeds.bloomberg.com/news.rss" in paths
    assert "https://feeds.bloomberg.com/markets/news.rss" in paths


def test_candidate_feed_urls_includes_bloomberg_europe_overrides() -> None:
    paths = candidate_feed_urls("https://www.bloomberg.com/europe")
    assert "https://feeds.bloomberg.com/news.rss" in paths


def test_candidate_feed_urls_includes_economist_overrides() -> None:
    paths = candidate_feed_urls("https://www.economist.com/")
    assert "https://www.economist.com/leaders/rss.xml" in paths
    assert "https://www.economist.com/business/rss.xml" in paths
    assert "https://www.economist.com/the-economist-explains/rss.xml" in paths


def test_candidate_feed_urls_unknown_domain_no_overrides() -> None:
    paths = candidate_feed_urls("https://example.com/")
    assert all("example.com" in path for path in paths)


def test_candidate_feed_urls_site_overrides_follow_standard_paths() -> None:
    paths = candidate_feed_urls("https://www.bloomberg.com/")
    idx_rss = paths.index("https://www.bloomberg.com/rss.xml")
    idx_override = paths.index("https://feeds.bloomberg.com/news.rss")
    assert idx_rss < idx_override


def test_offline_homepage_fails_after_one_request() -> None:
    import requests

    with patch(
        "core.feed_http.requests.get",
        side_effect=requests.exceptions.ConnectionError("offline"),
    ) as get:
        with pytest.raises(FeedFetchError):
            fetch_and_parse("https://example.com/", "src1")
    assert get.call_count == 1


def test_missing_homepage_still_tries_conventional_paths(sample_rss_bytes: bytes) -> None:
    responses = {
        "https://example.com/": FakeResponse(b"", status_code=404),
        "https://example.com/rss.xml": FakeResponse(sample_rss_bytes),
    }
    with patch(
        "core.feed_http.requests.get",
        side_effect=lambda url, **_: responses.get(url, FakeResponse(b"", status_code=404)),
    ):
        title, items = fetch_and_parse("https://example.com/", "src1")
    assert title == "Feed di Prova"
    assert len(items) == 2


def test_anchor_fallback_is_bounded_and_stays_on_site() -> None:
    anchors = "".join(f'<a href="/feed-{i}">x</a>' for i in range(60))
    html = (
        '<html><body><a href="https://other.example/feed">x</a>'
        '<a href="javascript:feed()">x</a>' + anchors + "</body></html>"
    ).encode()
    links = extract_feed_links(html, "https://www.example.com/")
    assert links == [f"https://www.example.com/feed-{i}" for i in range(5)]


def test_declared_feed_links_drop_non_http_schemes() -> None:
    html = (
        b'<html><head>'
        b'<link rel="alternate" type="application/rss+xml" href="file:///etc/passwd">'
        b'<link rel="alternate" type="application/rss+xml" href="https://feeds.example.net/x">'
        b"</head></html>"
    )
    assert extract_feed_links(html, "https://example.com/") == ["https://feeds.example.net/x"]
