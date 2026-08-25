"""Application controller and canonical operational state owner.

The controller coordinates feed operations, refresh lifecycle and UI-facing
queries. Presentation layers consume serializable snapshots and do not own
persistent or operational state.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from config.constants import AppMeta, FeedDefaults
from config.settings import Settings, SettingsManager
from core.event_bus import EventBus
from core.exceptions import FeedError
from core.feed_manager import FeedManager
from core.models import FeedItem, FeedSource
from core.refresh_state import RefreshState

logger = logging.getLogger(__name__)


class AppController:
    """Coordinate application services and own refresh lifecycle state."""

    _instance: AppController | None = None

    def __new__(cls, *args: Any, **kwargs: Any) -> AppController:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        feed_manager: FeedManager | None = None,
        settings_manager: SettingsManager | None = None,
    ) -> None:
        if getattr(self, "_initialized", False):
            return
        self._feed_manager = feed_manager or FeedManager()
        self._settings_manager = settings_manager or SettingsManager()
        self._bus = EventBus()
        self._refresh_thread: threading.Thread | None = None
        self._refresh_lock = threading.RLock()
        self._refresh_state = RefreshState()
        self._auto_timer: threading.Timer | None = None
        self._shutting_down = False
        self._initialized = True
        self._settings_manager.register_change_callback(self._on_settings_changed)
        self._bus.subscribe("feed_refresh_started", self._on_feed_refresh_started)
        self._bus.subscribe("feed_refresh_completed", self._on_feed_refresh_finished)
        self._bus.subscribe("feed_refresh_failed", self._on_feed_refresh_finished)
        logger.info("%s controller inizializzato", AppMeta.NAME)

    def _on_settings_changed(self, settings: Settings) -> None:
        from dataclasses import asdict

        self._bus.emit(
            "config_changed",
            {"source": AppMeta.NAME, "settings": asdict(settings)},
        )

    @property
    def feed_manager(self) -> FeedManager:
        return self._feed_manager

    @property
    def settings(self) -> Settings:
        return self._settings_manager.settings

    @property
    def settings_manager(self) -> SettingsManager:
        return self._settings_manager

    def get_refresh_state(self) -> dict[str, Any]:
        """Return a serializable snapshot of refresh state."""
        with self._refresh_lock:
            return self._refresh_state.snapshot()

    def is_refreshing(self) -> bool:
        with self._refresh_lock:
            return self._refresh_state.active

    def _emit_refresh_state(self) -> None:
        self._bus.emit("refresh_state_changed", self.get_refresh_state())

    def _begin_refresh(self, scope: str, total: int, source_id: str = "") -> bool:
        with self._refresh_lock:
            if self._shutting_down or self._refresh_state.active:
                return False
            if scope not in {"all", "feed"}:
                raise ValueError(f"Scope refresh non valido: {scope}")
            self._refresh_state.begin(scope, total, source_id)  # type: ignore[arg-type]
        self._emit_refresh_state()
        return True

    def _set_refresh_progress(self, current: int, total: int) -> None:
        with self._refresh_lock:
            if not self._refresh_state.active:
                return
            self._refresh_state.progress(current, total)
        self._emit_refresh_state()

    def _finish_refresh(self) -> None:
        with self._refresh_lock:
            self._refresh_state.finish()
            self._refresh_thread = None
        self._emit_refresh_state()

    def _on_feed_refresh_started(self, payload: dict[str, Any]) -> None:
        source_id = str(payload.get("source_id", ""))
        with self._refresh_lock:
            if not self._refresh_state.active:
                return
            self._refresh_state.feed_started(source_id)
        self._emit_refresh_state()

    def _on_feed_refresh_finished(self, payload: dict[str, Any]) -> None:
        source_id = str(payload.get("source_id", ""))
        with self._refresh_lock:
            if not self._refresh_state.active:
                return
            self._refresh_state.feed_finished(source_id)
        self._emit_refresh_state()

    def add_feed(self, url: str, title: str = "") -> FeedSource:
        return self._feed_manager.add(url, title)

    def remove_feed(self, source_id: str) -> None:
        self._feed_manager.remove(source_id)

    def get_feed(self, source_id: str) -> FeedSource:
        return self._feed_manager.get(source_id)

    def get_all_feeds(self) -> list[FeedSource]:
        return self._feed_manager.get_all()

    def get_recent_items(self, limit: int = 100) -> list[FeedItem]:
        return self._feed_manager.get_all_items(limit)

    def get_items(
        self,
        scope: str,
        identifier: str,
        limit: int = 200,
    ) -> list[FeedItem]:
        """Return recent items for a UI scope without leaking query rules to UI."""
        limit = max(1, min(int(limit), 500))
        if scope == "category":
            return self._feed_manager.get_items_by_category(identifier, limit)
        if scope == "feed":
            source = self._feed_manager.get(identifier)
            cutoff = datetime.now(timezone.utc) - timedelta(
                hours=FeedDefaults.MAX_ITEM_AGE_HOURS
            )
            items = [item for item in source.items if item.published >= cutoff]
            items.sort(key=lambda item: item.published, reverse=True)
            return items[:limit]
        return self._feed_manager.get_all_items(limit)

    def mark_read(self, source_id: str, item_id: str) -> None:
        self._feed_manager.mark_read(source_id, item_id)

    def rename_feed(self, source_id: str, new_title: str) -> FeedSource:
        return self._feed_manager.rename_feed(source_id, new_title)

    def set_category(self, source_id: str, category: str) -> FeedSource:
        return self._feed_manager.set_category(source_id, category)

    def get_categories(self) -> list[str]:
        return self._feed_manager.get_categories()

    def get_feeds_by_category(self, category: str) -> list[FeedSource]:
        return self._feed_manager.get_feeds_by_category(category)

    def get_items_by_category(
        self, category: str, limit: int = 200
    ) -> list[FeedItem]:
        return self._feed_manager.get_items_by_category(category, limit)

    def get_all_items(self, limit: int = 200) -> list[FeedItem]:
        return self._feed_manager.get_all_items(limit)

    def get_total_unread_count(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=FeedDefaults.MAX_ITEM_AGE_HOURS
        )
        return sum(
            1
            for source in self._feed_manager.get_all()
            for item in source.items
            if not item.read and item.published >= cutoff
        )

    def refresh_feed_async(
        self,
        source_id: str,
        on_done: Callable[[bool, str], None] | None = None,
    ) -> bool:
        """Start one feed refresh; return False when refresh cannot start."""
        if not self._begin_refresh("feed", 1, source_id):
            logger.warning("Refresh singolo non avviato: occupato o shutdown in corso")
            return False
        thread = threading.Thread(
            target=self._refresh_feed_worker,
            args=(source_id, on_done),
            daemon=True,
            name=f"feed-refresh-{source_id[:8]}",
        )
        with self._refresh_lock:
            self._refresh_thread = thread
        thread.start()
        return True

    def refresh_all_async(
        self,
        on_done: Callable[[dict[str, Any]], None] | None = None,
        progress_cb: Callable[[str, int, int], None] | None = None,
    ) -> bool:
        """Start a global refresh; return False when refresh cannot start."""
        total = sum(1 for source in self._feed_manager.get_all() if source.enabled)
        if not self._begin_refresh("all", total):
            logger.warning("Refresh globale non avviato: occupato o shutdown in corso")
            return False
        thread = threading.Thread(
            target=self._refresh_all_worker,
            args=(on_done, progress_cb),
            daemon=True,
            name="feed-refresh-all",
        )
        with self._refresh_lock:
            self._refresh_thread = thread
        thread.start()
        return True

    def start_auto_refresh(self) -> None:
        with self._refresh_lock:
            if self._shutting_down:
                return
        self._stop_auto_refresh()
        interval = self.settings.refresh_interval_minutes * 60
        if interval < 30:
            interval = FeedDefaults.REFRESH_INTERVAL_SECONDS
        timer = threading.Timer(interval, self._on_auto_refresh)
        timer.daemon = True
        with self._refresh_lock:
            if self._shutting_down:
                return
            self._auto_timer = timer
        timer.start()
        logger.info("Auto-refresh schedulato ogni %d secondi", interval)

    def stop_auto_refresh(self) -> None:
        self._stop_auto_refresh()

    def _stop_auto_refresh(self) -> None:
        with self._refresh_lock:
            timer = self._auto_timer
            self._auto_timer = None
        if timer:
            timer.cancel()

    def _on_auto_refresh(self) -> None:
        with self._refresh_lock:
            if self._shutting_down:
                return
        logger.info("Auto-refresh triggered")
        self.start_auto_refresh()
        if not self.refresh_all_async():
            logger.info("Auto-refresh saltato: aggiornamento già in corso")

    def _refresh_feed_worker(
        self,
        source_id: str,
        on_done: Callable[[bool, str], None] | None,
    ) -> None:
        success = False
        message = ""
        try:
            new_count = self._feed_manager.refresh(source_id)
            success = True
            message = f"{new_count} nuovi articoli"
        except FeedError as exc:
            message = str(exc)
            logger.error("Refresh fallito: %s", exc)
        except Exception as exc:
            message = str(exc)
            logger.error("Refresh fallito: %s", exc, exc_info=True)
        finally:
            self._set_refresh_progress(1, 1)
            self._finish_refresh()
        if on_done:
            on_done(success, message)

    def _refresh_all_worker(
        self,
        on_done: Callable[[dict[str, Any]], None] | None,
        progress_cb: Callable[[str, int, int], None] | None,
    ) -> None:
        def tracked_progress(source_id: str, current: int, total: int) -> None:
            self._set_refresh_progress(current, total)
            if progress_cb:
                try:
                    progress_cb(source_id, current, total)
                except Exception:
                    logger.exception("Callback progresso refresh fallita")

        try:
            result = self._feed_manager.refresh_all(tracked_progress)
        except Exception as exc:
            logger.error("Refresh tutti fallito: %s", exc, exc_info=True)
            result = {"success": 0, "failed": 0, "errors": [str(exc)]}
        finally:
            self._finish_refresh()
        if on_done:
            on_done(result)

    def shutdown(self, wait_timeout: float = 2.0) -> None:
        """Stop scheduling and wait a bounded time for the owned refresh worker."""
        with self._refresh_lock:
            if self._shutting_down:
                return
            self._shutting_down = True
            worker = self._refresh_thread
        self._stop_auto_refresh()

        if (
            worker is not None
            and worker.is_alive()
            and worker is not threading.current_thread()
        ):
            worker.join(timeout=max(0.0, wait_timeout))
            if worker.is_alive():
                logger.warning(
                    "Worker refresh ancora attivo dopo %.1f secondi di shutdown",
                    wait_timeout,
                )
        logger.info("Controller shutdown completato")


__all__ = ["AppController"]
