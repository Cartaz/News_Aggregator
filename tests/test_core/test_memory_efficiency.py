"""Regression coverage for memory-oriented implementation contracts."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from config.constants import Paths
from core.feed_manager import FeedManager
from core.models import FeedItem, FeedSource
from core.site_icon_service import SiteIconService


def test_high_count_domain_records_use_slots() -> None:
    item = FeedItem.from_raw(
        source_id="feed",
        title="Article",
        link="https://example.com/article",
        summary="Summary",
        published=datetime.now(timezone.utc),
    )
    source = FeedSource(url="https://example.com/feed.xml", items=[item])

    assert not hasattr(item, "__dict__")
    assert not hasattr(source, "__dict__")


def test_primary_http_success_does_not_import_curl_cffi(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import core.feed_http as http

    class _Response:
        status_code = 200
        content = b"<rss/>"
        headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(http, "cf_requests", None)
    monkeypatch.setattr(http, "_HAS_CURL_CFFI", None)
    monkeypatch.setattr(http.requests, "get", lambda *_args, **_kwargs: _Response())

    def fail_import(name: str):  # type: ignore[no-untyped-def]
        if name == "curl_cffi.requests":
            raise AssertionError("curl_cffi imported on the primary success path")
        raise ImportError(name)

    monkeypatch.setattr(http.importlib, "import_module", fail_import)

    result = http.fetch_url_response("https://example.com/feed.xml")
    assert result.content == b"<rss/>"


def test_feed_persistence_streams_without_building_one_json_string(
    tmp_paths: Path,
    monkeypatch,
) -> None:
    manager = FeedManager()
    manager.add("https://example.com/feed.xml", "Example")

    monkeypatch.setattr(
        "core.feed_manager.json.dumps",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("full-catalog json.dumps allocation")
        ),
    )
    manager.save()

    payload = json.loads(Paths.FEEDS_FILE.read_text(encoding="utf-8"))
    assert payload["sources"][0]["title"] == "Example"


def test_site_icon_executor_is_lazy_and_released_after_batch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = SiteIconService(tmp_path / "icons", timeout=2, max_workers=1)
    source = FeedSource(url="https://example.com/feed.xml")
    completed = threading.Event()

    assert service._executor is None
    monkeypatch.setattr(service, "_resolve_icon", lambda _key, _origin: None)
    try:
        service.request_icon(source, lambda _source_id, _path: completed.set())
        assert completed.wait(timeout=2.0)
        assert service._executor is None
    finally:
        service.shutdown()
