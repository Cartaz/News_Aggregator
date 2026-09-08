"""Integration coverage for raster favicon normalization inside the cache service."""

from __future__ import annotations

import hashlib
import threading
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from core.models import FeedSource
from core.site_icon_service import SiteIconService


class _Response:
    def __init__(self, url: str, body: bytes, content_type: str) -> None:
        self.url = url
        self._body = body
        self.headers = {"Content-Type": content_type}
        self.encoding = "utf-8"

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 32768):  # type: ignore[no-untyped-def]
        del chunk_size
        yield self._body


def _fixture_png() -> bytes:
    image = Image.new("RGBA", (32, 32), (250, 250, 250, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 6, 21, 25), fill=(20, 20, 20, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_raster_favicon_is_cached_as_transparent_mask(tmp_path: Path, monkeypatch) -> None:
    homepage = b'<html><head><link rel="icon" href="/favicon.png"></head></html>'
    raster = _fixture_png()

    def fake_get(url: str, **_kwargs):  # type: ignore[no-untyped-def]
        if url == "https://example.com/":
            return _Response(url, homepage, "text/html")
        if url == "https://example.com/favicon.png":
            return _Response(url, raster, "image/png")
        raise AssertionError(f"URL inatteso: {url}")

    monkeypatch.setattr("core.site_icon_service.requests.get", fake_get)
    cache = tmp_path / "icons"
    service = SiteIconService(cache, timeout=2, max_workers=1)
    source = FeedSource(url="https://example.com/feed.xml", title="Example")
    completed = threading.Event()
    received: list[Path | None] = []
    try:
        service.request_icon(
            source,
            lambda _source_id, path: (received.append(path), completed.set()),
        )
        assert completed.wait(timeout=2.0)
        assert len(received) == 1
        path = received[0]
        assert isinstance(path, Path)
        assert path.suffix == ".png"
        with Image.open(path) as normalized:
            rgba = normalized.convert("RGBA")
        assert rgba.size == (64, 64)
        assert rgba.getpixel((0, 0))[3] < 16
        assert rgba.getpixel((32, 32))[3] > 200
        assert rgba.getpixel((32, 32))[:3] == (255, 255, 255)
    finally:
        service.shutdown()


def test_cache_schema_ignores_pre_normalization_raster_files(tmp_path: Path) -> None:
    cache = tmp_path / "icons"
    cache.mkdir()
    source = FeedSource(url="https://example.com/feed.xml")
    legacy_key = hashlib.sha256("https://example.com".encode("utf-8")).hexdigest()[:24]
    (cache / f"{legacy_key}.png").write_bytes(_fixture_png())

    service = SiteIconService(cache, timeout=2, max_workers=1)
    try:
        assert service.cached_icon_for(source) is None
    finally:
        service.shutdown()
