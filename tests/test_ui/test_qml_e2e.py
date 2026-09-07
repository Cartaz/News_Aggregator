"""Qt Quick integration coverage without WebEngine."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtQuick")

from PySide6.QtCore import QObject
from config.constants import Paths
from config.settings import SettingsManager
from core.app_controller import AppController
from core.feed_manager import FeedManager
from core.models import FeedItem
from ui.controller import UiController
from ui.window import QmlMainWindow


@pytest.fixture
def backend(tmp_paths):  # type: ignore[no-untyped-def]
    manager = FeedManager(Paths.FEEDS_FILE)
    controller = AppController(manager, SettingsManager(Paths.SETTINGS_FILE))
    ui = UiController(controller, open_external=lambda _url: (True, "Link aperto"))
    yield manager, controller, ui
    ui.shutdown()
    controller.shutdown()


def article(source_id: str, title: str, minutes_ago: int) -> FeedItem:
    return FeedItem.from_raw(
        source_id=source_id,
        title=title,
        link=f"https://example.com/{title.lower().replace(' ', '-')}",
        summary=f"Summary {title}",
        published=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )


def seed_items(manager: FeedManager, source_id: str, items: list[FeedItem]) -> None:
    with manager._lock:
        manager._sources[source_id].items = list(items)
    manager.save()


def test_qml_window_loads_and_exposes_virtualized_views(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller, ui = backend
    manager.add("https://example.com/one.xml", title="One")
    manager.add("https://example.com/two.xml", title="Two")
    ui.sync()
    window = QmlMainWindow(controller, ui)
    try:
        window.show()
        qtbot.waitUntil(window.window.isVisible, timeout=3000)
        assert window.window.findChild(QObject, "sourceList") is not None
        assert window.window.findChild(QObject, "articleList") is not None
        assert window.window.findChild(QObject, "searchInput") is not None
        dialogs = window.window.findChild(QObject, "appDialogs")
        assert dialogs is not None
        assert dialogs.property("backend") is not None
        assert ui.sources.rowCount() == 3
    finally:
        window.window.hide()
        window.shutdown()


def test_scope_filter_and_selection_are_backed_by_python_models(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, _controller, ui = backend
    source = manager.add("https://example.com/feed.xml", title="Example")
    seed_items(manager, source.id, [article(source.id, "Newest", 1), article(source.id, "Older", 2)])
    ui.sync()
    assert ui.articles.rowCount() == 2

    ui.setSearchQuery("Newest")
    assert ui.articles.rowCount() == 1
    ui.selectArticle(0)
    assert ui.selectedArticleTitle == "Newest"

    ui.setSearchQuery("")
    ui.selectArticle(1)
    qtbot.waitUntil(lambda: manager.get(source.id).items[0].read, timeout=3000)
    assert ui.selectedArticleTitle == "Older"


def test_add_update_remove_use_async_controller_commands(qtbot, backend, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    manager, _controller, ui = backend
    monkeypatch.setattr(manager, "refresh", lambda source_id, cancel_event=None: 0)

    with qtbot.waitSignal(ui.operationFinished, timeout=3000) as added:
        ui.addFeed("https://example.com/feed.xml", "Example")
    assert added.args[0:2] == ["addFeed", True]
    assert ui.selectedSourceIsFeed is True

    with qtbot.waitSignal(ui.operationFinished, timeout=3000) as updated:
        ui.updateSelectedFeed("Renamed", "Tech")
    assert updated.args[0:2] == ["updateFeed", True]
    assert ui.selectedSourceTitle == "Renamed"
    assert ui.selectedSourceCategory == "Tech"

    with qtbot.waitSignal(ui.operationFinished, timeout=3000) as removed:
        ui.removeSelectedFeed()
    assert removed.args[0:2] == ["removeFeed", True]
    assert manager.get_all() == []
    assert ui.selectedSourceIsFeed is False


def test_restore_from_tray_resyncs_canonical_state(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller, ui = backend
    source = manager.add("https://example.com/feed.xml", title="Example")
    ui.sync()
    window = QmlMainWindow(controller, ui)
    try:
        window.show()
        qtbot.waitUntil(window.window.isVisible, timeout=3000)
        assert ui.articles.rowCount() == 0
        window.window.hide()
        seed_items(manager, source.id, [article(source.id, "Arrived Hidden", 1)])
        window.restore_from_tray()
        qtbot.waitUntil(lambda: ui.articles.rowCount() == 1, timeout=3000)
    finally:
        window.window.hide()
        window.shutdown()
