"""Native window restore regression coverage for the desktop UI."""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")

from config.constants import Paths
from config.settings import SettingsManager
from core.app_controller import AppController
from core.feed_manager import FeedManager
from core.models import FeedItem
from ui.window import WebMainWindow

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def js(qtbot, view, script: str, timeout: int = 5000) -> Any:  # type: ignore[no-untyped-def]
    box: dict[str, Any] = {"done": False, "value": None}

    def done(value: Any) -> None:
        box.update(done=True, value=value)

    view.page().runJavaScript(script, done)
    qtbot.waitUntil(lambda: box["done"], timeout=timeout)
    return box["value"]


def wait_js(qtbot, view, script: str, expected: Any = True, timeout: int = 7000) -> None:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + timeout / 1000
    last = None
    while time.monotonic() < deadline:
        last = js(qtbot, view, script)
        if last == expected:
            return
        qtbot.wait(40)
    raise AssertionError(f"Expected {expected!r}, got {last!r}: {script}")


@pytest.fixture
def backend(tmp_paths, reset_event_bus):  # type: ignore[no-untyped-def]
    AppController._instance = None
    SettingsManager._instance = None
    manager = FeedManager(Paths.FEEDS_FILE)
    controller = AppController(manager, SettingsManager(Paths.SETTINGS_FILE))
    yield manager, controller
    controller.shutdown()
    AppController._instance = None
    SettingsManager._instance = None


def article(source_id: str, title: str) -> FeedItem:
    return FeedItem.from_raw(
        source_id=source_id,
        title=title,
        link=f"https://example.com/{title.lower().replace(' ', '-')}",
        summary=f"Summary {title}",
        published=datetime.now(timezone.utc) - timedelta(minutes=1),
    )


def test_native_restore_resyncs_stale_snapshot_and_items(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller = backend
    source = manager.add("https://example.com/feed.xml", title="Example")

    window = WebMainWindow(controller)
    window.resize(1280, 800)
    window.show()
    view = window._view  # type: ignore[attr-defined]
    wait_js(qtbot, view, "document.getElementById('app').getAttribute('aria-busy') === 'false'")
    wait_js(qtbot, view, "document.getElementById('all-unread').textContent", "0")
    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", 0)

    window.hide()
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=2000)

    # Simulate an auto-refresh having updated the persistent/core state while
    # WebEngine received no stateChanged/backendEvent signal at all.
    refreshed = manager.get(source.id)
    refreshed.items = [article(source.id, "Arrived While Hidden")]
    manager.save()

    window.restore_from_tray()
    qtbot.waitUntil(window.isVisible, timeout=2000)
    wait_js(qtbot, view, "document.getElementById('all-unread').textContent", "1")
    wait_js(qtbot, view, "document.querySelectorAll('.article-row').length", 1)
    assert js(qtbot, view, "document.querySelector('.article-title').textContent") == "Arrived While Hidden"

    window.hide()
    window.deleteLater()


def test_main_routes_tray_restore_through_single_sync_path() -> None:
    source = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
    assert "tray.showWindowRequested.connect(window.restore_from_tray)" in source
    assert "tray.messageClicked.connect(window.restore_from_tray)" in source
    assert "tray.showWindowRequested.connect(window.showNormal)" not in source
