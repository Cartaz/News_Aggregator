"""Central feed catalog, refresh orchestration and persistence."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config.constants import FeedDefaults, Paths
from core.exceptions import (
    FeedDuplicateError,
    FeedError,
    FeedFetchError,
    FeedNotFoundError,
    FeedParseError,
    RefreshCancelledError,
)
from core.feed_fetcher import FeedFetchResult, fetch_and_parse_resolved
from core.feed_serializer import deserialize_source, serialize_source
from core.models import FeedItem, FeedSource

logger = logging.getLogger(__name__)

FeedEventSink = Callable[[str, dict[str, Any]], None]


def _invalidates_cached_url(exc: FeedFetchError | FeedParseError) -> bool:
    """Only a gone URL or non-feed content justifies a new discovery."""
    if isinstance(exc, FeedParseError):
        return True
    return exc.status_code in {404, 410}


class FeedManager:
    """Own feed storage, locking, persistence and feed-level mutations.

    Persistence has two speeds. Catalog edits the user makes (add, remove,
    rename/categorize) are transactional: written to disk before they become
    visible, so a disk error is reported to the user. High-frequency changes
    (refresh results, read state) are applied in memory, marked dirty and
    written once by a short debounced flush, after a whole refresh batch, or
    on ``close()``. A crash can lose at most the last few seconds of those.
    """

    def __init__(
        self,
        storage_path: Path | None = None,
        event_sink: FeedEventSink | None = None,
        *,
        flush_delay: float = 2.0,
    ) -> None:
        self._path = storage_path or Paths.FEEDS_FILE
        self._sources: dict[str, FeedSource] = {}
        self._source_epochs: dict[str, int] = {}
        self._next_source_epoch = 0
        self._max_items_per_feed = FeedDefaults.MAX_ITEMS_PER_FEED
        self._lock = threading.RLock()
        # Serializes writers of the catalog file (one temporary file path).
        self._write_lock = threading.Lock()
        self._event_sink = event_sink
        self._flush_delay = max(0.0, float(flush_delay))
        self._dirty_generation = 0
        self._persisted_generation = 0
        self._flush_timer: threading.Timer | None = None
        self._batch_depth = 0
        self._closed = False
        self.load()

    def set_max_items_per_feed(self, limit: int) -> None:
        """Apply the validated storage limit to subsequent refreshes."""
        if type(limit) is not int or not 1 <= limit <= FeedDefaults.MAX_SUPPORTED_ITEMS_PER_FEED:
            raise ValueError("Limite articoli per feed non valido")
        with self._lock:
            self._max_items_per_feed = limit

    @staticmethod
    def _snapshot_source(source: FeedSource) -> FeedSource:
        """Return a detached source snapshot without exposing canonical lists."""
        return replace(source, items=list(source.items))

    def _snapshot_catalog_locked(self) -> dict[str, FeedSource]:
        """Copy the canonical catalog while the caller owns ``_lock``."""
        return {
            source_id: self._snapshot_source(source)
            for source_id, source in self._sources.items()
        }

    def _mark_dirty_locked(self) -> None:
        """Record an in-memory change that the next flush must write."""
        self._dirty_generation += 1

    def _schedule_flush(self) -> None:
        """Debounce one background flush unless a batch will flush at its end."""
        with self._lock:
            if (
                self._closed
                or self._batch_depth
                or self._flush_timer is not None
                or self._dirty_generation == self._persisted_generation
            ):
                return
            timer = threading.Timer(self._flush_delay, self._flush_in_background)
            timer.daemon = True
            self._flush_timer = timer
        timer.start()

    def _flush_in_background(self) -> None:
        with self._lock:
            self._flush_timer = None
        try:
            self.flush()
        except FeedError:
            # State stays dirty: the next change, batch end or close() retries.
            logger.exception("Salvataggio differito dei feed non riuscito")

    def flush(self) -> None:
        """Write pending in-memory changes, if any. Raises ``FeedError``."""
        with self._write_lock:
            with self._lock:
                generation = self._dirty_generation
                if generation == self._persisted_generation:
                    return
                catalog = self._snapshot_catalog_locked()
            self._persist_catalog(catalog)
            with self._lock:
                self._persisted_generation = max(self._persisted_generation, generation)

    def close(self) -> None:
        """Stop deferred writes and persist everything still pending."""
        with self._lock:
            self._closed = True
            timer = self._flush_timer
            self._flush_timer = None
        if timer is not None:
            timer.cancel()
        try:
            self.flush()
        except FeedError:
            logger.exception("Salvataggio finale dei feed non riuscito")

    @property
    def has_pending_changes(self) -> bool:
        with self._lock:
            return self._dirty_generation != self._persisted_generation

    @staticmethod
    def _age_cutoff() -> datetime:
        return datetime.now(timezone.utc) - timedelta(
            hours=FeedDefaults.MAX_ITEM_AGE_HOURS
        )

    @staticmethod
    def _raise_if_cancelled(cancel_event: threading.Event | None) -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise RefreshCancelledError()

    def _allocate_source_epoch(self) -> int:
        self._next_source_epoch += 1
        return self._next_source_epoch

    def _source_is_current(self, source_id: str, epoch: int) -> bool:
        return source_id in self._sources and self._source_epochs.get(source_id) == epoch

    def set_event_sink(self, event_sink: FeedEventSink | None) -> None:
        """Set the single explicit sink for domain events."""
        self._event_sink = event_sink

    def _emit_event(self, event_name: str, payload: dict[str, Any]) -> None:
        sink = self._event_sink
        if sink is None:
            return
        try:
            sink(event_name, payload)
        except Exception:
            logger.exception("Errore nel consumer evento feed %s", event_name)

    def load(self) -> None:
        if not self._path.exists():
            logger.info("File feed non trovato, raccolta vuota: %s", self._path)
            return
        try:
            raw: Any = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            logger.warning("File feed corrotto o non leggibile, raccolta invariata: %s", exc)
            return
        if not isinstance(raw, dict):
            logger.warning("File feed con struttura non valida: root non oggetto")
            return
        raw_sources = raw.get("sources", [])
        if not isinstance(raw_sources, list):
            logger.warning("File feed con struttura non valida: sources non lista")
            return
        with self._lock:
            loaded: dict[str, FeedSource] = {}
            loaded_epochs: dict[str, int] = {}
            for src_data in raw_sources:
                try:
                    source = deserialize_source(src_data)
                    loaded[source.id] = source
                    loaded_epochs[source.id] = self._allocate_source_epoch()
                except (KeyError, TypeError, ValueError) as exc:
                    logger.warning("Feed ignorato (dati non validi): %s", exc)
            self._sources = loaded
            self._source_epochs = loaded_epochs

    def _persist_catalog(self, catalog: dict[str, FeedSource]) -> None:
        """Atomically stream one detached catalog without holding the state lock."""
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write('{"sources":[')
                for index, source in enumerate(catalog.values()):
                    if index:
                        handle.write(",")
                    json.dump(
                        serialize_source(source),
                        handle,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        default=str,
                    )
                handle.write("]}")
            temporary.replace(self._path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logger.debug("Impossibile rimuovere feed temporanei", exc_info=True)
            raise FeedError(f"Impossibile salvare i feed: {exc}") from exc

    def save(self) -> None:
        """Persist the whole current catalog now, pending changes included."""
        with self._write_lock:
            with self._lock:
                generation = self._dirty_generation
                catalog = self._snapshot_catalog_locked()
            self._persist_catalog(catalog)
            with self._lock:
                self._persisted_generation = max(self._persisted_generation, generation)

    def _persist_transaction(self, catalog: dict[str, FeedSource], generation: int) -> None:
        """Write a candidate catalog taken at ``generation`` (caller owns write lock)."""
        self._persist_catalog(catalog)
        with self._lock:
            self._persisted_generation = max(self._persisted_generation, generation)

    def add(self, url: str, title: str = "") -> FeedSource:
        normalized = url.strip()
        if not normalized:
            raise FeedError("URL vuoto non valido")

        with self._write_lock:
            with self._lock:
                for existing in self._sources.values():
                    if existing.url == normalized:
                        raise FeedDuplicateError(normalized)
                generation = self._dirty_generation
                candidate = self._snapshot_catalog_locked()

            source = FeedSource(url=normalized, title=title or normalized)
            candidate[source.id] = self._snapshot_source(source)
            self._persist_transaction(candidate, generation)

            with self._lock:
                self._sources[source.id] = source
                self._source_epochs[source.id] = self._allocate_source_epoch()
                snapshot = self._snapshot_source(source)

        self._emit_event(
            "feed_added",
            {"source_id": source.id, "url": source.url, "title": source.title},
        )
        logger.info("Feed aggiunto: %s", normalized)
        return snapshot

    def remove(self, source_id: str) -> None:
        with self._write_lock:
            with self._lock:
                if source_id not in self._sources:
                    raise FeedNotFoundError(source_id)
                generation = self._dirty_generation
                candidate = self._snapshot_catalog_locked()
                removed = candidate.pop(source_id)

            self._persist_transaction(candidate, generation)

            with self._lock:
                self._sources.pop(source_id, None)
                self._source_epochs.pop(source_id, None)

        self._emit_event(
            "feed_removed",
            {"source_id": source_id, "url": removed.url},
        )
        logger.info("Feed rimosso: %s", removed.url)

    def get(self, source_id: str) -> FeedSource:
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            return self._snapshot_source(self._sources[source_id])

    def get_all(self) -> list[FeedSource]:
        with self._lock:
            return [self._snapshot_source(source) for source in self._sources.values()]

    def _fetch_effective_url(
        self,
        source: FeedSource,
        url: str,
        cancel_event: threading.Event | None,
    ) -> FeedFetchResult:
        try:
            return fetch_and_parse_resolved(
                url,
                source.id,
                etag=source.http_etag,
                last_modified=source.http_last_modified,
                cancel_event=cancel_event,
            )
        except RefreshCancelledError:
            raise
        except (FeedFetchError, FeedParseError) as exc:
            if not source.http_etag and not source.http_last_modified:
                raise
            if isinstance(exc, FeedFetchError) and exc.is_transient:
                # Network trouble says nothing about the validators.
                raise
            logger.info(
                "Richiesta condizionale fallita per %s; riprovo senza validator",
                url,
            )
            source.http_etag = ""
            source.http_last_modified = ""
            self._raise_if_cancelled(cancel_event)
            return self._fetch_effective_url(source, url, cancel_event)

    def _fetch_source(
        self,
        source: FeedSource,
        cancel_event: threading.Event | None,
    ) -> FeedFetchResult:
        cached_url = source.resolved_feed_url.strip()
        if cached_url:
            try:
                logger.debug("Uso feed cached per %s: %s", source.url, cached_url)
                return self._fetch_effective_url(source, cached_url, cancel_event)
            except RefreshCancelledError:
                raise
            except (FeedFetchError, FeedParseError) as exc:
                if not _invalidates_cached_url(exc):
                    raise
                logger.info(
                    "Feed cached non più valido per %s (%s); rifaccio discovery",
                    source.url,
                    exc,
                )
                source.resolved_feed_url = ""
                source.http_etag = ""
                source.http_last_modified = ""
        self._raise_if_cancelled(cancel_event)
        return self._fetch_effective_url(source, source.url, cancel_event)

    @staticmethod
    def _store_fetch_metadata(source: FeedSource, result: FeedFetchResult) -> None:
        source.resolved_feed_url = (
            result.resolved_url
            if result.resolved_url and result.resolved_url != source.url
            else ""
        )
        source.http_etag = result.etag
        source.http_last_modified = result.last_modified

    def _commit_refresh_result(
        self,
        source_id: str,
        epoch: int,
        result: FeedFetchResult,
        visible_items: list[FeedItem] | None,
        cancel_event: threading.Event | None,
    ) -> tuple[FeedSource, list[FeedItem], bool] | None:
        """Commit one fetch result; return snapshot, new items and first-fetch flag."""
        self._raise_if_cancelled(cancel_event)

        with self._lock:
            if not self._source_is_current(source_id, epoch):
                return None
            current = self._snapshot_source(self._sources[source_id])
            first_fetch = current.last_updated is None
            if result.not_modified:
                persisted_metadata = (
                    current.resolved_feed_url,
                    current.http_etag,
                    current.http_last_modified,
                )
                self._store_fetch_metadata(current, result)
                current.last_updated = datetime.now(timezone.utc)
                current.last_error = ""
                brand_new: list[FeedItem] = []
                # A 304 is worth writing only if the cache validators moved.
                changed = persisted_metadata != (
                    current.resolved_feed_url,
                    current.http_etag,
                    current.http_last_modified,
                )
            else:
                if not current.title or current.title == current.url:
                    current.title = result.title
                self._store_fetch_metadata(current, result)
                brand_new = current.replace_items(visible_items or [])
                changed = True

            self._sources[source_id] = current
            if changed:
                self._mark_dirty_locked()
            committed = self._snapshot_source(current)

        self._schedule_flush()
        return committed, brand_new, first_fetch

    def refresh(
        self,
        source_id: str,
        cancel_event: threading.Event | None = None,
    ) -> int:
        self._raise_if_cancelled(cancel_event)
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            source = self._snapshot_source(self._sources[source_id])
            epoch = self._source_epochs[source_id]

        self._emit_event(
            "feed_refresh_started",
            {"source_id": source_id, "url": source.url},
        )
        try:
            result = self._fetch_source(source, cancel_event)
            self._raise_if_cancelled(cancel_event)
        except RefreshCancelledError:
            self._emit_event(
                "feed_refresh_cancelled",
                {"source_id": source_id, "url": source.url},
            )
            raise
        except (FeedFetchError, FeedParseError) as exc:
            with self._lock:
                stale = not self._source_is_current(source_id, epoch)
                if not stale:
                    current = self._snapshot_source(self._sources[source_id])
                    current.last_error = str(exc)
                    self._sources[source_id] = current
            if stale:
                self._emit_event(
                    "feed_refresh_cancelled",
                    {"source_id": source_id, "url": source.url},
                )
                raise RefreshCancelledError() from exc
            self._emit_event(
                "feed_refresh_failed",
                {"source_id": source_id, "error": str(exc)},
            )
            logger.error("Refresh fallito per %s: %s", source.url, exc)
            raise

        visible_items: list[FeedItem] | None = None
        if not result.not_modified:
            cutoff = self._age_cutoff()
            with self._lock:
                limit = self._max_items_per_feed
            visible_items = sorted(
                (item for item in result.items if item.published >= cutoff),
                key=lambda item: item.published,
                reverse=True,
            )[:limit]

        try:
            committed = self._commit_refresh_result(
                source_id,
                epoch,
                result,
                visible_items,
                cancel_event,
            )
        except RefreshCancelledError:
            self._emit_event(
                "feed_refresh_cancelled",
                {"source_id": source_id, "url": source.url},
            )
            raise
        if committed is None:
            self._emit_event(
                "feed_refresh_cancelled",
                {"source_id": source_id, "url": source.url},
            )
            raise RefreshCancelledError()

        committed_source, brand_new, first_fetch = committed
        self._emit_refresh_completed(
            source_id,
            committed_source,
            brand_new,
            not_modified=result.not_modified,
            announce_new_items=not first_fetch,
        )
        if result.not_modified:
            logger.info("Feed %s non modificato (HTTP 304)", committed_source.url)
            return 0
        logger.info(
            "Feed %s aggiornato: %d nuovi articoli",
            committed_source.url,
            len(brand_new),
        )
        return len(brand_new)

    def refresh_all(
        self,
        progress_cb: Callable[[str, int, int], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            sources = [
                self._snapshot_source(source)
                for source in self._sources.values()
                if source.enabled
            ]
        total = len(sources)
        if total == 0:
            return {"success": 0, "failed": 0, "errors": []}

        with self._lock:
            self._batch_depth += 1
        try:
            return self._refresh_batch(sources, progress_cb, cancel_event)
        finally:
            with self._lock:
                self._batch_depth -= 1
            try:
                self.flush()
            except FeedError:
                logger.exception("Salvataggio dei feed dopo l'aggiornamento non riuscito")

    def _refresh_batch(
        self,
        sources: list[FeedSource],
        progress_cb: Callable[[str, int, int], None] | None,
        cancel_event: threading.Event | None,
    ) -> dict[str, Any]:
        total = len(sources)
        max_workers = min(FeedDefaults.REFRESH_MAX_WORKERS, total)
        success = 0
        cancelled = 0
        errors: list[str] = []
        completed = 0

        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="feed-refresh",
        ) as executor:
            future_to_source: dict[Future[int], FeedSource] = {}
            for source in sources:
                future = executor.submit(self.refresh, source.id, cancel_event)
                future_to_source[future] = source

            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    future.result()
                    success += 1
                except RefreshCancelledError:
                    cancelled += 1
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
                        except Exception:
                            logger.exception("Callback progresso refresh fallita")

        result: dict[str, Any] = {
            "success": success,
            "failed": len(errors),
            "errors": errors,
        }
        if cancelled:
            result["cancelled"] = cancelled
        return result

    def mark_read(self, source_id: str, item_id: str) -> None:
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            source = self._snapshot_source(self._sources[source_id])
            if not source.mark_read(item_id):
                raise FeedError(f"Articolo non trovato: {item_id}")
            self._sources[source_id] = source
            self._mark_dirty_locked()
        self._schedule_flush()

        self._emit_event(
            "item_read_changed",
            {"source_id": source_id, "item_id": item_id, "read": True},
        )

    def update_feed(self, source_id: str, title: str, category: str) -> FeedSource:
        """Atomically update editable feed metadata and persist it once."""
        cleaned_title = (title or "").strip()
        cleaned_category = (category or "").strip()
        if not cleaned_title:
            raise FeedError("Il nuovo titolo non può essere vuoto")

        with self._write_lock:
            with self._lock:
                if source_id not in self._sources:
                    raise FeedNotFoundError(source_id)
                generation = self._dirty_generation
                candidate = self._snapshot_catalog_locked()
                source = candidate[source_id]

            source.title = cleaned_title
            source.category = cleaned_category
            self._persist_transaction(candidate, generation)

            with self._lock:
                # Re-read: a refresh may have committed new items meanwhile.
                current = self._snapshot_source(self._sources[source_id])
                current.title = cleaned_title
                current.category = cleaned_category
                self._sources[source_id] = current
                snapshot = self._snapshot_source(current)

        self._emit_event(
            "feed_updated",
            {
                "source_id": source_id,
                "title": cleaned_title,
                "category": cleaned_category,
            },
        )
        logger.info(
            "Feed %s aggiornato: titolo=%r categoria=%r",
            source_id,
            cleaned_title,
            cleaned_category or "(nessuna)",
        )
        return snapshot

    def get_categories(self) -> list[str]:
        with self._lock:
            return sorted(
                {source.category for source in self._sources.values() if source.category}
            )

    def total_unread_count(self) -> int:
        """Count unread items inside the visible age window without copying."""
        cutoff = self._age_cutoff()
        with self._lock:
            return sum(
                1
                for source in self._sources.values()
                for item in source.items
                if not item.read and item.published >= cutoff
            )

    def get_items_for_feed(self, source_id: str, limit: int = 200) -> list[FeedItem]:
        cutoff = self._age_cutoff()
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            items = [
                item for item in self._sources[source_id].items if item.published >= cutoff
            ]
        items.sort(key=lambda item: item.published, reverse=True)
        return items[:limit]

    def get_items_by_category(
        self, category: str, limit: int = 200
    ) -> list[FeedItem]:
        cutoff = self._age_cutoff()
        with self._lock:
            items = [
                item
                for source in self._sources.values()
                if source.category == category
                for item in source.items
                if item.published >= cutoff
            ]
        items.sort(key=lambda item: item.published, reverse=True)
        return items[:limit]

    def get_all_items(self, limit: int = 200) -> list[FeedItem]:
        cutoff = self._age_cutoff()
        with self._lock:
            items = [
                item
                for source in self._sources.values()
                for item in source.items
                if item.published >= cutoff
            ]
        items.sort(key=lambda item: item.published, reverse=True)
        return items[:limit]

    def _emit_refresh_completed(
        self,
        source_id: str,
        source: FeedSource,
        brand_new: list[FeedItem],
        *,
        not_modified: bool = False,
        announce_new_items: bool = True,
    ) -> None:
        self._emit_event(
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
        # The first fetch of a feed fills an empty source: those items are the
        # initial catalog, not news worth a desktop notification.
        if brand_new and announce_new_items:
            self._emit_event(
                "new_items_available",
                {
                    "source_id": source_id,
                    "items": [
                        {"id": item.id, "title": item.title, "link": item.link}
                        for item in brand_new
                    ],
                },
            )


__all__ = ["FeedManager", "FeedEventSink"]
