"""Qt WebChannel bridge between the web UI and the Python application core."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import asdict
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Qt, Signal, Slot

from config.constants import AppMeta
from core.app_controller import AppController
from core.models import FeedItem, FeedSource

logger = logging.getLogger(__name__)

OpenExternalPort = Callable[[str], tuple[bool, str]]


class WebBridge(QObject):
    """Presentation adapter exposed to JavaScript through QWebChannel."""

    stateChanged = Signal(str)
    backendEvent = Signal(str)
    refreshFinished = Signal(str)
    unreadCountChanged = Signal(int)
    newItemsDetected = Signal(int, str)
    uiSyncRequested = Signal()
    requestQuit = Signal()
    requestHide = Signal()

    _eventRelay = Signal(str)
    _finishRelay = Signal(str)

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
        self._eventRelay.connect(self._deliver_event, Qt.ConnectionType.QueuedConnection)
        self._finishRelay.connect(self._deliver_finish, Qt.ConnectionType.QueuedConnection)
        self._controller.register_event_listener(self._relay_controller_event)

    def _relay_controller_event(
        self,
        event_name: str,
        payload: dict[str, Any],
    ) -> None:
        """Relay controller events into Qt's queued GUI-thread delivery."""
        self._eventRelay.emit(
            self._json({"event": event_name, "payload": payload})
        )

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
                    logger.debug("Titolo feed non disponibile per %s", source_id, exc_info=True)
                if count:
                    self.newItemsDetected.emit(count, title)
            self._emit_state()
        except Exception:
            logger.debug("Impossibile elaborare evento WebChannel", exc_info=True)

    @Slot(str)
    def _deliver_finish(self, raw: str) -> None:
        self.refreshFinished.emit(raw)
        self._emit_state()

    def request_ui_sync(self) -> None:
        """Ask the web view to reload current state/items after becoming visible."""
        self.uiSyncRequested.emit()

    def _emit_state(self) -> None:
        snapshot = self.getSnapshot()
        self.stateChanged.emit(snapshot)
        try:
            self.unreadCountChanged.emit(json.loads(snapshot)["data"]["unreadCount"])
        except (KeyError, TypeError, json.JSONDecodeError):
            logger.debug("Snapshot privo di unreadCount", exc_info=True)

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
            data = {
                "app": {
                    "name": AppMeta.DISPLAY_NAME,
                    "version": AppMeta.VERSION,
                    "description": AppMeta.DESCRIPTION,
                },
                "feeds": [self._serialize_feed(feed) for feed in feeds],
                "categories": self._controller.get_categories(),
                "unreadCount": self._controller.get_total_unread_count(),
                "settings": asdict(self._controller.settings),
                "refreshing": self._controller.get_refresh_state(),
            }
            return self._ok(data)
        except Exception as exc:
            logger.exception("Snapshot UI non disponibile")
            return self._error(exc)

    @Slot(str, str, int, result=str)
    def getItems(self, scope: str, identifier: str, limit: int = 200) -> str:
        try:
            items = self._controller.get_items(scope, identifier, limit)
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
        def done(success: bool, message: str) -> None:
            self._finishRelay.emit(self._json({
                "scope": "feed",
                "sourceId": source_id,
                "ok": success,
                "message": message,
            }))

        if not self._controller.refresh_feed_async(source_id, done):
            return self._error("Aggiornamento già in corso")
        self._emit_state()
        return self._ok(message="Aggiornamento avviato")

    @Slot(result=str)
    def refreshAll(self) -> str:
        def done(result: dict[str, Any]) -> None:
            self._finishRelay.emit(self._json({
                "scope": "all",
                "ok": result.get("failed", 0) == 0,
                **result,
            }))

        if not self._controller.refresh_all_async(done):
            return self._error("Aggiornamento già in corso")
        self._emit_state()
        return self._ok(message="Aggiornamento globale avviato")

    @Slot(str, result=str)
    def saveSettings(self, raw: str) -> str:
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Formato impostazioni non valido")
            allowed = {
                "refresh_interval_minutes",
                "mark_read_on_select",
                "show_unread_only",
                "font_scale_factor",
                "notify_new_items",
                "close_to_tray",
            }
            changes = {key: value for key, value in payload.items() if key in allowed}
            updated = self._controller.update_settings(changes)
            return self._ok(asdict(updated), "Impostazioni salvate")
        except Exception as exc:
            logger.warning("Salvataggio impostazioni fallito: %s", exc)
            return self._error(exc)

    @Slot(int, result=str)
    def setSidebarWidth(self, width: int) -> str:
        try:
            width = max(240, min(int(width), 480))
            updated = self._controller.update_settings({"source_split_width": width})
            return self._ok(updated.source_split_width)
        except Exception as exc:
            return self._error(exc)

    @Slot(int, result=str)
    def getLogTail(self, max_lines: int = 250) -> str:
        try:
            return self._ok(self._controller.get_log_tail(max_lines))
        except Exception as exc:
            logger.warning("Lettura log fallita: %s", exc)
            return self._error(exc)

    @Slot(str, result=str)
    def openExternal(self, raw_url: str) -> str:
        try:
            normalized = self._normalize_url(raw_url)
            if self._open_external is None:
                return self._error("Apertura link non disponibile")
            ok, message = self._open_external(normalized)
            if not ok:
                return self._error(message)
            return self._ok(message=message)
        except Exception as exc:
            logger.warning("Apertura link esterno fallita: %s", exc)
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


__all__ = ["WebBridge", "OpenExternalPort"]
