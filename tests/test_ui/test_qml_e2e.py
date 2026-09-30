"""Qt Quick integration coverage without WebEngine."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtQuick")

from PySide6.QtCore import QObject, Qt, QMetaObject
from PySide6.QtQuick import QQuickItem
from config.constants import Paths
from config.settings import SettingsManager
from core.app_controller import AppController
from core.feed_manager import FeedManager
from core.models import FeedItem
from ui.controller import UiController
from ui.window import QmlMainWindow


class _NoopSiteIcons:
    def cached_icon_for(self, _source):  # type: ignore[no-untyped-def]
        return None

    def request_icon(self, _source, _callback) -> None:  # type: ignore[no-untyped-def]
        return None

    def shutdown(self) -> None:
        return None


@pytest.fixture
def backend(tmp_paths, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr("ui.controller.SiteIconService", _NoopSiteIcons)
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


def test_minimum_window_keeps_workspace_and_detail_inside_layout(qtbot, backend) -> None:  # type: ignore[no-untyped-def]
    manager, controller, ui = backend
    source = manager.add("https://example.com/feed.xml", title="Example")
    seed_items(manager, source.id, [article(source.id, "Responsive article", 1)])
    ui.sync()
    ui.selectArticle(0)
    window = QmlMainWindow(controller, ui)
    try:
        window.window.resize(900, 600)
        window.show()
        qtbot.waitUntil(window.window.isVisible, timeout=3000)

        workspace = window.window.findChild(QObject, "workspace")
        content = window.window.findChild(QObject, "contentArea")
        columns = window.window.findChild(QObject, "articleColumns")
        article_panel = window.window.findChild(QObject, "articleListPanel")
        detail_panel = window.window.findChild(QObject, "detailPanel")
        assert all(item is not None for item in (workspace, content, columns, article_panel, detail_panel))

        def geometry_is_settled() -> bool:
            assert workspace is not None
            assert content is not None
            assert columns is not None
            assert article_panel is not None
            assert detail_panel is not None
            return (
                float(content.property("x")) + float(content.property("width")) <= float(workspace.property("width")) + 1.0
                and float(detail_panel.property("x")) + float(detail_panel.property("width")) <= float(columns.property("width")) + 1.0
                and float(article_panel.property("width")) >= 269.0
                and float(detail_panel.property("width")) >= 299.0
            )

        qtbot.waitUntil(geometry_is_settled, timeout=3000)
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


def test_external_read_and_metadata_events_update_visible_state(qtbot, backend):
    manager, controller, ui = backend
    source = manager.add("https://example.com/feed.xml", title="Original")
    seed_items(manager, source.id, [article(source.id, "Item", 1)])
    ui.sync()
    ui.selectSource(ui.sources.index_for("feed", source.id))
    ui.selectArticle(0)
    controller.rename_feed(source.id, "Renamed")
    qtbot.waitUntil(lambda: ui.scopeTitle == "Renamed")
    controller.mark_read(source.id, ui.selectedArticleId)
    qtbot.waitUntil(lambda: ui.selectedArticleRead)
    controller.remove_feed(source.id)
    qtbot.waitUntil(lambda: not ui.hasSelectedArticle)
    assert ui.sources.row(0).selected is True
    assert ui.selectedSourceRow == 0


def test_config_event_clears_filtered_detail(qtbot, backend):
    manager, controller, ui = backend
    source = manager.add("https://example.com/feed.xml")
    seed_items(manager, source.id, [article(source.id, "Item", 1)])
    ui.sync()
    ui.selectArticle(0)
    controller.mark_read(source.id, ui.selectedArticleId)
    qtbot.waitUntil(lambda: ui.selectedArticleRead)
    controller.update_settings({"show_unread_only": True})
    qtbot.waitUntil(lambda: ui.unreadOnly)
    assert ui.articles.rowCount() == 0
    assert not ui.hasSelectedArticle


def test_filter_reset_does_not_select_another_article_or_mark_read(qtbot, backend):
    manager, controller, ui = backend
    source = manager.add("https://example.com/feed.xml")
    seed_items(manager, source.id, [article(source.id, "Newest", 1), article(source.id, "Older", 2)])
    ui.sync()
    window = QmlMainWindow(controller, ui)
    try:
        window.show()
        ui.selectArticle(0)
        view = window.window.findChild(QQuickItem, "articleList")
        view.forceActiveFocus()
        ui.setSearchQuery("Older")
        qtbot.wait(100)
        assert not ui.hasSelectedArticle
        assert view.property("currentIndex") == -1
        assert not any(item.read for item in manager.get(source.id).items)
        qtbot.keyClick(window.window, Qt.Key.Key_Down)
        qtbot.waitUntil(lambda: ui.selectedArticleTitle == "Older")
    finally:
        window.window.hide()
        window.shutdown()


def test_add_dialog_focus_accepts_typing(qtbot, backend):
    _manager, controller, ui = backend
    window = QmlMainWindow(controller, ui)
    try:
        window.show()
        dialogs = window.window.findChild(QObject, "appDialogs")
        assert QMetaObject.invokeMethod(dialogs, "openAddFeed")
        qtbot.waitUntil(lambda: window.window.activeFocusItem() is not None and window.window.activeFocusItem().property("text") is not None)
        for character in "example.com":
            qtbot.keyClick(window.window, ord(character.upper()))
        assert window.window.activeFocusItem().property("text").casefold() == "example.com"
    finally:
        window.window.hide()
        window.shutdown()


def test_hide_without_tray_keeps_window_reachable(qtbot, backend, monkeypatch):
    _manager, controller, ui = backend
    monkeypatch.setattr("ui.window.QSystemTrayIcon.isSystemTrayAvailable", lambda: False)
    window = QmlMainWindow(controller, ui)
    try:
        window.show()
        with qtbot.waitSignal(ui.toastRequested):
            window.hide_to_tray()
        assert window.window.isVisible()
    finally:
        window.window.hide()
        window.shutdown()


def test_diagnostics_runs_off_gui_and_closed_log_discards_pending_result(qtbot, backend, monkeypatch):
    import threading
    _manager, controller, ui = backend
    started, release = threading.Event(), threading.Event()
    observed = []

    def slow_log(_limit):
        observed.append(threading.current_thread())
        started.set()
        assert release.wait(2)
        return {"path": "app.log", "lines": ["Delayed"]}

    monkeypatch.setattr(controller, "get_log_tail", slow_log)
    try:
        assert ui.diagnostics.load()
        assert started.wait(1)
        assert observed[0] is not threading.current_thread()
        ui.diagnostics.clear()
    finally:
        release.set()
    qtbot.wait(100)
    assert ui.diagnostics.text == ""
    with qtbot.waitSignal(ui.diagnostics.changed):
        assert ui.diagnostics.load()
    assert ui.diagnostics.text == "Delayed"


def test_article_summary_cannot_enable_rich_text(qtbot, backend):
    from dataclasses import replace
    from PySide6.QtQml import QQmlEngine, QQmlExpression
    manager, controller, ui = backend
    source = manager.add("https://example.com/feed.xml")
    markup = '<img src="https://example.com/remote.png">'
    item = replace(article(source.id, "Literal markup", 1), summary=markup)
    seed_items(manager, source.id, [item])
    ui.sync()
    ui.selectArticle(0)
    window = QmlMainWindow(controller, ui)
    try:
        summary = window.window.findChild(QObject, "summaryText")
        assert summary.property("text") == markup
        expression = QQmlExpression(QQmlEngine.contextForObject(summary), summary, "textFormat === 0")
        assert expression.evaluate()[0] is True  # QQuickText.PlainText
    finally:
        window.shutdown()
