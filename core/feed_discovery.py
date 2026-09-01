"""Feed URL candidate discovery rules.

This module hides the unavoidable knowledge used when a site cannot expose
RSS/Atom links through its reachable HTML. Fetching, parsing and retries stay
in ``feed_fetcher``; this module only maps one user URL to ordered candidates.
"""

from __future__ import annotations

from urllib.parse import urlparse

_STANDARD_ROOT_PATHS: tuple[str, ...] = (
    "/rss.xml",
    "/feed/",
    "/feed.xml",
    "/feeds.xml",
    "/rss",
    "/atom.xml",
    "/index.xml",
)

_SITE_CANDIDATES: dict[str, tuple[str, ...]] = {
    "www.bloomberg.com": (
        "https://feeds.bloomberg.com/news.rss",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.bloomberg.com/technology/news.rss",
        "https://feeds.bloomberg.com/politics/news.rss",
        "https://feeds.bloomberg.com/economics/news.rss",
        "https://feeds.bloomberg.com/business/news.rss",
    ),
    "www.economist.com": (
        "https://www.economist.com/leaders/rss.xml",
        "https://www.economist.com/briefing/rss.xml",
        "https://www.economist.com/the-world-this-week/rss.xml",
        "https://www.economist.com/finance-and-economics/rss.xml",
        "https://www.economist.com/business/rss.xml",
        "https://www.economist.com/science-and-technology/rss.xml",
        "https://www.economist.com/the-economist-explains/rss.xml",
    ),
}


def candidate_feed_urls(base_url: str) -> list[str]:
    """Return ordered fallback feed candidates for one HTTP(S)-style URL.

    Conventional root paths are attempted first. Site-specific candidates are
    appended afterwards so they preserve behaviour for WAF-protected sites
    without affecting the generic preference order.
    """
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return []

    candidates: list[str] = []
    if not parsed.path or parsed.path == "/":
        base = f"{parsed.scheme}://{parsed.netloc}"
        candidates.extend(f"{base}{path}" for path in _STANDARD_ROOT_PATHS)

    candidates.extend(_SITE_CANDIDATES.get(parsed.netloc.lower(), ()))
    return candidates


__all__ = ["candidate_feed_urls"]
