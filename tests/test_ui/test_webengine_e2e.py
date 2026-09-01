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


def article(source_id: str, title: str, minutes_ago: int) -> FeedItem:
    return FeedItem.from_raw(
        source_id=source_id,
        title=title,
        link=f"https://example.com/{title.lower()}",
        summary=f"Summary {title}",
        published=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )


def seed_items(manager: FeedManager, source_id: str, items: list[FeedItem]) -> None:
    """Test-only setup that preserves the production defensive-read contract."""
    with manager._lock:
        manager._sources[source_id].items = list(items)
    manager.save()


def test_webengine_boots_with_real_webchannel(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    manager.add("https://example.com/one.xml", title="One")
    manager.add("https://example.com/two.xml", title="Two")
    view = open_app(qtbot, controller)
    wait_js(qtbot, view, "document.querySelectorAll('#feed-list .source-row').length", 2)
    assert js(qtbot, view, "document.getElementById('app-name').textContent") == "News Aggregator"
    assert js(qtbot, view, "typeof state !== 'undefined' && Boolean(state.backend)") is True


def test_refresh_progresses_one_segment_per_completed_feed(qtbot, backend, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    first = manager.add("https://example.com/one.xml", title="One")
    second = manager.add("https://example.com/two.xml", title="Two")
    started = {first.id: threading.Event(), second.id: threading.Event()}
    release = {first.id: threading.Event(), second.id: threading.Event()}

    def controlled_refresh(source_id: str, cancel_event=None) -> int:  # type: ignore[no-untyped-def]
        assert cancel_event is not None
        started[source_id].set()
        if not release[source_id].wait(5):
            raise RuntimeError("test refresh release timeout")
        return 0

    monkeypatch.setattr(manager, "refresh", controlled_refresh)
    view = open_app(qtbot, controller)
    js(qtbot, view, "document.getElementById('refresh-all-btn').click(); true")
    assert started[first.id].wait(2) and started[second.id].wait(2)
    wait_js(qtbot, view, "state.snapshot.refreshing.active && state.snapshot.refreshing.total === 2")
    wait_js(qtbot, view, "!document.getElementById('refresh-track').hidden && document.getElementById('refresh-fill').children.length === 2")
    release[first.id].set()
    wait_js(qtbot, view, "state.snapshot.refreshing.current", 1)
    assert js(qtbot, view, "document.getElementById('refresh-track').getAttribute('aria-valuenow')") == "1"
    release[second.id].set()
    wait_js(qtbot, view, "state.snapshot.refreshing.active", False)
    wait_js(qtbot, view, "document.getElementById('refresh-all-btn').disabled", False)
    assert controller.get_refresh_state()["current"] == 2


def test_background_refresh_reloads_current_scope_without_reclick(qtbot, backend, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    source = manager.add("https://example.com/feed.xml", title="Example")
    manager.set_category(source.id, "Tech")

    def background_refresh(source_id: str, cancel_event=None) -> int:  # type: ignore[no-untyped-def]
        assert cancel_event is not None
        seed_items(manager, source_id, [article(source_id, "Background News", 1)])
        return 1

    monkeypatch.setattr(manager, "refresh", background_refresh)
    view = open_app(qtbot, controller)
    js(qtbot, view, "document.querySelector('#category-list .source-row').click(); true")
    wait_js(qtbot, view, "document.getElementById('content-title').textContent", "Tech")
    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", 0)

    assert controller.refresh_all_async() is True
    wait_js(qtbot, view, "state.snapshot.refreshing.active", False)
    wait_js(qtbot, view, "document.getElementById('all-unread').textContent", "1")
    wait_js(qtbot, view, "document.querySelector('#category-list .count-badge').textContent", "1")
    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", 1)
    assert js(qtbot, view, "document.querySelector('.article-title').textContent") == "Background News"
    assert js(qtbot, view, "document.getElementById('content-title').textContent") == "Tech"

    badge = "document.querySelector('#category-list .count-badge')"
    assert js(qtbot, view, f"getComputedStyle({badge}).color") == "rgb(255, 102, 0)"
    assert js(qtbot, view, f"getComputedStyle({badge}).backgroundColor") == "rgb(20, 20, 20)"
    assert js(qtbot, view, f"getComputedStyle({badge}).boxShadow") != "none"
    assert js(qtbot, view, f"getComputedStyle({badge}).borderRadius") == "10px"
    assert js(qtbot, view, f"getComputedStyle({badge}).height") == "23px"


def test_resume_sync_recovers_after_hidden_refresh_signals_are_missed(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    source = manager.add("https://example.com/feed.xml", title="Example")
    manager.set_category(source.id, "Tech")
    view = open_app(qtbot, controller)
    js(qtbot, view, "document.querySelector('#category-list .source-row').click(); true")
    wait_js(qtbot, view, "document.getElementById('content-title').textContent", "Tech")
    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", 0)

    view.hide()
    seed_items(manager, source.id, [article(source.id, "Hidden News", 1)])

    # No controller/WebChannel event is emitted: this simulates a hidden
    # WebEngine page missing the background state transition entirely.
    view.show()
    view._bridge.uiSyncRequested.emit()  # type: ignore[attr-defined]

    wait_js(qtbot, view, "document.getElementById('all-unread').textContent", "1")
    wait_js(qtbot, view, "document.querySelector('#category-list .count-badge').textContent", "1")
    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", 1)
    assert js(qtbot, view, "document.querySelector('.article-title').textContent") == "Hidden News"


def test_unread_filter_and_arrow_navigation(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    source = manager.add("https://example.com/feed.xml", title="Example")
    seed_items(
        manager,
        source.id,
        [article(source.id, "Newest", 1), article(source.id, "Older", 2)],
    )
    view = open_app(qtbot, controller)
    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", 2)
    js(qtbot, view, "const t=document.getElementById('unread-toggle');t.checked=true;t.dispatchEvent(new Event('change',{bubbles:true}));true")
    js(qtbot, view, "document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));true")
    wait_js(qtbot, view, "document.getElementById('detail-title').textContent", "Newest")
    js(qtbot, view, "document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));true")
    wait_js(qtbot, view, "document.getElementById('detail-title').textContent", "Older")
    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", 1)
    items = {item.title: item for item in manager.get(source.id).items}
    assert items["Newest"].read is True
    assert items["Older"].read is False


def test_add_edit_remove_and_error_feedback(qtbot, backend, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    monkeypatch.setattr(manager, "refresh", lambda source_id, cancel_event=None: 0)
    view = open_app(qtbot, controller)

    js(qtbot, view, "document.getElementById('add-feed-btn').click();true")
    wait_js(qtbot, view, "Boolean(document.getElementById('feed-url'))")
    js(qtbot, view, "document.getElementById('feed-url').value='https://example.com/feed.xml';document.getElementById('feed-title').value='Example Feed';document.querySelector('#modal-actions .active-accent').click();true")
    wait_js(qtbot, view, "document.querySelectorAll('#feed-list .source-row').length", 1)
    wait_js(qtbot, view, "document.getElementById('feed-actions').hidden", False)

    js(qtbot, view, "document.getElementById('edit-feed-btn').click();true")
    wait_js(qtbot, view, "Boolean(document.getElementById('edit-title'))")
    js(qtbot, view, "document.getElementById('edit-title').value='Renamed Feed';document.getElementById('edit-category').value='Tech';document.querySelector('#modal-actions .active-accent').click();true")
    wait_js(qtbot, view, "document.querySelector('#feed-list .source-label')?.textContent", "Renamed Feed")
    wait_js(qtbot, view, "document.querySelector('#category-list .source-label')?.textContent", "Tech")

    js(qtbot, view, "document.getElementById('remove-feed-btn').click();true")
    wait_js(qtbot, view, "document.getElementById('modal-title').textContent", "Rimuovi feed")
    js(qtbot, view, "document.querySelector('#modal-actions .active-accent').click();true")
    wait_js(qtbot, view, "document.querySelectorAll('#feed-list .source-row').length", 0)

    js(qtbot, view, "document.getElementById('add-feed-btn').click();true")
    wait_js(qtbot, view, "Boolean(document.getElementById('feed-url'))")
    js(qtbot, view, "document.getElementById('feed-url').value='invalid-scheme://example/feed';document.querySelector('#modal-actions .active-accent').click();true")
    wait_js(qtbot, view, "[...document.querySelectorAll('.toast')].some(t=>t.textContent.includes('Feed non aggiunto'))")
    assert js(qtbot, view, "document.getElementById('modal-backdrop').hidden") is False
