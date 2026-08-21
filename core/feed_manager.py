"""Gestore centrale dei feed: aggiunta, rimozione, refresh e persistenza."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
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
from core.feed_fetcher import FeedFetchResult, fetch_and_parse_resolved
from core.feed_serializer import deserialize_source, serialize_source
from core.models import FeedItem, FeedSource

logger = logging.getLogger(__name__)


class FeedManager:
    """Catalogo centrale delle sorgenti feed, thread-safe tramite RLock."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self._path: Path = storage_path or Paths.FEEDS_FILE
        self._sources: dict[str, FeedSource] = {}
        self._lock = threading.RLock()
        self._bus = EventBus()
        Paths.ensure_user_dirs()
        self.load()

    def load(self) -> None:
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
                    source = deserialize_source(src_data)
                    self._sources[source.id] = source
                except (KeyError, TypeError, ValueError) as exc:
                    logger.warning("Feed ignorato (dati non validi): %s", exc)

    def save(self) -> None:
        """Persiste lo snapshot corrente serializzando anche la scrittura.

        Con refresh concorrenti più worker possono terminare quasi insieme.
        Il lock resta quindi acquisito fino alla fine di ``write_text`` per
        impedire scritture JSON sovrapposte sullo stesso file.
        """
        try:
            with self._lock:
                data = {
                    "sources": [serialize_source(s) for s in self._sources.values()]
                }
                self._path.write_text(
                    json.dumps(data, indent=2, default=str), encoding="utf-8"
                )
        except OSError as exc:
            logger.error("Impossibile salvare i feed: %s", exc)

    def add(self, url: str, title: str = "") -> FeedSource:
        normalized = url.strip()
        if not normalized:
            raise FeedError("URL vuoto non valido")
        with self._lock:
            for src in self._sources.values():
                if src.url == normalized:
                    raise FeedDuplicateError(normalized)
            source = FeedSource(url=normalized, title=title or normalized)
            self._sources[source.id] = source
        self.save()
        self._bus.emit(
            "feed_added",
            {"source_id": source.id, "url": source.url, "title": source.title},
        )
        logger.info("Feed aggiunto: %s", normalized)
        return source

    def remove(self, source_id: str) -> None:
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            removed = self._sources.pop(source_id)
        self.save()
        self._bus.emit(
            "feed_removed", {"source_id": source_id, "url": removed.url}
        )
        logger.info("Feed rimosso: %s", removed.url)

    def get(self, source_id: str) -> FeedSource:
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            return self._sources[source_id]

    def get_all(self) -> list[FeedSource]:
        with self._lock:
            return list(self._sources.values())

    @staticmethod
    def _normalize_fetch_result(raw: Any, requested_url: str) -> FeedFetchResult:
        """Accetta anche i vecchi tuple mock usati dai test/integrazioni."""
        if isinstance(raw, FeedFetchResult):
            return raw
        title, items, resolved_url = raw
        return FeedFetchResult(title, items, resolved_url or requested_url)

    def _clear_validators(self, source: FeedSource) -> None:
        with self._lock:
            current = self._sources.get(source.id)
            if current is not None:
                current.http_etag = ""
                current.http_last_modified = ""

    def _fetch_effective_url(
        self, source: FeedSource, url: str
    ) -> FeedFetchResult:
        """Fetch dell'URL effettivo; se i validator falliscono, retry pieno."""
        kwargs: dict[str, str] = {}
        if source.http_etag:
            kwargs["etag"] = source.http_etag
        if source.http_last_modified:
            kwargs["last_modified"] = source.http_last_modified
        try:
            raw = fetch_and_parse_resolved(url, source.id, **kwargs)
            return self._normalize_fetch_result(raw, url)
        except (FeedFetchError, FeedParseError):
            if not kwargs:
                raise
            logger.info(
                "Richiesta condizionale fallita per %s; riprovo senza validator",
                url,
            )
            self._clear_validators(source)
            self.save()
            raw = fetch_and_parse_resolved(url, source.id)
            return self._normalize_fetch_result(raw, url)

    def _fetch_source(self, source: FeedSource) -> FeedFetchResult:
        """Usa prima il feed risolto cached, poi fallback all'URL originale."""
        cached_url = source.resolved_feed_url.strip()
        if cached_url:
            try:
                logger.debug("Uso feed cached per %s: %s", source.url, cached_url)
                return self._fetch_effective_url(source, cached_url)
            except (FeedFetchError, FeedParseError) as exc:
                logger.info(
                    "Feed cached non più valido per %s (%s); rifaccio discovery",
                    source.url,
                    exc,
                )
                with self._lock:
                    current = self._sources.get(source.id)
                    if current is not None:
                        current.resolved_feed_url = ""
                        current.http_etag = ""
                        current.http_last_modified = ""
                self.save()
        return self._fetch_effective_url(source, source.url)

    def _store_fetch_metadata(
        self, source: FeedSource, result: FeedFetchResult
    ) -> None:
        new_cached = (
            result.resolved_url
            if result.resolved_url and result.resolved_url != source.url
            else ""
        )
        source.resolved_feed_url = new_cached
        source.http_etag = result.etag
        source.http_last_modified = result.last_modified

    def refresh(self, source_id: str) -> int:
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            source = self._sources[source_id]

        self._bus.emit(
            "feed_refresh_started", {"source_id": source_id, "url": source.url}
        )
        try:
            result = self._fetch_source(source)
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

        if result.not_modified:
            with self._lock:
                self._store_fetch_metadata(source, result)
                source.last_updated = datetime.now(timezone.utc)
                source.last_error = ""
            self.save()
            self._emit_refresh_completed(source_id, source, [], not_modified=True)
            logger.info("Feed %s non modificato (HTTP 304)", source.url)
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=FeedDefaults.MAX_ITEM_AGE_HOURS
        )
        visible_items = [
            it for it in result.items if it.published >= cutoff
        ][: FeedDefaults.MAX_ITEMS_PER_FEED]

        with self._lock:
            if not source.title or source.title == source.url:
                source.title = result.title
            self._store_fetch_metadata(source, result)
            brand_new = source.replace_items(visible_items)

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
        """Aggiorna i feed abilitati con un pool concorrente limitato.

        Il callback di progresso viene invocato dal thread coordinatore dopo
        ogni future completata, quindi ``completed`` cresce sempre da 1 a N
        anche se l'ordine dei feed terminati è diverso da quello iniziale.
        """
        with self._lock:
            sources = [s for s in self._sources.values() if s.enabled]
        total = len(sources)
        if total == 0:
            return {"success": 0, "failed": 0, "errors": []}

        max_workers = min(FeedDefaults.REFRESH_MAX_WORKERS, total)
        success = 0
        errors: list[str] = []
        completed = 0

        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="feed-refresh",
        ) as executor:
            future_to_source: dict[Future[int], FeedSource] = {
                executor.submit(self.refresh, source.id): source
                for source in sources
            }
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    future.result()
                    success += 1
                except FeedError as exc:
                    errors.append(f"{source.url}: {exc}")
                except Exception as exc:
                    logger.error(
                        "Errore inatteso durante refresh di %s: %s",
                        source.url,
                        exc,
                        exc_info=True,
                    )
                    errors.append(f"{source.url}: {exc}")
                finally:
                    completed += 1
                    if progress_cb:
                        try:
                            progress_cb(source.id, completed, total)
                        except Exception as exc:
                            logger.error(
                                "Callback progresso refresh fallita: %s",
                                exc,
                                exc_info=True,
                            )

        return {"success": success, "failed": len(errors), "errors": errors}

    def mark_read(self, source_id: str, item_id: str) -> None:
        with self._lock:
            source = self._sources.get(source_id)
            if not source:
                raise FeedNotFoundError(source_id)
            source.mark_read(item_id)
        self.save()
        self._bus.emit(
            "item_read_changed",
            {"source_id": source_id, "item_id": item_id, "read": True},
        )

    def rename_feed(self, source_id: str, new_title: str) -> FeedSource:
        from core.feed_write_ops import rename_feed
        return rename_feed(self, source_id, new_title)

    def set_category(self, source_id: str, category: str) -> FeedSource:
        from core.feed_write_ops import set_category
        return set_category(self, source_id, category)

    def get_categories(self) -> list[str]:
        from core.category_ops import list_categories
        return list_categories(self)

    def get_feeds_by_category(self, category: str) -> list[FeedSource]:
        from core.category_ops import get_feeds_by_category
        return get_feeds_by_category(self, category)

    def get_items_by_category(self, category: str, limit: int = 200) -> list[FeedItem]:
        from core.category_ops import get_items_by_category
        return get_items_by_category(self, category, limit)

    def get_all_items(self, limit: int = 200) -> list[FeedItem]:
        from core.category_ops import get_all_items
        return get_all_items(self, limit)

    def _emit_refresh_completed(
        self,
        source_id: str,
        source: FeedSource,
        brand_new: list[FeedItem],
        *,
        not_modified: bool = False,
    ) -> None:
        self._bus.emit(
            "feed_refresh_completed",
            {
                "source_id": source_id,
                "url": source.url,
                "title": source.title,
                "new_count": len(brand_new),
                "total_count": len(source.items),
                "not_modified": not_modified,
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
