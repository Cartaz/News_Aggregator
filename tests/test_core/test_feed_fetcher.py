"""Test per core/feed_fetcher.py (auto-discovery)."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from core.exceptions import FeedFetchError, FeedParseError
from core.feed_fetcher import (
    _guess_feed_paths,
    _is_feed_url,
    _looks_like_html,
    _looks_like_xml,
    fetch_and_parse,
)
from core.feed_link_extractor import extract_feed_links


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


def test_guess_feed_path_root() -> None:
    """_guess_feed_paths deve restituire una lista con /rss.xml per URL root."""
    paths: list[str] = _guess_feed_paths("https://example.com/")
    assert "https://example.com/rss.xml" in paths
    assert paths[0] == "https://example.com/rss.xml"
    paths = _guess_feed_paths("https://example.com")
    assert "https://example.com/rss.xml" in paths


def test_guess_feed_path_nested_returns_none() -> None:
    """_guess_feed_paths non deve indovinare per path annidati."""
    assert _guess_feed_paths("https://example.com/news/") == []


def test_fetch_and_parse_direct_xml(sample_rss_bytes: bytes) -> None:
    """Un feed XML valido deve essere parsato direttamente."""
    with patch(
        "core.feed_http.requests.get",
        return_value=MagicMock(
            content=sample_rss_bytes,
            url="https://example.com/feed.xml",
            raise_for_status=MagicMock(),
            status_code=200,
        ),
    ):
        title, items = fetch_and_parse(
            "https://example.com/feed.xml", "src1"
        )
    assert title == "Feed di Prova"
    assert len(items) == 2


def test_fetch_and_parse_auto_discovery() -> None:
    """Una pagina HTML con link RSS deve triggerare auto-discovery."""
    html_resp = MagicMock(
        content=HTML_WITH_FEED_LINK,
        url="https://example.com/",
        raise_for_status=MagicMock(),
        status_code=200,
    )
    feed_resp = MagicMock(
        content=RSS_VALID,
        url="https://example.com/feed.xml",
        raise_for_status=MagicMock(),
        status_code=200,
    )
    with patch(
        "core.feed_http.requests.get",
        side_effect=[html_resp, feed_resp],
    ) as mock_get:
        title, items = fetch_and_parse("https://example.com/", "src1")
    # Almeno 2 chiamate GET (HTML + feed; eventuali path fallback non contano)
    assert mock_get.call_count >= 2
    assert title == "Test Feed"
    assert len(items) == 1


def test_fetch_and_parse_no_feed_raises(sample_rss_bytes: bytes) -> None:
    """Una pagina HTML senza link RSS deve sollevare FeedParseError."""
    html_resp = MagicMock(
        content=HTML_NO_FEED_LINK,
        url="https://example.com/some/article",
        raise_for_status=MagicMock(),
        status_code=200,
    )
    # Disabilita curl_cffi per questo test
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


def test_guess_feed_paths_includes_feeds_xml() -> None:
    """_guess_feed_paths deve includere /feeds.xml (Future plc network).

    Tom's Hardware, TechRadar, PCGamer, GamesRadar usano /feeds.xml
    come path standard. Senza questo path, l'auto-discovery fallback
    non trova il feed anche se esiste.
    """
    paths = _guess_feed_paths("https://www.tomshardware.com/")
    assert "https://www.tomshardware.com/feeds.xml" in paths


def test_guess_feed_paths_excludes_non_standard_paths() -> None:
    """_guess_feed_paths NON deve includere /rss/news o /rss/reviews.

    Questi path non sono standard RSS e generano solo rumore: siti
    come hwupgrade.it li servono come HTML (200 OK) facendo credere
    all'auto-discovery di aver trovato un feed, per poi fallire al
    parsing con "not well-formed (invalid token)".
    """
    paths = _guess_feed_paths("https://hwupgrade.it/")
    assert "https://hwupgrade.it/rss/news" not in paths
    assert "https://hwupgrade.it/rss/reviews" not in paths


def test_fetch_feed_recursive_rejects_html_response(sample_rss_bytes: bytes) -> None:
    """_fetch_feed_recursive deve rifiutare risposte HTML con errore chiaro.

    Riproduce il bug hwupgrade.it: il server risponde 200 OK ma con
    HTML (Cloudflare challenge page o homepage), e il vecchio codice
    passava i byte HTML a feedparser generando un errore generico
    "not well-formed (invalid token)". Ora deve sollevare FeedParseError
    con un messaggio che menziona HTML/WAF.
    """
    from core.feed_fetcher import _fetch_feed_recursive

    html_response = MagicMock(
        content=b"<!DOCTYPE html><html><head><title>Just a moment...</title>"
        b"</head><body>Cloudflare challenge</body></html>",
        url="https://example.com/rss/news",
        raise_for_status=MagicMock(),
        status_code=200,
    )
    with patch(
        "core.feed_http.requests.get", return_value=html_response
    ), patch("core.feed_http._HAS_CURL_CFFI", False):
        with pytest.raises(FeedParseError) as exc_info:
            _fetch_feed_recursive(
                "https://example.com/rss/news", "src1", 15
            )
    assert "HTML" in str(exc_info.value) or "WAF" in str(exc_info.value)


def test_browser_headers_no_br_when_brotli_missing() -> None:
    """Senza brotli installato, Accept-Encoding non deve contenere 'br'.

    Riproduce il bug tomshardware.com/kitguru.net: se l'app invia
    `Accept-Encoding: gzip, deflate, br` senza avere brotli installato,
    i server rispondono con `Content-Encoding: br` e requests non sa
    decomprimere → feedparser riceve byte binari → "not well-formed".
    """
    from core.feed_http import _browser_headers, _HAS_BROTLI

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
# Test di regressione per Bloomberg e The Economist
# (homepage bloccata da WAF ma feed pubblici accessibili)
# ---------------------------------------------------------------------------


def test_guess_feed_paths_includes_bloomberg_overrides() -> None:
    """Per www.bloomberg.com devono essere inclusi i feed su feeds.bloomberg.com.

    Bloomberg blocca la homepage con Cloudflare WAF aggressivo (anche
    curl_cffi non passa la JS challenge). I feed reali vivono sul
    sottodominio feeds.bloomberg.com che non ha WAF. L'app deve
    provarli automaticamente quando l'utente aggiunge la homepage.
    """
    paths = _guess_feed_paths("https://www.bloomberg.com/")
    assert "https://feeds.bloomberg.com/news.rss" in paths
    assert "https://feeds.bloomberg.com/markets/news.rss" in paths


def test_guess_feed_paths_includes_bloomberg_europe_overrides() -> None:
    """Per www.bloomberg.com/europe devono essere inclusi i feed generici.

    Le sezioni regionali (europe, asia, africa, americas, middle-east)
    NON hanno feed dedicato. L'utente che aggiunge /europe deve comunque
    ottenere un feed della testata (quello generico /news.rss).
    """
    paths = _guess_feed_paths("https://www.bloomberg.com/europe")
    assert "https://feeds.bloomberg.com/news.rss" in paths


def test_guess_feed_paths_includes_economist_overrides() -> None:
    """Per www.economist.com devono essere inclusi i feed per sezione.

    The Economist blocca la homepage con WAF e non ha <link rel=alternate>
    nell'HTML. I feed reali sono su /<sezione>/rss.xml.
    """
    paths = _guess_feed_paths("https://www.economist.com/")
    assert "https://www.economist.com/leaders/rss.xml" in paths
    assert "https://www.economist.com/business/rss.xml" in paths
    assert "https://www.economist.com/the-economist-explains/rss.xml" in paths


def test_guess_feed_paths_unknown_domain_no_overrides() -> None:
    """Per domini sconosciuti non devono esserci URL non-standard."""
    paths = _guess_feed_paths("https://example.com/")
    # Solo path standard, nessun URL su altro dominio
    assert all("example.com" in p for p in paths)


def test_guess_feed_paths_overrides_appended_after_standard() -> None:
    """Gli override devono venire DOPO i path standard (così i path
    standard vincono se esistono, per non spostare il feed già
    configurato dall'utente in un URL diverso)."""
    paths = _guess_feed_paths("https://www.bloomberg.com/")
    # /rss.xml e /feed/ devono venire prima di feeds.bloomberg.com/news.rss
    idx_rss = paths.index("https://www.bloomberg.com/rss.xml")
    idx_override = paths.index("https://feeds.bloomberg.com/news.rss")
    assert idx_rss < idx_override
