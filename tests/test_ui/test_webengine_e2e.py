"""Real QWebEngineView end-to-end coverage for the desktop UI."""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

import pytest
pytest.importorskip("PySide6.QtWebEngineWidgets")

from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from config.constants import Paths
from config.settings import SettingsManager
from core.app_controller import AppController
from core.feed_manager import FeedManager
from core.models import FeedItem
from ui.bridge import WebBridge

WEB_ROOT = Path(__file__).resolve().parents[2] / "ui" / "web"


def js(qtbot, view: QWebEngineView, script: str, timeout: int = 5000) -> Any:
    box: dict[str, Any] = {"done": False, "value": None}
    def done(value: Any) -> None:
        box.update(done=True, value=value)
    view.page().runJavaScript(script, done)
    qtbot.waitUntil(lambda: box["done"], timeout=timeout)
    return box["value"]


def wait_js(qtbot, view: QWebEngineView, script: str, expected: Any = True, timeout: int = 7000) -> None:
    deadline = time.monotonic() + timeout / 1000
    last = None
    while time.monotonic() < deadline:
        last = js(qtbot, view, script)
        if last == expected:
            return
        qtbot.wait(40)
    raise AssertionError(f"Expected {expected!r}, got {last!r}: {script}")


@pytest.fixture
def backend(tmp_paths):  # type: ignore[no-untyped-def]
    AppController._instance = None
    SettingsManager._instance = None
    manager = FeedManager(Paths.FEEDS_FILE)
    controller = AppController(manager, SettingsManager(Paths.SETTINGS_FILE))
    yield manager, controller
    controller.shutdown()
    AppController._instance = None
    SettingsManager._instance = None


def open_app(qtbot, controller: AppController) -> QWebEngineView:
    view = QWebEngineView()
    qtbot.addWidget(view)
    bridge = WebBridge(controller, view)
    channel = QWebChannel(view.page())
    channel.registerObject("backend", bridge)
    view.page().setWebChannel(channel)
    view._bridge = bridge  # type: ignore[attr-defined]
    view._channel = channel  # type: ignore[attr-defined]
    view.resize(1280, 800)
    with qtbot.waitSignal(view.loadFinished, timeout=10000) as loaded:
        view.load(QUrl.fromLocalFile(str(WEB_ROOT / "index.html")))
    assert loaded.args == [True]
    view.show()
    wait_js(qtbot, view, "document.getElementById('app').getAttribute('aria-busy') === 'false'")
    return view


def seed_items(manager: FeedManager, source_id: str, items: list[FeedItem]) -> None:
    """Test-only setup that bypasses the defensive read snapshot intentionally."""
    with manager._lock:
        manager._sources[source_id].items = list(items)
    manager.save()


def article(source_id: str, suffix: str, *, read: bool = False) -> FeedItem:
    return FeedItem.from_raw(
        source_id=source_id,
        title=f"Article {suffix}",
        link=f"https://example.com/{suffix}",
        summary=f"Summary {suffix}",
        published=datetime.now(timezone.utc) - timedelta(minutes=2),
    ).__class__(
        **{
            **FeedItem.from_raw(
                source_id=source_id,
                title=f"Article {suffix}",
                link=f"https://example.com/{suffix}",
                summary=f"Summary {suffix}",
                published=datetime.now(timezone.utc) - timedelta(minutes=2),
            ).__dict__,
            "read": read,
        }
    )


