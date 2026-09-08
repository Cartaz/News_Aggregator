"""Focused QObject adapter between QML and the Python application controller."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Property, Qt, Signal, Slot

from config.constants import AppMeta
from core.app_controller import AppController
from core.models import FeedItem, FeedSource
from core.site_icon_service import SiteIconService
from ui.diagnostics import DiagnosticsAdapter
from ui.models import ArticleListModel, SourceListModel, SourceRowData
from ui.preferences import PreferencesAdapter

logger = logging.getLogger(__name__)

OpenExternalPort = Callable[[str], tuple[bool, str]]


class UiController(QObject):
    """Expose a small typed QML API while keeping Python as state owner."""

    requestQuit = Signal()
    requestHide = Signal()
    toastRequested = Signal(str, str, bool)
    operationFinished = Signal(str, bool, str)
    unreadCountChanged = Signal(int)
    newItemsDetected = Signal(int, str)

    scopeChanged = Signal()
    articleSelectionChanged = Signal()
    filterChanged = Signal()
    refreshChanged = Signal()
    selectedSourceChanged = Signal()

    _eventRelay = Signal(str, object)
    _commandRelay = Signal(str, bool, str, str)
    _siteIconRelay = Signal(str, str)

    def __init__(
        self,
        controller: AppController,
        parent: QObject | None = None,
        *,
        open_external: OpenExternalPort | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._open_external = open_external
        self._sources = SourceListModel(self)
        self._articles = ArticleListModel(self)
        self._preferences = PreferencesAdapter(controller, self)
        self._diagnostics = DiagnosticsAdapter(controller, self)
        self._site_icons = SiteIconService()
        self._scope_kind = "all"
        self._scope_id = ""
        self._scope_title = "Tutti gli articoli"
        self._selected_source_row = 0
        self._selected_article_id = ""
        self._selected_article: FeedItem | None = None
        self._selected_article_source = ""
        self._search_query = ""
        self._unread_only = bool(controller.settings.show_unread_only)
        self._refresh_state = controller.get_refresh_state()
        self._shutdown = False

        self._eventRelay.connect(self._deliver_event, Qt.ConnectionType.QueuedConnection)
        self._commandRelay.connect(self._deliver_command, Qt.ConnectionType.QueuedConnection)
        self._siteIconRelay.connect(
            self._deliver_site_icon,
            Qt.ConnectionType.QueuedConnection,
        )
        controller.register_event_listener(self._relay_controller_event)
        self.sync()

    @Property(QObject, constant=True)
    def sources(self) -> SourceListModel:
        return self._sources

    @Property(QObject, constant=True)
    def articles(self) -> ArticleListModel:
        return self._articles

    @Property(QObject, constant=True)
    def preferences(self) -> PreferencesAdapter:
        return self._preferences

    @Property(QObject, constant=True)
    def diagnostics(self) -> DiagnosticsAdapter:
        return self._diagnostics

    @Property(str, constant=True)
    def appName(self) -> str:  # noqa: N802 - QML API
        return AppMeta.DISPLAY_NAME

    @Property(str, constant=True)
    def appVersion(self) -> str:  # noqa: N802 - QML API
        return AppMeta.VERSION

    @Property(str, notify=scopeChanged)
    def scopeTitle(self) -> str:  # noqa: N802
        return self._scope_title

    @Property(int, notify=scopeChanged)
    def visibleArticleCount(self) -> int:  # noqa: N802
        return self._articles.rowCount()

    @Property(int, notify=scopeChanged)
    def totalArticleCount(self) -> int:  # noqa: N802
        return self._articles.total_count()

    @Property(int, notify=selectedSourceChanged)
    def selectedSourceRow(self) -> int:  # noqa: N802
        return self._selected_source_row

    @Property(bool, notify=selectedSourceChanged)
    def selectedSourceIsFeed(self) -> bool:  # noqa: N802
        row = self._sources.row(self._selected_source_row)
        return bool(row and row.kind == "feed")

    @Property(str, notify=selectedSourceChanged)
    def selectedSourceTitle(self) -> str:  # noqa: N802
        row = self._sources.row(self._selected_source_row)
        return row.title if row and row.kind == "feed" else ""

    @Property(str, notify=selectedSourceChanged)
    def selectedSourceStatus(self) -> str:  # noqa: N802
        row = self._sources.row(self._selected_source_row)
        if row is None or row.kind != "feed":
            return ""
        if row.error:
            return f"Errore: {row.error}"
        return row.status

    @Property(str, notify=selectedSourceChanged)
    def selectedSourceCategory(self) -> str:  # noqa: N802
        row = self._sources.row(self._selected_source_row)
        if row is None or row.kind != "feed":
            return ""
        try:
            return self._controller.get_feed(row.identifier).category
        except Exception:
            return ""

    @Property(str, notify=selectedSourceChanged)
    def selectedSourceUrl(self) -> str:  # noqa: N802
        row = self._sources.row(self._selected_source_row)
        if row is None or row.kind != "feed":
            return ""
        try:
            return self._controller.get_feed(row.identifier).url
        except Exception:
            return ""

    @Property(bool, notify=articleSelectionChanged)
    def hasSelectedArticle(self) -> bool:  # noqa: N802
        return self._selected_article is not None

    @Property(str, notify=articleSelectionChanged)
    def selectedArticleId(self) -> str:  # noqa: N802
        return self._selected_article.id if self._selected_article else ""

    @Property(int, notify=articleSelectionChanged)
    def selectedArticleRow(self) -> int:  # noqa: N802
        if not self._selected_article_id:
            return -1
        return self._articles.index_for_item(self._selected_article_id)

    @Property(str, notify=articleSelectionChanged)
    def selectedArticleTitle(self) -> str:  # noqa: N802
        return self._selected_article.title if self._selected_article else ""

    @Property(str, notify=articleSelectionChanged)
    def selectedArticleSource(self) -> str:  # noqa: N802
        return self._selected_article_source

    @Property(str, notify=articleSelectionChanged)
    def selectedArticleAuthor(self) -> str:  # noqa: N802
        if self._selected_article is None or not self._selected_article.author:
            return ""
        return f"Di {self._selected_article.author}"

    @Property(str, notify=articleSelectionChanged)
    def selectedArticleSummary(self) -> str:  # noqa: N802
        if self._selected_article is None:
            return ""
        return self._selected_article.summary or "Nessun sommario disponibile per questo articolo."

    @Property(str, notify=articleSelectionChanged)
    def selectedArticleDate(self) -> str:  # noqa: N802
        if self._selected_article is None:
            return ""
        return self._selected_article.published.astimezone().strftime("%d/%m/%Y %H:%M")

    @Property(bool, notify=articleSelectionChanged)
    def selectedArticleRead(self) -> bool:  # noqa: N802
        return bool(self._selected_article and self._selected_article.read)

    @Property(bool, notify=articleSelectionChanged)
    def selectedArticleHasLink(self) -> bool:  # noqa: N802
        return bool(self._selected_article and self._selected_article.link)

    @Property(bool, notify=filterChanged)
    def unreadOnly(self) -> bool:  # noqa: N802
        return self._unread_only

    @Property(bool, notify=refreshChanged)
    def refreshing(self) -> bool:
        return bool(self._refresh_state.get("active", False))

    @Property(str, notify=refreshChanged)
    def refreshScope(self) -> str:  # noqa: N802
        return str(self._refresh_state.get("scope", ""))

    @Property(int, notify=refreshChanged)
    def refreshCurrent(self) -> int:  # noqa: N802
        return int(self._refresh_state.get("current", 0) or 0)

    @Property(int, notify=refreshChanged)
    def refreshTotal(self) -> int:  # noqa: N802
        return int(self._refresh_state.get("total", 0) or 0)

    @Slot()
    def sync(self) -> None:
        """Refresh view snapshots from canonical Python state."""
        if self._shutdown:
            return
        try:
            feeds = self._controller.get_all_feeds()
            categories = self._controller.get_categories()
            self._rebuild_sources(feeds, categories)
            self._reload_articles(feeds)
            self._refresh_state = self._controller.get_refresh_state()
            self._unread_only = bool(self._controller.settings.show_unread_only)
            self._articles.set_filter(self._search_query, self._unread_only)
            self._restore_selected_article()
            self._emit_snapshot_signals()
        except Exception as exc:
            logger.exception("Sincronizzazione QML fallita")
            self.toastRequested.emit("Sincronizzazione non riuscita", str(exc), True)

    def _emit_snapshot_signals(self) -> None:
        self.scopeChanged.emit()
        self.selectedSourceChanged.emit()
        self.articleSelectionChanged.emit()
        self._preferences.sync()
        self.filterChanged.emit()
        self.refreshChanged.emit()
        self.unreadCountChanged.emit(self._controller.get_total_unread_count())

    def _rebuild_sources(self, feeds: list[FeedSource], categories: list[str]) -> None:
        unread_by_category: dict[str, int] = {}
        for feed in feeds:
            if feed.category:
                unread_by_category[feed.category] = (
                    unread_by_category.get(feed.category, 0) + feed.unread_count
                )

        rows: list[SourceRowData] = [
            SourceRowData(
                kind="all",
                identifier="",
                title="Tutti gli articoli",
                unread_count=self._controller.get_total_unread_count(),
                selected=self._scope_kind == "all",
            )
        ]
        for category in categories:
            rows.append(
                SourceRowData(
                    kind="category",
                    identifier=category,
                    title=category,
                    unread_count=unread_by_category.get(category, 0),
                    selected=(
                        self._scope_kind == "category"
                        and self._scope_id == category
                    ),
                )
            )

        missing_icons: list[FeedSource] = []
        for index, feed in enumerate(feeds):
            status = "Mai aggiornato"
            if feed.last_updated is not None:
                status = (
                    "Aggiornato "
                    + feed.last_updated.astimezone().strftime("%d/%m %H:%M")
                )
            cached_icon = self._site_icons.cached_icon_for(feed)
            if cached_icon is None:
                missing_icons.append(feed)
            rows.append(
                SourceRowData(
                    kind="feed",
                    identifier=feed.id,
                    title=feed.title or feed.url,
                    unread_count=feed.unread_count,
                    selected=(
                        self._scope_kind == "feed" and self._scope_id == feed.id
                    ),
                    status=status,
                    error=feed.last_error,
                    first_feed=index == 0,
                    icon_source=cached_icon.as_uri() if cached_icon else "",
                )
            )
        self._sources.replace(rows)
        for feed in missing_icons:
            self._site_icons.request_icon(feed, self._site_icon_ready)

        selected = self._sources.index_for(self._scope_kind, self._scope_id)
        if selected < 0:
            self._scope_kind = "all"
            self._scope_id = ""
            self._scope_title = "Tutti gli articoli"
            selected = 0
        self._selected_source_row = selected

    def _site_icon_ready(self, source_id: str, path: Path | None) -> None:
        if path is not None:
            self._siteIconRelay.emit(source_id, path.as_uri())

    @Slot(str, str)
    def _deliver_site_icon(self, source_id: str, icon_source: str) -> None:
        if self._shutdown or not icon_source:
            return
        self._sources.set_icon_source(source_id, icon_source)

    def _sync_navigation(self) -> None:
        """Refresh only source navigation/counts after one feed-level event."""
        if self._shutdown:
            return
        try:
            feeds = self._controller.get_all_feeds()
            self._rebuild_sources(feeds, self._controller.get_categories())
            self.selectedSourceChanged.emit()
            self.unreadCountChanged.emit(self._controller.get_total_unread_count())
        except Exception as exc:
            logger.exception("Sincronizzazione navigazione QML fallita")
            self.toastRequested.emit("Sincronizzazione non riuscita", str(exc), True)

    def _reload_articles(self, feeds: list[FeedSource] | None = None) -> None:
        feeds = feeds if feeds is not None else self._controller.get_all_feeds()
        titles = {feed.id: (feed.title or feed.url) for feed in feeds}
        items = self._controller.get_items(self._scope_kind, self._scope_id, 500)
        self._articles.replace_items(items, titles)
        self._articles.set_filter(self._search_query, self._unread_only)

    def _restore_selected_article(self) -> None:
        if not self._selected_article_id:
            self._selected_article = None
            self._selected_article_source = ""
            return
        row_index = self._articles.index_for_item(self._selected_article_id)
        row = self._articles.row(row_index)
        if row is None:
            self._selected_article = None
            self._selected_article_source = ""
            return
        self._selected_article = row.item
        self._selected_article_source = row.source_title

    @Slot(int)
    def selectSource(self, row_index: int) -> None:  # noqa: N802
        row = self._sources.row(int(row_index))
        if row is None:
            return
        self._scope_kind = row.kind
        self._scope_id = row.identifier
        self._scope_title = row.title
        self._selected_source_row = int(row_index)
        self._selected_article_id = ""
        self._selected_article = None
        self._selected_article_source = ""
        feeds = self._controller.get_all_feeds()
        self._rebuild_sources(feeds, self._controller.get_categories())
        self._reload_articles(feeds)
        self.scopeChanged.emit()
        self.selectedSourceChanged.emit()
        self.articleSelectionChanged.emit()

    @Slot(int)
    def selectArticle(self, row_index: int) -> None:  # noqa: N802
        row = self._articles.row(int(row_index))
        if row is None or row.item.id == self._selected_article_id:
            return
        previous = self._selected_article
        self._selected_article_id = row.item.id
        self._selected_article = row.item
        self._selected_article_source = row.source_title
        self.articleSelectionChanged.emit()

        if previous and not previous.read and self._controller.settings.mark_read_on_select:
            self._queue_mutation(
                "auto_mark_read",
                lambda done: self._controller.mark_read_async(previous.source_id, previous.id, done),
            )

    @Slot(str)
    def setSearchQuery(self, query: str) -> None:  # noqa: N802
        self._search_query = query or ""
        self._articles.set_filter(self._search_query, self._unread_only)
        self._restore_selected_article()
        self.scopeChanged.emit()
        self.articleSelectionChanged.emit()

    @Slot(bool)
    def setUnreadOnly(self, enabled: bool) -> None:  # noqa: N802
        enabled = bool(enabled)
        self._unread_only = enabled
        self._articles.set_filter(self._search_query, enabled)
        self._restore_selected_article()
        self.filterChanged.emit()
        self.scopeChanged.emit()
        self.articleSelectionChanged.emit()
        self._queue_mutation(
            "unread_filter",
            lambda done: self._controller.update_settings_async(
                {"show_unread_only": enabled}, done
            ),
        )

    @Slot()
    def refreshAll(self) -> None:  # noqa: N802
        if not self._controller.refresh_all_async(self._refresh_all_done):
            self.toastRequested.emit("Aggiornamento non avviato", "Un aggiornamento è già in corso.", True)
            return
        self._refresh_state = self._controller.get_refresh_state()
        self.refreshChanged.emit()

    @Slot()
    def refreshSelectedFeed(self) -> None:  # noqa: N802
        row = self._sources.row(self._selected_source_row)
        if row is None or row.kind != "feed":
            return
        if not self._controller.refresh_feed_async(row.identifier, self._refresh_feed_done):
            self.toastRequested.emit("Aggiornamento non avviato", "Un aggiornamento è già in corso.", True)
            return
        self._refresh_state = self._controller.get_refresh_state()
        self.refreshChanged.emit()

    @Slot(str, str)
    def addFeed(self, url: str, title: str) -> None:  # noqa: N802
        try:
            normalized = self._normalize_url(url)
        except ValueError as exc:
            self.operationFinished.emit("addFeed", False, str(exc))
            return
        self._queue_mutation(
            "addFeed",
            lambda done: self._controller.add_feed_async(normalized, title.strip(), done),
        )

    @Slot(str, str)
    def updateSelectedFeed(self, title: str, category: str) -> None:  # noqa: N802
        row = self._sources.row(self._selected_source_row)
        if row is None or row.kind != "feed":
            self.operationFinished.emit("updateFeed", False, "Nessun feed selezionato")
            return
        self._queue_mutation(
            "updateFeed",
            lambda done: self._controller.update_feed_async(
                row.identifier, title.strip(), category.strip(), done
            ),
        )

    @Slot()
    def removeSelectedFeed(self) -> None:  # noqa: N802
        row = self._sources.row(self._selected_source_row)
        if row is None or row.kind != "feed":
            self.operationFinished.emit("removeFeed", False, "Nessun feed selezionato")
            return
        self._queue_mutation(
            "removeFeed",
            lambda done: self._controller.remove_feed_async(row.identifier, done),
        )

    @Slot()
    def markSelectedRead(self) -> None:  # noqa: N802
        item = self._selected_article
        if item is None or item.read:
            return
        self._queue_mutation(
            "markRead",
            lambda done: self._controller.mark_read_async(item.source_id, item.id, done),
        )

    @Slot()
    def openSelectedArticle(self) -> None:  # noqa: N802
        item = self._selected_article
        if item is None or not item.link:
            return
        if self._open_external is None:
            self.toastRequested.emit("Link non aperto", "Apertura browser non disponibile", True)
            return
        ok, message = self._open_external(item.link)
        if not ok:
            self.toastRequested.emit("Link non aperto", message, True)

    @Slot()
    def hideApp(self) -> None:  # noqa: N802
        self.requestHide.emit()

    @Slot()
    def quitApp(self) -> None:  # noqa: N802
        self.requestQuit.emit()

    def _queue_mutation(self, action: str, submit: Any) -> None:
        def done(
            _operation_id: str,
            result: Any | None,
            error: Exception | None,
        ) -> None:
            result_id = result.id if isinstance(result, FeedSource) else ""
            self._commandRelay.emit(
                action,
                error is None,
                "" if error is None else (str(error) or "Operazione non riuscita"),
                result_id,
            )

        try:
            operation_id = submit(done)
        except Exception as exc:
            logger.exception("Comando %s non avviato", action)
            self.operationFinished.emit(action, False, str(exc))
            return
        if operation_id is None:
            self.operationFinished.emit(
                action,
                False,
                "Operazione non accettata: applicazione in chiusura",
            )

    @Slot(str, bool, str, str)
    def _deliver_command(
        self,
        action: str,
        success: bool,
        error_message: str,
        result_id: str,
    ) -> None:
        if not success:
            message = error_message or "Operazione non riuscita"
            if action == "unread_filter":
                self._unread_only = bool(self._controller.settings.show_unread_only)
                self._articles.set_filter(self._search_query, self._unread_only)
                self._restore_selected_article()
                self.filterChanged.emit()
                self.scopeChanged.emit()
                self.articleSelectionChanged.emit()
                self.toastRequested.emit("Filtro non salvato", message, True)
            elif action in {"auto_mark_read", "markRead"}:
                self.toastRequested.emit("Stato non aggiornato", message, True)
            self.operationFinished.emit(action, False, message)
            return

        if action == "addFeed" and result_id:
            try:
                source = self._controller.get_feed(result_id)
            except Exception as exc:
                logger.exception("Feed appena aggiunto non rileggibile")
                self.sync()
                self.operationFinished.emit(action, False, str(exc))
                return
            self._scope_kind = "feed"
            self._scope_id = source.id
            self._scope_title = source.title or source.url
            self._selected_article_id = ""
            self.sync()
            refresh_started = self._controller.refresh_feed_async(
                source.id,
                self._refresh_feed_done,
            )
            message = (
                "Il primo aggiornamento è stato avviato."
                if refresh_started
                else "Feed salvato; un altro aggiornamento è già in corso."
            )
            self.operationFinished.emit(action, True, message)
            return

        if action == "removeFeed":
            self._scope_kind = "all"
            self._scope_id = ""
            self._scope_title = "Tutti gli articoli"
            self._selected_article_id = ""

        self.sync()
        messages = {
            "updateFeed": "Feed aggiornato",
            "removeFeed": "Feed rimosso",
            "markRead": "Articolo segnato come letto",
            "unread_filter": "Filtro salvato",
            "auto_mark_read": "",
        }
        self.operationFinished.emit(
            action, True, messages.get(action, "Operazione completata")
        )

    def _relay_controller_event(self, event_name: str, payload: dict[str, Any]) -> None:
        self._eventRelay.emit(event_name, dict(payload))

    def _refresh_all_done(self, result: dict[str, Any]) -> None:
        self._eventRelay.emit("refresh_callback_all", dict(result))

    def _refresh_feed_done(self, success: bool, message: str) -> None:
        self._eventRelay.emit(
            "refresh_callback_feed",
            {"success": bool(success), "message": str(message)},
        )

    @Slot(str, object)
    def _deliver_event(self, event_name: str, payload: object) -> None:
        if self._shutdown:
            return
        data = payload if isinstance(payload, dict) else {}
        if event_name == "refresh_callback_all":
            self.sync()
            failed = int(data.get("failed", 0) or 0)
            success = int(data.get("success", 0) or 0)
            title = "Aggiornamento completato con errori" if failed else "Aggiornamento completato"
            message = f"{success} riusciti, {failed} falliti" if failed else f"{success} feed aggiornati"
            self.toastRequested.emit(title, message, failed > 0)
            return
        if event_name == "refresh_callback_feed":
            self.sync()
            if not bool(data.get("success", False)):
                self.toastRequested.emit("Aggiornamento feed fallito", str(data.get("message", "")), True)
            return
        if event_name == "refresh_state_changed":
            self._refresh_state = dict(data)
            self.refreshChanged.emit()
            if not bool(data.get("active", False)):
                self.sync()
            return
        if event_name == "config_changed":
            self._unread_only = bool(self._controller.settings.show_unread_only)
            self._articles.set_filter(self._search_query, self._unread_only)
            self._preferences.sync()
            self.filterChanged.emit()
            self.scopeChanged.emit()
            return
        if event_name == "new_items_available":
            source_id = str(data.get("source_id", ""))
            items = data.get("items", [])
            count = len(items) if isinstance(items, list) else 0
            title = source_id
            try:
                title = self._controller.get_feed(source_id).title or source_id
            except Exception:
                logger.debug(
                    "Titolo feed non disponibile per %s",
                    source_id,
                    exc_info=True,
                )
            if count:
                self.newItemsDetected.emit(count, title)
            self._sync_navigation()
            return
        if event_name in {
            "feed_added",
            "feed_removed",
            "feed_updated",
            "feed_refresh_completed",
            "feed_refresh_failed",
            "feed_refresh_cancelled",
        }:
            self._sync_navigation()
            if event_name == "feed_refresh_failed":
                self.toastRequested.emit(
                    "Feed non aggiornato",
                    str(data.get("error", "Errore di rete")),
                    True,
                )

    @staticmethod
    def _normalize_url(raw: str) -> str:
        value = (raw or "").strip()
        if not value:
            raise ValueError("Inserisci un URL")
        if "://" not in value:
            value = "https://" + value
        parsed = urlparse(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Inserisci un URL HTTP o HTTPS valido")
        return value

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._site_icons.shutdown()
        self._controller.unregister_event_listener(self._relay_controller_event)


__all__ = ["OpenExternalPort", "UiController"]
