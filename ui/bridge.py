"""Qt WebChannel bridge between the web UI and the Python application core."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Qt, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices

from config.constants import AppMeta, FeedDefaults, Paths
from config.settings import Settings
from core.app_controller import AppController
from core.event_bus import EventBus
from core.models import FeedItem, FeedSource

logger = logging.getLogger(__name__)


class WebBridge(QObject):
    """Small presentation adapter exposed to JavaScript through QWebChannel."""

    stateChanged = Signal(str)
    backendEvent = Signal(str)
    refreshProgress = Signal(str)
    refreshFinished = Signal(str)
    unreadCountChanged = Signal(int)
    newItemsDetected = Signal(int, str)
    requestQuit = Signal()
    requestHide = Signal()

    _eventRelay = Signal(str)
    _progressRelay = Signal(str)
    _finishRelay = Signal(str)

    _EVENTS = (
        "feed_added",
        "feed_removed",
        "feed_renamed",
        "feed_category_changed",
        "feed_refresh_started",
        "feed_refresh_completed",
        "feed_refresh_failed",
        "new_items_available",
        "item_read_changed",
        "config_changed",
    )

    def __init__(self, controller: AppController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._bus = EventBus()
        self._refresh_lock = threading.Lock()
        self._refreshing_all = False
        self._refreshing_feeds: set[str] = set()
        self._eventRelay.connect(self._deliver_event, Qt.ConnectionType.QueuedConnection)
        self._progressRelay.connect(self.refreshProgress.emit, Qt.ConnectionType.QueuedConnection)
        self._finishRelay.connect(self._deliver_finish, Qt.ConnectionType.QueuedConnection)
        for event_name in self._EVENTS:
            self._bus.subscribe(event_name, self._make_event_handler(event_name))

    def _make_event_handler(self, event_name: str):  # type: ignore[no-untyped-def]
        def handler(payload: dict[str, Any]) -> None:
            self._eventRelay.emit(self._json({"event": event_name, "payload": payload}))

        return handler

    @Slot(str)
    def _deliver_event(self, raw: str) -> None:
        self.backendEvent.emit(raw)
        try:
            event = json.loads(raw)
            event_name = event.get("event", "")
            payload = event.get("payload", {})
            if event_name == "new_items_available":
                source_id = str(payload.get("source_id", ""))
                count = len(payload.get("items", []))
                title = source_id
                try:
                    title = self._controller.get_feed(source_id).title
                except Exception:
                    pass
                if count:
                    self.newItemsDetected.emit(count, title)
            if event_name not in {"feed_refresh_started"}:
                self._emit_state()
        except Exception:
            logger.debug("Impossibile elaborare evento WebChannel", exc_info=True)

    @Slot(str)
    def _deliver_finish(self, raw: str) -> None:
        self.refreshFinished.emit(raw)
        self._emit_state()

    def _emit_state(self) -> None:
        snapshot = self.getSnapshot()
        self.stateChanged.emit(snapshot)
        try:
            self.unreadCountChanged.emit(json.loads(snapshot)["data"]["unreadCount"])
        except Exception:
            pass

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _ok(data: Any = None, message: str = "") -> str:
        return WebBridge._json({"ok": True, "message": message, "data": data})

    @staticmethod
    def _error(exc: Exception | str, *, details: str = "") -> str:
        message = str(exc) or "Operazione non riuscita"
        return WebBridge._json({"ok": False, "message": message, "details": details})

    def _serialize_feed(self, source: FeedSource) -> dict[str, Any]:
        return {
            "id": source.id,
            "url": source.url,
            "title": source.title,
            "enabled": source.enabled,
            "lastUpdated": source.last_updated.isoformat() if source.last_updated else None,
            "lastError": source.last_error,
            "unreadCount": source.unread_count,
            "itemCount": len(source.items),
            "category": source.category,
        }

    def _serialize_item(self, item: FeedItem, source_titles: dict[str, str]) -> dict[str, Any]:
        return {
            "id": item.id,
            "sourceId": item.source_id,
            "sourceTitle": source_titles.get(item.source_id, item.source_id),
            "title": item.title,
            "link": item.link,
            "summary": item.summary,
            "published": item.published.isoformat(),
            "author": item.author,
            "read": item.read,
        }

    @Slot(result=str)
    def getSnapshot(self) -> str:
        try:
            feeds = self._controller.get_all_feeds()
            settings = asdict(self._controller.settings)
            data = {
                "app": {
                    "name": AppMeta.DISPLAY_NAME,
                    "version": AppMeta.VERSION,
                    "description": AppMeta.DESCRIPTION,
                },
                "feeds": [self._serialize_feed(feed) for feed in feeds],
                "categories": self._controller.get_categories(),
                "unreadCount": self._controller.get_total_unread_count(),
                "settings": settings,
                "refreshing": {
                    "all": self._refreshing_all,
                    "feeds": sorted(self._refreshing_feeds),
                },
            }
            return self._ok(data)
        except Exception as exc:
            logger.exception("Snapshot UI non disponibile")
            return self._error(exc)

    @Slot(str, str, int, result=str)
    def getItems(self, scope: str, identifier: str, limit: int = 200) -> str:
        try:
            limit = max(1, min(int(limit), 500))
            if scope == "category":
                items = self._controller.get_items_by_category(identifier, limit)
            elif scope == "feed":
                source = self._controller.get_feed(identifier)
                cutoff = datetime.now(timezone.utc) - timedelta(hours=FeedDefaults.MAX_ITEM_AGE_HOURS)
                items = [item for item in source.items if item.published >= cutoff]
                items.sort(key=lambda item: item.published, reverse=True)
                items = items[:limit]
            else:
                items = self._controller.get_all_items(limit)
            titles = {feed.id: feed.title for feed in self._controller.get_all_feeds()}
            return self._ok([self._serialize_item(item, titles) for item in items])
        except Exception as exc:
            logger.exception("Caricamento articoli fallito")
            return self._error(exc)

    @Slot(str, str, result=str)
    def addFeed(self, url: str, title: str = "") -> str:
        try:
            normalized = self._normalize_url(url)
            source = self._controller.add_feed(normalized, title.strip())
            self.refreshFeed(source.id)
            return self._ok(self._serialize_feed(source), "Feed aggiunto")
        except Exception as exc:
            logger.warning("Aggiunta feed fallita: %s", exc)
            return self._error(exc)

    @Slot(str, result=str)
    def removeFeed(self, source_id: str) -> str:
        try:
            self._controller.remove_feed(source_id)
            return self._ok(message="Feed rimosso")
        except Exception as exc:
            logger.warning("Rimozione feed fallita: %s", exc)
            return self._error(exc)

    @Slot(str, str, result=str)
    def renameFeed(self, source_id: str, title: str) -> str:
        try:
            source = self._controller.rename_feed(source_id, title)
            return self._ok(self._serialize_feed(source), "Feed rinominato")
        except Exception as exc:
            return self._error(exc)

    @Slot(str, str, result=str)
    def setFeedCategory(self, source_id: str, category: str) -> str:
        try:
            source = self._controller.set_category(source_id, category)
            return self._ok(self._serialize_feed(source), "Categoria aggiornata")
        except Exception as exc:
            return self._error(exc)

    @Slot(str, str, result=str)
    def markRead(self, source_id: str, item_id: str) -> str:
        try:
            self._controller.mark_read(source_id, item_id)
            return self._ok(message="Articolo segnato come letto")
        except Exception as exc:
            return self._error(exc)

    @Slot(str, result=str)
    def refreshFeed(self, source_id: str) -> str:
        with self._refresh_lock:
            if self._refreshing_all or source_id in self._refreshing_feeds:
                return self._error("Aggiornamento già in corso")
            self._refreshing_feeds.add(source_id)

        def done(success: bool, message: str) -> None:
            with self._refresh_lock:
                self._refreshing_feeds.discard(source_id)
            self._finishRelay.emit(self._json({
                "scope": "feed",
                "sourceId": source_id,
                "ok": success,
                "message": message,
            }))

        self._controller.refresh_feed_async(source_id, done)
        self._emit_state()
        return self._ok(message="Aggiornamento avviato")

    @Slot(result=str)
    def refreshAll(self) -> str:
        with self._refresh_lock:
            core_thread = getattr(self._controller, "_refresh_thread", None)
            if self._refreshing_all or self._refreshing_feeds or (core_thread and core_thread.is_alive()):
                return self._error("Aggiornamento già in corso")
            self._refreshing_all = True

        def progress(source_id: str, current: int, total: int) -> None:
            self._progressRelay.emit(self._json({
                "sourceId": source_id,
                "current": current,
                "total": total,
            }))

        def done(result: dict[str, Any]) -> None:
            with self._refresh_lock:
                self._refreshing_all = False
            self._finishRelay.emit(self._json({"scope": "all", "ok": result.get("failed", 0) == 0, **result}))

        self._controller.refresh_all_async(done, progress)
        self._emit_state()
        return self._ok(message="Aggiornamento globale avviato")

    @Slot(str, result=str)
    def saveSettings(self, raw: str) -> str:
        try:
            payload = json.loads(raw)
            allowed = {
                "refresh_interval_minutes",
                "mark_read_on_select",
                "show_unread_only",
                "font_scale_factor",
                "notify_new_items",
                "close_to_tray",
            }
            manager = self._controller.settings_manager
            current = manager.settings
            candidate = Settings(**asdict(current))
            old_interval = current.refresh_interval_minutes
            for key, value in payload.items():
                if key in allowed:
                    setattr(candidate, key, value)
            candidate.validate()
            for key in allowed:
                setattr(current, key, getattr(candidate, key))
            manager.save()
            if current.refresh_interval_minutes != old_interval:
                self._controller.start_auto_refresh()
            return self._ok(asdict(current), "Impostazioni salvate")
        except Exception as exc:
            logger.warning("Salvataggio impostazioni fallito: %s", exc)
            return self._error(exc)

    @Slot(int, result=str)
    def setSidebarWidth(self, width: int) -> str:
        try:
            width = max(240, min(int(width), 480))
            settings = self._controller.settings_manager.settings
            settings.source_split_width = width
            self._controller.settings_manager.save()
            return self._ok(width)
        except Exception as exc:
            return self._error(exc)

    @Slot(int, result=str)
    def getLogTail(self, max_lines: int = 250) -> str:
        """Return a bounded tail of the real application log for diagnostics."""
        try:
            max_lines = max(20, min(int(max_lines), 1000))
            if not Paths.LOG_FILE.exists():
                return self._ok({"lines": [], "path": str(Paths.LOG_FILE)})
            lines = Paths.LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            return self._ok({"lines": lines[-max_lines:], "path": str(Paths.LOG_FILE)})
        except Exception as exc:
            logger.warning("Lettura log fallita: %s", exc)
            return self._error(exc)

    @Slot(str, result=str)
    def openExternal(self, raw_url: str) -> str:
        try:
            url = QUrl.fromUserInput(raw_url.strip())
            if not url.isValid() or url.scheme().lower() not in {"http", "https"}:
                return self._error("Link non valido")
            if not QDesktopServices.openUrl(url):
                return self._error("Impossibile aprire il browser")
            return self._ok(message="Link aperto")
        except Exception as exc:
            return self._error(exc)

    @Slot()
    def quitApp(self) -> None:
        self.requestQuit.emit()

    @Slot()
    def hideApp(self) -> None:
        self.requestHide.emit()

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
