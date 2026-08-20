"""Controller principale: facade verso l'UI per operazioni sui feed.

Questo modulo è l'unico punto di contatto tra il livello UI e il livello
core. Espone metodi sincroni (chiamabili dall'UI nel thread principale)
ed metodi asincroni tramite un worker thread interno per le operazioni
di rete.

Il controller è framework-agnostic: NON importa Qt. Le notifiche verso
l'UI avvengono esclusivamente tramite l'event bus.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from config.constants import AppMeta, FeedDefaults, Paths
from config.settings import Settings, SettingsManager
from core.event_bus import EventBus
from core.exceptions import FeedError
from core.feed_manager import FeedManager
from core.models import FeedItem, FeedSource

logger = logging.getLogger(__name__)


class AppController:
    """Facade singleton per le operazioni dell'applicazione.

    Mantiene riferimenti a FeedManager e SettingsManager. Espone API
    sincrona (add/remove/get) e asincrona (refresh in worker thread).
    """

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
        self._feed_manager: FeedManager = feed_manager or FeedManager()
        self._settings_manager: SettingsManager = (
            settings_manager or SettingsManager()
        )
        self._bus: EventBus = EventBus()
        self._refresh_thread: threading.Thread | None = None
        self._refresh_lock: threading.Lock = threading.Lock()
        self._auto_timer: threading.Timer | None = None
        self._initialized: bool = True
        # Registra callback per propagare config_changed su EventBus
        # (config/ non può importare EventBus, lo facciamo qui nel core)
        self._settings_manager.register_change_callback(self._on_settings_changed)
        logger.info("%s controller inizializzato", AppMeta.NAME)

    def _on_settings_changed(self, settings: Settings) -> None:
        """Propaga il cambiamento impostazioni sull'EventBus.

        Args:
            settings: Nuovo snapshot delle impostazioni.
        """
        from dataclasses import asdict

        self._bus.emit(
            "config_changed",
            {"source": AppMeta.NAME, "settings": asdict(settings)},
        )

    @property
    def feed_manager(self) -> FeedManager:
        """Restituisce l'istanza del FeedManager."""
        return self._feed_manager

    @property
    def settings(self) -> Settings:
        """Restituisce le impostazioni correnti."""
        return self._settings_manager.settings

    @property
    def settings_manager(self) -> SettingsManager:
        """Restituisce il SettingsManager."""
        return self._settings_manager

    def add_feed(self, url: str, title: str = "") -> FeedSource:
        """Aggiunge un feed (sincrono).

        Raises:
            FeedError: Se l'aggiunta fallisce.
        """
        return self._feed_manager.add(url, title)

    def remove_feed(self, source_id: str) -> None:
        """Rimuove un feed per ID."""
        self._feed_manager.remove(source_id)

    def get_feed(self, source_id: str) -> FeedSource:
        """Restituisce un feed per ID."""
        return self._feed_manager.get(source_id)

    def get_all_feeds(self) -> list[FeedSource]:
        """Restituisce tutti i feed."""
        return self._feed_manager.get_all()

    def get_recent_items(self, limit: int = 100) -> list[FeedItem]:
        """Restituisce gli articoli più recenti (cross-feed)."""
        return self._feed_manager.get_all_items(limit)

    def mark_read(self, source_id: str, item_id: str) -> None:
        """Marca un articolo come letto."""
        self._feed_manager.mark_read(source_id, item_id)

    def rename_feed(self, source_id: str, new_title: str) -> FeedSource:
        """Rinomina una sorgente feed.

        Raises:
            FeedError: Se il titolo è vuoto o la sorgente non esiste.
        """
        return self._feed_manager.rename_feed(source_id, new_title)

    def set_category(self, source_id: str, category: str) -> FeedSource:
        """Assegna o rimuove la categoria di una sorgente."""
        return self._feed_manager.set_category(source_id, category)

    def get_categories(self) -> list[str]:
        """Restituisce l'elenco delle categorie in uso."""
        return self._feed_manager.get_categories()

    def get_feeds_by_category(self, category: str) -> list[FeedSource]:
        """Restituisce i feed di una categoria."""
        return self._feed_manager.get_feeds_by_category(category)

    def get_items_by_category(
        self, category: str, limit: int = 200
    ) -> list[FeedItem]:
        """Restituisce gli articoli aggregati di una categoria (mega-feed)."""
        return self._feed_manager.get_items_by_category(category, limit)

    def get_all_items(self, limit: int = 200) -> list[FeedItem]:
        """Restituisce tutti gli articoli di tutte le sorgenti (mega-feed)."""
        return self._feed_manager.get_all_items(limit)

    def get_total_unread_count(self) -> int:
        """Restituisce il numero totale di articoli non letti (tutti i feed).

        Usa il cutoff di età di ``FeedDefaults.MAX_ITEM_AGE_HOURS`` per
        contare solo gli articoli ancora visibili nella vista (non quelli
        potati dal pruning). Thread-safe.

        Returns:
            Somma di ``FeedSource.unread_count`` su tutti i feed, ma solo
            per gli articoli entro la finestra di età configurata.
        """
        from datetime import datetime, timedelta, timezone

        from config.constants import FeedDefaults

        cutoff: datetime = datetime.now(timezone.utc) - timedelta(
            hours=FeedDefaults.MAX_ITEM_AGE_HOURS
        )
        with self._feed_manager._lock:  # type: ignore[attr-defined]
            total: int = 0
            for source in self._feed_manager._sources.values():  # type: ignore[attr-defined]
                total += sum(
                    1
                    for it in source.items
                    if not it.read and it.published >= cutoff
                )
        return total

    def refresh_feed_async(
        self,
        source_id: str,
        on_done: Callable[[bool, str], None] | None = None,
    ) -> None:
        """Aggiorna un singolo feed in background.

        Args:
            source_id: ID del feed da aggiornare.
            on_done: Callback (success, message) eseguita al termine.
        """
        thread: threading.Thread = threading.Thread(
            target=self._refresh_feed_worker,
            args=(source_id, on_done),
            daemon=True,
        )
        thread.start()

    def refresh_all_async(
        self,
        on_done: Callable[[dict[str, Any]], None] | None = None,
        progress_cb: Callable[[str, int, int], None] | None = None,
    ) -> None:
        """Aggiorna tutti i feed abilitati in background.

        Args:
            on_done: Callback con il dict risultato (vedi refresh_all).
            progress_cb: Callback (source_id, current, total).
        """
        with self._refresh_lock:
            if self._refresh_thread and self._refresh_thread.is_alive():
                logger.warning("Refresh già in corso, richiesta ignorata")
                return
            self._refresh_thread = threading.Thread(
                target=self._refresh_all_worker,
                args=(on_done, progress_cb),
                daemon=True,
            )
            self._refresh_thread.start()

    def start_auto_refresh(self) -> None:
        """Avvia il timer di refresh automatico periodico."""
        self._stop_auto_refresh()
        interval: int = self.settings.refresh_interval_minutes * 60
        if interval < 30:
            # Soglia di sicurezza: sotto 30s il traffico di rete è eccessivo.
            interval = FeedDefaults.REFRESH_INTERVAL_SECONDS
        self._auto_timer = threading.Timer(interval, self._on_auto_refresh)
        self._auto_timer.daemon = True
        self._auto_timer.start()
        logger.info("Auto-refresh schedulato ogni %d secondi", interval)

    def stop_auto_refresh(self) -> None:
        """Ferma il timer di refresh automatico."""
        self._stop_auto_refresh()

    def _stop_auto_refresh(self) -> None:
        """Implementazione interna di stop timer."""
        if self._auto_timer:
            self._auto_timer.cancel()
            self._auto_timer = None

    def _on_auto_refresh(self) -> None:
        """Callback interna del timer di auto-refresh.

        Rischedula il timer prima di avviare il refresh, così il ciclo
        è periodico (``threading.Timer`` è one-shot).
        """
        logger.info("Auto-refresh triggered")
        # Riavvia il timer per il prossimo ciclo
        self.start_auto_refresh()
        self.refresh_all_async()

    def _refresh_feed_worker(
        self,
        source_id: str,
        on_done: Callable[[bool, str], None] | None,
    ) -> None:
        """Worker thread per refresh di un singolo feed."""
        try:
            new_count: int = self._feed_manager.refresh(source_id)
            if on_done:
                on_done(True, f"{new_count} nuovi articoli")
        except FeedError as exc:
            logger.error("Refresh fallito: %s", exc)
            if on_done:
                on_done(False, str(exc))

    def _refresh_all_worker(
        self,
        on_done: Callable[[dict[str, Any]], None] | None,
        progress_cb: Callable[[str, int, int], None] | None,
    ) -> None:
        """Worker thread per refresh di tutti i feed."""
        try:
            result: dict[str, Any] = self._feed_manager.refresh_all(progress_cb)
            if on_done:
                on_done(result)
        except Exception as exc:
            logger.error("Refresh tutti fallito: %s", exc, exc_info=True)
            if on_done:
                on_done(
                    {"success": 0, "failed": 0, "errors": [str(exc)]}
                )

    def shutdown(self) -> None:
        """Pulisce le risorse prima della chiusura dell'app."""
        self._stop_auto_refresh()
        logger.info("Controller shutdown completato")


__all__ = ["AppController"]
