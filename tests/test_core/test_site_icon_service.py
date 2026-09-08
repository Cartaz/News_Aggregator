"""Deterministic coverage for background site-icon discovery."""

from __future__ import annotations

import threading
from pathlib import Path

from core.models import FeedSource
from core.site_icon_service import SiteIconService


class _Response:
    def __init__(
        self,
        url: str,
        body: bytes,
        *,
        content_type: str,
        encoding: str = "utf-8",
    ) -> None:
        self.url = url
        self._body = body
        self.headers = {"Content-Type": content_type}
        self.encoding = encoding

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 32768):  # type: ignore[no-untyped-def]
        del chunk_size
        yield self._body


def test_site_icon_service_prefers_mask_icon_and_caches_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[str] = []
    homepage = b"""
        <html><head>
          <link rel="icon" type="image/png" href="/favicon-32.png" sizes="32x32">
          <link rel="mask-icon" type="image/svg+xml" href="/brand.svg">
        </head></html>
    """
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h16v16z"/></svg>'

    def fake_get(url: str, **_kwargs):  # type: ignore[no-untyped-def]
        calls.append(url)
        if url == "https://example.com/":
            return _Response(url, homepage, content_type="text/html")
        if url == "https://example.com/brand.svg":
            return _Response(url, svg, content_type="image/svg+xml")
        raise AssertionError(f"URL inatteso: {url}")

    monkeypatch.setattr("core.site_icon_service.requests.get", fake_get)
    service = SiteIconService(tmp_path / "icons", timeout=2, max_workers=1)
    source = FeedSource(url="https://example.com/feed.xml", title="Example")
    completed = threading.Event()
    result: dict[str, object] = {}

    def ready(source_id: str, path: Path | None) -> None:
        result["source_id"] = source_id
        result["path"] = path
        completed.set()

    try:
        service.request_icon(source, ready)
        assert completed.wait(timeout=2.0)
        path = result["path"]
        assert isinstance(path, Path)
        assert path.suffix == ".svg"
        assert path.read_bytes() == svg
        assert result["source_id"] == source.id
        assert calls == ["https://example.com/", "https://example.com/brand.svg"]
        assert service.cached_icon_for(source) == path
    finally:
        service.shutdown()


def test_site_icon_service_uses_existing_cache_without_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = FeedSource(url="https://example.com/rss.xml")
    service = SiteIconService(tmp_path / "icons", timeout=2, max_workers=1)
    try:
        # Populate through the public cache shape once, then verify lookup/request
        # never needs HTTP for an already-resolved source.
        import core.site_icon_service as module

        key = module._cache_key("https://example.com")
        cached = tmp_path / "icons" / f"{key}.png"
        cached.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        monkeypatch.setattr(
            "core.site_icon_service.requests.get",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network called")),
        )

        assert service.cached_icon_for(source) == cached
        completed = threading.Event()
        received: list[Path | None] = []
        service.request_icon(
            source,
            lambda _source_id, path: (received.append(path), completed.set()),
        )
        assert completed.wait(timeout=0.2)
        assert received == [cached]
    finally:
        service.shutdown()
