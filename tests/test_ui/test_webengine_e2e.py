"""End-to-end tests that execute the real HTML UI inside QWebEngineView."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Must be set before QtWebEngine/QApplication initialization. CI can override
# QT_QPA_PLATFORM with xcb and run these tests under xvfb-run.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu"
)

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


def _js(qtbot, view: QWebEngineView, script: str, timeout: int = 5000) -> Any:
    result: dict[str, Any] = {"done": False, "value": None}

    def completed(value: Any) -> None:
        result["value"] = value
        result["done"] = True

    view.page().runJavaScript(script, completed)
    qtbot.waitUntil(lambda: result["done"], timeout=timeout)
    return result["value"]


def _wait_js(
    qtbot,
    view: QWebEngineView,
    script: str,
    *,
    expected: Any = True,
    timeout: int = 7000,
) -> Any:
    deadline = time.monotonic() + timeout / 1000
    last: Any = None
    while time.monotonic() < deadline:
        last = _js(qtbot, view, script)
        if last == expected:
            return last
        qtbot.wait(40)
    raise AssertionError(
        f"JavaScript condition did not reach {expected!r}; last value={last!r}: {script}"
    )


@pytest.fixture
def backend(tmp_paths, reset_event_bus):  # type: ignore[no-untyped-def]
    AppController._instance = None
    SettingsManager._instance = None
    manager = FeedManager(Paths.FEEDS_FILE)
    settings = SettingsManager(Paths.SETTINGS_FILE)
    controller = AppController(manager, settings)
    yield manager, controller
    controller.shutdown()
    AppController._instance = None
    SettingsManager._instance = None


def _open_app(qtbot, controller: AppController) -> QWebEngineView:
    view = QWebEngineView()
    qtbot.addWidget(view)
    view.resize(1280, 800)

    bridge = WebBridge(controller, view)
    channel = QWebChannel(view.page())
    channel.registerObject("backend", bridge)
    view.page().setWebChannel(channel)
    # Keep Python references alive for the lifetime of the view.
    view._test_bridge = bridge  # type: ignore[attr-defined]
    view._test_channel = channel  # type: ignore[attr-defined]

    with qtbot.waitSignal(view.loadFinished, timeout=10000) as loaded:
        view.load(QUrl.fromLocalFile(str(WEB_ROOT / "index.html")))
    assert loaded.args == [True]
    view.show()
    _wait_js(
        qtbot,
        view,
        "document.getElementById('app').getAttribute('aria-busy') === 'false'",
    )
    return view


def _article(source_id: str, title: str, minutes_ago: int) -> FeedItem:
    published = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return FeedItem.from_raw(
        source_id=source_id,
        title=title,
        link=f"https://example.com/{title.lower()}",
        summary=f"Summary {title}",
        published=published,
    )


def test_real_webengine_boots_and_renders_backend_state(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    manager.add("https://example.com/one.xml", title="One")
    manager.add("https://example.com/two.xml", title="Two")

    view = _open_app(qtbot, controller)

    _wait_js(qtbot, view, "document.querySelectorAll('#feed-list .source-row').length", expected=2)
    assert _js(qtbot, view, "document.getElementById('app-name').textContent") == "News Aggregator"
    assert _js(qtbot, view, "Boolean(window.state && state.backend)") is True


def test_global_refresh_progresses_feed_by_feed_and_reenables_button(
    qtbot, backend, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    first = manager.add("https://example.com/one.xml", title="One")
    second = manager.add("https://example.com/two.xml", title="Two")

    import threading

    started = {first.id: threading.Event(), second.id: threading.Event()}
    release = {first.id: threading.Event(), second.id: threading.Event()}

    def controlled_refresh(source_id: str) -> int:
        started[source_id].set()
        if not release[source_id].wait(5):
            raise RuntimeError(f"test timeout waiting to release {source_id}")
        return 0

    monkeypatch.setattr(manager, "refresh", controlled_refresh)
    view = _open_app(qtbot, controller)

    _js(qtbot, view, "document.getElementById('refresh-all-btn').click(); true")
    assert started[first.id].wait(2)
    assert started[second.id].wait(2)

    _wait_js(
        qtbot,
        view,
        "state.snapshot.refreshing.active === true && state.snapshot.refreshing.scope === 'all' && state.snapshot.refreshing.total === 2",
    )
    _wait_js(
        qtbot,
        view,
        "document.getElementById('refresh-track').hidden === false && document.getElementById('refresh-fill').children.length === 2",
    )

    release[first.id].set()
    _wait_js(qtbot, view, "state.snapshot.refreshing.current", expected=1)
    assert _js(qtbot, view, "document.getElementById('refresh-track').getAttribute('aria-valuenow')") == "1"
    assert _js(
        qtbot,
        view,
        "document.getElementById('refresh-fill').children[0].style.background.includes('var(--accent)')",
    ) is True

    release[second.id].set()
    _wait_js(qtbot, view, "state.snapshot.refreshing.active", expected=False)
    _wait_js(qtbot, view, "document.getElementById('refresh-all-btn').disabled", expected=False)
    assert controller.get_refresh_state()["current"] == 2
    assert controller.get_refresh_state()["total"] == 2


def test_unread_filter_and_arrow_navigation_use_real_frontend(
    qtbot, backend
) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    source = manager.add("https://example.com/feed.xml", title="Example")
    newest = _article(source.id, "Newest", 1)
    older = _article(source.id, "Older", 2)
    source.items = [newest, older]
    manager.save()

    view = _open_app(qtbot, controller)
    _wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", expected=2)

    _js(
        qtbot,
        view,
        """
        (() => {
          const toggle = document.getElementById('unread-toggle');
          toggle.checked = true;
          toggle.dispatchEvent(new Event('change', {bubbles: true}));
          return true;
        })()
        """,
    )
    _wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", expected=2)

    _js(qtbot, view, "document.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true})); true")
    _wait_js(qtbot, view, "state.selectedItemId === state.filteredItems[0].id")
    assert _js(qtbot, view, "document.getElementById('detail-title').textContent") == "Newest"

    _js(qtbot, view, "document.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true})); true")
    _wait_js(qtbot, view, "document.getElementById('detail-title').textContent", expected="Older")
    _wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", expected=1)

    refreshed = manager.get(source.id)
    by_title = {item.title: item for item in refreshed.items}
    assert by_title["Newest"].read is True
    assert by_title["Older"].read is False


def test_add_edit_remove_and_error_feedback_through_real_ui(
    qtbot, backend, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    monkeypatch.setattr(manager, "refresh", lambda source_id: 0)
    view = _open_app(qtbot, controller)

    # Add.
    _js(qtbot, view, "document.getElementById('add-feed-btn').click(); true")
    _wait_js(qtbot, view, "Boolean(document.getElementById('feed-url'))")
    _js(
        qtbot,
        view,
        """
        (() => {
          document.getElementById('feed-url').value = 'https://example.com/feed.xml';
          document.getElementById('feed-title').value = 'Example Feed';
          document.querySelector('#modal-actions .active-accent').click();
          return true;
        })()
        """,
    )
    _wait_js(qtbot, view, "document.querySelectorAll('#feed-list .source-row').length", expected=1)
    _wait_js(qtbot, view, "document.getElementById('feed-actions').hidden", expected=False)

    # Edit title and category.
    _js(qtbot, view, "document.getElementById('edit-feed-btn').click(); true")
    _wait_js(qtbot, view, "Boolean(document.getElementById('edit-title'))")
    _js(
        qtbot,
        view,
        """
        (() => {
          document.getElementById('edit-title').value = 'Renamed Feed';
          document.getElementById('edit-category').value = 'Tech';
          document.querySelector('#modal-actions .active-accent').click();
          return true;
        })()
        """,
    )
    _wait_js(
        qtbot,
        view,
        "document.querySelector('#feed-list .source-label')?.textContent",
        expected="Renamed Feed",
    )
    _wait_js(
        qtbot,
        view,
        "document.querySelector('#category-list .source-label')?.textContent",
        expected="Tech",
    )

    # Remove.
    _js(qtbot, view, "document.getElementById('remove-feed-btn').click(); true")
    _wait_js(qtbot, view, "document.getElementById('modal-title').textContent", expected="Rimuovi feed")
    _js(qtbot, view, "document.querySelector('#modal-actions .active-accent').click(); true")
    _wait_js(qtbot, view, "document.querySelectorAll('#feed-list .source-row').length", expected=0)

    # Invalid scheme must stay in the UI and produce visible feedback.
    _js(qtbot, view, "document.getElementById('add-feed-btn').click(); true")
    _wait_js(qtbot, view, "Boolean(document.getElementById('feed-url'))")
    _js(
        qtbot,
        view,
        """
        (() => {
          document.getElementById('feed-url').value = 'ftp://example.com/feed';
          document.querySelector('#modal-actions .active-accent').click();
          return true;
        })()
        """,
    )
    _wait_js(
        qtbot,
        view,
        "[...document.querySelectorAll('.toast')].some((toast) => toast.textContent.includes('Feed non aggiunto'))",
    )
    assert _js(qtbot, view, "document.getElementById('modal-backdrop').hidden") is False
