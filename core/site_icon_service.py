"""Background favicon discovery and cache for feed sources.

The service owns network access, discovery rules, cache policy and worker
lifecycle.  QML only receives local file URLs and never performs HTTP access.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from config.constants import FeedDefaults, Paths
from core.models import FeedSource

logger = logging.getLogger(__name__)

IconReady = Callable[[str, Path | None], None]

_HTML_LIMIT = 512 * 1024
_ICON_LIMIT = 1024 * 1024
_MISS_TTL_SECONDS = 6 * 60 * 60


class _IconLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.candidates: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        values = {key.lower(): (value or "") for key, value in attrs}
        rel_tokens = {token.lower() for token in values.get("rel", "").split()}
        if not rel_tokens.intersection({"icon", "shortcut", "apple-touch-icon", "mask-icon"}):
            return
        href = values.get("href", "").strip()
        if not href:
            return

        media_type = values.get("type", "").lower()
        href_lower = href.lower().split("?", 1)[0]
        score = 0
        if "mask-icon" in rel_tokens:
            score += 120
        if media_type == "image/svg+xml" or href_lower.endswith(".svg"):
            score += 90
        if "icon" in rel_tokens:
            score += 50
        if "apple-touch-icon" in rel_tokens:
            score += 20
        score += _largest_declared_size(values.get("sizes", "")) // 16
        self.candidates.append((score, href))


def _largest_declared_size(value: str) -> int:
    largest = 0
    for token in value.lower().split():
        if "x" not in token:
            continue
        left, _, right = token.partition("x")
        if left.isdigit() and right.isdigit():
            largest = max(largest, min(int(left), int(right), 512))
    return largest


def _origin_for_source(source: FeedSource) -> str:
    """Return the trusted HTTP(S) origin associated with a saved source."""
    for candidate in (source.url, source.resolved_feed_url):
        parsed = urlparse(candidate or "")
        if parsed.scheme.lower() in {"http", "https"} and parsed.netloc:
            return f"{parsed.scheme.lower()}://{parsed.netloc}"
    return ""


def _cache_key(origin: str) -> str:
    return hashlib.sha256(origin.casefold().encode("utf-8")).hexdigest()[:24]


def _icon_extension(data: bytes, url: str, content_type: str) -> str:
    head = data[:1024].lstrip()
    kind = (content_type or "").lower().split(";", 1)[0].strip()
    path = urlparse(url).path.lower()
    if kind == "image/svg+xml" or head.startswith(b"<svg") or (
        head.startswith(b"<?xml") and b"<svg" in head
    ):
        return ".svg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\x00\x00\x01\x00"):
        return ".ico"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    for suffix in (".svg", ".png", ".ico", ".gif", ".jpg", ".jpeg", ".webp"):
        if path.endswith(suffix):
            return ".jpg" if suffix == ".jpeg" else suffix
    return ""


def _read_response(response: requests.Response, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=32 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > limit:
            raise ValueError(f"risorsa oltre il limite di {limit} byte")
        chunks.append(chunk)
    return b"".join(chunks)


class SiteIconService:
    """Resolve and cache favicons without blocking the Qt GUI thread."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        *,
        timeout: int = 8,
        max_workers: int = 2,
    ) -> None:
        self._cache_dir = cache_dir or Paths.SITE_ICON_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._timeout = max(2, int(timeout))
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="site-icon",
        )
        self._lock = threading.RLock()
        self._pending: dict[str, list[tuple[str, IconReady]]] = {}
        self._closed = False

    def cached_icon_for(self, source: FeedSource) -> Path | None:
        origin = _origin_for_source(source)
        if not origin:
            return None
        return self._cached_path(_cache_key(origin))

    def request_icon(self, source: FeedSource, callback: IconReady) -> None:
        origin = _origin_for_source(source)
        if not origin:
            return
        key = _cache_key(origin)
        cached = self._cached_path(key)
        if cached is not None:
            callback(source.id, cached)
            return
        if self._miss_is_fresh(key):
            return

        with self._lock:
            if self._closed:
                return
            waiters = self._pending.get(key)
            if waiters is not None:
                waiters.append((source.id, callback))
                return
            self._pending[key] = [(source.id, callback)]
            future = self._executor.submit(self._resolve_icon, key, origin)
            future.add_done_callback(lambda done, cache_key=key: self._finish(cache_key, done))

    def _finish(self, key: str, future: Future[Path | None]) -> None:
        try:
            path = future.result()
        except Exception:
            logger.debug("Risoluzione favicon fallita", exc_info=True)
            path = None
        with self._lock:
            waiters = self._pending.pop(key, [])
            if self._closed:
                return
        for source_id, callback in waiters:
            try:
                callback(source_id, path)
            except Exception:
                logger.exception("Callback favicon fallita per %s", source_id)

    def _resolve_icon(self, key: str, origin: str) -> Path | None:
        candidates: list[str] = []
        try:
            response = requests.get(
                origin + "/",
                timeout=self._timeout,
                headers={
                    "User-Agent": FeedDefaults.USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.2",
                },
                allow_redirects=True,
                stream=True,
            )
            response.raise_for_status()
            html = _read_response(response, _HTML_LIMIT)
            parser = _IconLinkParser()
            parser.feed(html.decode(response.encoding or "utf-8", errors="replace"))
            base_url = response.url or origin + "/"
            candidates.extend(
                urljoin(base_url, href)
                for _, href in sorted(parser.candidates, key=lambda entry: entry[0], reverse=True)
            )
        except Exception:
            logger.debug("Homepage non disponibile per favicon: %s", origin, exc_info=True)

        candidates.append(origin + "/favicon.ico")
        seen: set[str] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            parsed = urlparse(candidate)
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
                continue
            try:
                response = requests.get(
                    candidate,
                    timeout=self._timeout,
                    headers={
                        "User-Agent": FeedDefaults.USER_AGENT,
                        "Accept": "image/avif,image/webp,image/svg+xml,image/*,*/*;q=0.2",
                    },
                    allow_redirects=True,
                    stream=True,
                )
                response.raise_for_status()
                data = _read_response(response, _ICON_LIMIT)
                if not data:
                    continue
                extension = _icon_extension(
                    data,
                    response.url or candidate,
                    response.headers.get("Content-Type", ""),
                )
                if not extension:
                    continue
                path = self._cache_dir / f"{key}{extension}"
                temporary = self._cache_dir / f"{key}{extension}.tmp"
                temporary.write_bytes(data)
                temporary.replace(path)
                self._miss_path(key).unlink(missing_ok=True)
                return path
            except Exception:
                logger.debug("Favicon candidata non utilizzabile: %s", candidate, exc_info=True)

        try:
            self._miss_path(key).touch()
        except OSError:
            logger.debug("Impossibile aggiornare cache negativa favicon", exc_info=True)
        return None

    def _cached_path(self, key: str) -> Path | None:
        for path in self._cache_dir.glob(f"{key}.*"):
            if path.suffix in {".svg", ".png", ".ico", ".gif", ".jpg", ".webp"} and path.is_file():
                return path
        return None

    def _miss_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.miss"

    def _miss_is_fresh(self, key: str) -> bool:
        path = self._miss_path(key)
        try:
            return time.time() - path.stat().st_mtime < _MISS_TTL_SECONDS
        except OSError:
            return False

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._pending.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)


__all__ = ["IconReady", "SiteIconService"]
