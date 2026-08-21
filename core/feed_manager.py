"""Gestore centrale dei feed: aggiunta, rimozione, refresh, persistenza.

Mantiene lo stato delle sorgenti in memoria e lo persiste in JSON nella
directory XDG. Emette eventi tramite ``EventBus``. Serializzazione in
``feed_serializer``, scritture in ``feed_write_ops``, letture aggregate
in ``category_ops`` (split per il limite di 300 righe per file §5.1.3).
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config.constants import FeedDefaults, Paths
from core.event_bus import EventBus
from core.exceptions import (
    FeedDuplicateError,
    FeedError,
    FeedFetchError,
    FeedNotFoundError,
    FeedParseError,
)
from core.feed_fetcher import fetch_and_parse
from core.feed_serializer import deserialize_source, serialize_source
from core.models import FeedItem, FeedSource

logger = logging.getLogger(__name__)


class FeedManager:
    """Catalogo centrale delle sorgenti feed.

    Thread-safe tramite RLock. Le scritture emettono eventi sull'event
    bus; le letture restituiscono copie difensive.
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """Inizializza il manager.

        Args:
            storage_path: Percorso file JSON; default ``Paths.FEEDS_FILE``.
        """
        self._path: Path = storage_path or Paths.FEEDS_FILE
        self._sources: dict[str, FeedSource] = {}
        self._lock: threading.RLock = threading.RLock()
        self._bus: EventBus = EventBus()
        Paths.ensure_user_dirs()
        self.load()

    def load(self) -> None:
        """Carica le sorgenti feed da disco."""
        if not self._path.exists():
            logger.info("File feed non trovato, raccolta vuota: %s", self._path)
            return
        try:
            raw: dict[str, Any] = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("File feed corrotto, raccolta vuota: %s", exc)
            return
        with self._lock:
            self._sources.clear()
            for src_data in raw.get("sources", []):
                try:
                    source: FeedSource = deserialize_source(src_data)
                    self._sources[source.id] = source
                except (KeyError, TypeError, ValueError) as exc:
                    logger.warning("Feed ignorato (dati non validi): %s", exc)

    def save(self) -> None:
        """Persiste le sorgenti su disco."""
        try:
            with self._lock:
                data: dict[str, Any] = {
                    "sources": [
                        serialize_source(s) for s in self._sources.values()
                    ]
                }
            self._path.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("Impossibile salvare i feed: %s", exc)

    def add(self, url: str, title: str = "") -> FeedSource:
        """Aggiunge una nuova sorgente feed.

        Raises:
            FeedDuplicateError: Se l'URL esiste già.
            FeedError: Se l'URL è vuoto.
        """
        normalized: str = url.strip()
        if not normalized:
            raise FeedError("URL vuoto non valido")
        with self._lock:
            for src in self._sources.values():
                if src.url == normalized:
                    raise FeedDuplicateError(normalized)
            source: FeedSource = FeedSource(url=normalized, title=title or normalized)
            self._sources[source.id] = source
        self.save()
        self._bus.emit(
            "feed_added",
            {"source_id": source.id, "url": source.url, "title": source.title},
        )
        logger.info("Feed aggiunto: %s", normalized)
        return source

    def remove(self, source_id: str) -> None:
        """Rimuove una sorgente per ID.

        Raises:
            FeedNotFoundError: Se l'ID non esiste.
        """
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            removed: FeedSource = self._sources.pop(source_id)
        self.save()
        self._bus.emit(
            "feed_removed",
            {"source_id": source_id, "url": removed.url},
        )
        logger.info("Feed rimosso: %s", removed.url)

    def get(self, source_id: str) -> FeedSource:
        """Restituisce una sorgente per ID."""
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            return self._sources[source_id]

    def get_all(self) -> list[FeedSource]:
        """Restituisce tutte le sorgenti (copia difensiva)."""
        with self._lock:
            return list(self._sources.values())

    def refresh(self, source_id: str) -> int:
        """Aggiorna una singola sorgente (chiamata bloccante).

        Returns:
            Numero di articoli nuovi trovati.
        """
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            source: FeedSource = self._sources[source_id]

        self._bus.emit(
            "feed_refresh_started",
            {"source_id": source_id, "url": source.url},
        )
        try:
            feed_title, items = fetch_and_parse(source.url, source_id)
        except (FeedFetchError, FeedParseError) as exc:
            with self._lock:
                src = self._sources.get(source_id)
                if src:
                    src.last_error = str(exc)
            self._bus.emit(
                "feed_refresh_failed",
                {"source_id": source_id, "error": str(exc)},
            )
            logger.error("Refresh fallito per %s: %s", source.url, exc)
            raise

        # Filtra prima del confronto con gli item già memorizzati. Gli
        # articoli fuori dalla finestra visibile vengono potati localmente;
        # confrontarli prima del pruning li farebbe risultare "nuovi" ad ogni
        # refresh successivo, generando notifiche duplicate.
        cutoff: datetime = datetime.now(timezone.utc) - timedelta(
            hours=FeedDefaults.MAX_ITEM_AGE_HOURS
        )
        visible_items: list[FeedItem] = [
            it for it in items if it.published >= cutoff
        ][: FeedDefaults.MAX_ITEMS_PER_FEED]

        with self._lock:
            if not source.title or source.title == source.url:
                source.title = feed_title
            brand_new: list[FeedItem] = source.replace_items(visible_items)

        self.save()
        self._emit_refresh_completed(source_id, source, brand_new)
        logger.info(
            "Feed %s aggiornato: %d nuovi articoli", source.url, len(brand_new)
        )
        return len(brand_new)

    def refresh_all(
        self,
        progress_cb: Callable[[str, int, int], None] | None = None,
    ) -> dict[str, Any]:
        """Aggiorna tutte le sorgenti abilitate.

        Args:
            progress_cb: Callback (source_id, current, total).

        Returns:
            Dict con ``success``, ``failed``, ``errors``.
        """
        with self._lock:
            sources: list[FeedSource] = [
                s for s in self._sources.values() if s.enabled
            ]
        total: int = len(sources)
        success: int = 0
        errors: list[str] = []
        for idx, source in enumerate(sources, start=1):
            if progress_cb:
                progress_cb(source.id, idx, total)
            try:
                self.refresh(source.id)
                success += 1
            except FeedError as exc:
                errors.append(f"{source.url}: {exc}")
        return {"success": success, "failed": len(errors), "errors": errors}

    def mark_read(self, source_id: str, item_id: str) -> None:
        """Marca un articolo come letto."""
        with self._lock:
            source: FeedSource | None = self._sources.get(source_id)
            if not source:
                raise FeedNotFoundError(source_id)
            source.mark_read(item_id)
        self.save()
        self._bus.emit(
            "item_read_changed",
            {"source_id": source_id, "item_id": item_id, "read": True},
        )

    def rename_feed(self, source_id: str, new_title: str) -> FeedSource:
        """Rinomina una sorgente feed.

        Raises:
            FeedNotFoundError: Se l'ID non esiste.
            FeedError: Se il nuovo titolo è vuoto.
        """
        from core.feed_write_ops import rename_feed

        return rename_feed(self, source_id, new_title)

    def set_category(self, source_id: str, category: str) -> FeedSource:
        """Assegna (o rimuove, se vuota) la categoria di una sorgente."""
        from core.feed_write_ops import set_category

        return set_category(self, source_id, category)

    def get_categories(self) -> list[str]:
        """Elenco ordinato delle categorie in uso."""
        from core.category_ops import list_categories
        return list_categories(self)

    def get_feeds_by_category(self, category: str) -> list[FeedSource]:
        """Restituisce le sorgenti assegnate a una categoria."""
        from core.category_ops import get_feeds_by_category
        return get_feeds_by_category(self, category)

    def get_items_by_category(self, category: str, limit: int = 200) -> list[FeedItem]:
        """Articoli aggregati di tutti i feed in una categoria (mega-feed)."""
        from core.category_ops import get_items_by_category
        return get_items_by_category(self, category, limit)

    def get_all_items(self, limit: int = 200) -> list[FeedItem]:
        """Tutti gli articoli di tutte le sorgenti (mega-feed globale)."""
        from core.category_ops import get_all_items
        return get_all_items(self, limit)

    def _emit_refresh_completed(
        self,
        source_id: str,
        source: FeedSource,
        brand_new: list[FeedItem],
    ) -> None:
        """Emette gli eventi refresh_completed e new_items_available."""
        self._bus.emit(
            "feed_refresh_completed",
            {
                "source_id": source_id,
                "url": source.url,
                "title": source.title,
                "new_count": len(brand_new),
                "total_count": len(source.items),
            },
        )
        if brand_new:
            self._bus.emit(
                "new_items_available",
                {
                    "source_id": source_id,
                    "items": [
                        {"id": it.id, "title": it.title, "link": it.link}
                        for it in brand_new
                    ],
                },
            )


__all__ = ["FeedManager"]