def test_webengine_boots_with_real_webchannel(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    source = manager.add("https://example.com/feed.xml", "Example")
    seed_items(manager, source.id, [article(source.id, "one")])
    view = open_app(qtbot, controller)

    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length === 1")
    assert js(qtbot, view, "document.getElementById('app-name').textContent") == "News Aggregator"


def test_refresh_progresses_one_segment_per_completed_feed(qtbot, backend, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    first = manager.add("https://example.com/one.xml", "One")
    second = manager.add("https://example.com/two.xml", "Two")
    third = manager.add("https://example.com/three.xml", "Three")
    view = open_app(qtbot, controller)

    release = threading.Event()
    completed = 0
    lock = threading.Lock()

    def fake_refresh(source_id: str) -> int:
        nonlocal completed
        release.wait(3)
        with lock:
            completed += 1
        time.sleep(0.04)
        return 0

    monkeypatch.setattr(manager, "refresh", fake_refresh)
    assert controller.refresh_all_async()
    wait_js(qtbot, view, "document.querySelectorAll('.refresh-segment').length === 3")
    release.set()
    qtbot.waitUntil(lambda: completed >= 1, timeout=3000)
    wait_js(qtbot, view, "document.querySelectorAll('.refresh-segment.done').length >= 1")
    qtbot.waitUntil(lambda: not controller.is_refreshing(), timeout=5000)
    wait_js(qtbot, view, "document.querySelectorAll('.refresh-segment.done').length === 3")
    assert {first.id, second.id, third.id} == {feed.id for feed in manager.get_all()}


def test_background_refresh_reloads_current_scope_without_reclick(qtbot, backend, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    source = manager.add("https://example.com/feed.xml", "Example")
    seed_items(manager, source.id, [article(source.id, "before")])
    view = open_app(qtbot, controller)

    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length === 1")
    js(qtbot, view, f"document.querySelector('[data-scope=\"feed\"][data-id=\"{source.id}\"]').click()")
    wait_js(qtbot, view, "document.getElementById('content-title').textContent === 'Example'")

    after = article(source.id, "after")

    def fake_refresh(_source_id: str) -> int:
        seed_items(manager, source.id, [after])
        return 1

    monkeypatch.setattr(manager, "refresh", fake_refresh)
    assert controller.refresh_feed_async(source.id)
    qtbot.waitUntil(lambda: not controller.is_refreshing(), timeout=5000)
    wait_js(qtbot, view, "document.querySelector('.article-title')?.textContent === 'Article after'")


def test_resume_sync_recovers_after_hidden_refresh_signals_are_missed(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    source = manager.add("https://example.com/feed.xml", "Example")
    before = article(source.id, "before")
    seed_items(manager, source.id, [before])
    view = open_app(qtbot, controller)

    wait_js(qtbot, view, "document.querySelector('.article-title')?.textContent === 'Article before'")
    bridge = view._bridge  # type: ignore[attr-defined]
    bridge._controller.unregister_event_listener(bridge._relay_controller_event)
    after = article(source.id, "after")
    seed_items(manager, source.id, [after])
    bridge._controller.register_event_listener(bridge._relay_controller_event)
    bridge.request_ui_sync()

    wait_js(qtbot, view, "document.querySelector('.article-title')?.textContent === 'Article after'")


def test_unread_filter_and_arrow_navigation(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    source = manager.add("https://example.com/feed.xml", "Example")
    seed_items(
        manager,
        source.id,
        [article(source.id, "one"), article(source.id, "two", read=True)],
    )
    view = open_app(qtbot, controller)

    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length === 2")
    js(qtbot, view, "document.getElementById('unread-toggle').click()")
    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length === 1")
    js(qtbot, view, "document.querySelector('.article-row').focus()")
    js(qtbot, view, "document.dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowDown', bubbles:true}))")
    wait_js(qtbot, view, "Boolean(document.querySelector('.article-row.selected'))")


def test_add_edit_remove_and_error_feedback(qtbot, backend, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    view = open_app(qtbot, controller)

    monkeypatch.setattr(controller, "refresh_feed_async", lambda *_args, **_kwargs: True)
    result = js(
        qtbot,
        view,
        "new Promise(resolve => backend.addFeed('example.com/feed.xml', 'Example', raw => resolve(JSON.parse(raw))))",
    )
    assert result["ok"] is True
    source = manager.get_all()[0]

    renamed = js(
        qtbot,
        view,
        f"new Promise(resolve => backend.renameFeed('{source.id}', 'Renamed', raw => resolve(JSON.parse(raw))))",
    )
    assert renamed["ok"] is True
    assert manager.get(source.id).title == "Renamed"

    removed = js(
        qtbot,
        view,
        f"new Promise(resolve => backend.removeFeed('{source.id}', raw => resolve(JSON.parse(raw))))",
    )
    assert removed["ok"] is True
    assert manager.get_all() == []

    error = js(
        qtbot,
        view,
        "new Promise(resolve => backend.removeFeed('missing', raw => resolve(JSON.parse(raw))))",
    )
    assert error["ok"] is False
