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


class FeedManager:
    """Own feed storage, locking, persistence and feed-level mutations."""

    def __init__(
        self,
        storage_path: Path | None = None,
        event_sink: FeedEventSink | None = None,
    ) -> None:
        self._path = storage_path or Paths.FEEDS_FILE
        self._sources: dict[str, FeedSource] = {}
        self._source_epochs: dict[str, int] = {}
        self._next_source_epoch = 0
        self._lock = threading.RLock()
        self._event_sink = event_sink
        Paths.ensure_user_dirs()
        self.load()

    @staticmethod
    def _snapshot_source(source: FeedSource) -> FeedSource:
        """Return a detached source snapshot without exposing canonical lists."""
        return replace(source, items=list(source.items))

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
        return (
            source_id in self._sources
            and self._source_epochs.get(source_id) == epoch
        )

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
        except (OSError, json.JSONDecodeError) as exc:
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

    def save(self) -> None:
        """Atomically persist one locked snapshot or raise ``FeedError``."""
        Paths.ensure_user_dirs()
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        try:
            with self._lock:
                data = {
                    "sources": [serialize_source(source) for source in self._sources.values()]
                }
                temporary.write_text(
                    json.dumps(data, indent=2, default=str),
                    encoding="utf-8",
                )
                temporary.replace(self._path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logger.debug("Impossibile rimuovere feed temporanei", exc_info=True)
            raise FeedError(f"Impossibile salvare i feed: {exc}") from exc

    def add(self, url: str, title: str = "") -> FeedSource:
        normalized = url.strip()
        if not normalized:
            raise FeedError("URL vuoto non valido")
        with self._lock:
            for existing in self._sources.values():
                if existing.url == normalized:
                    raise FeedDuplicateError(normalized)
            source = FeedSource(url=normalized, title=title or normalized)
            epoch = self._allocate_source_epoch()
            self._sources[source.id] = source
            self._source_epochs[source.id] = epoch
            try:
                self.save()
            except Exception:
                self._sources.pop(source.id, None)
                self._source_epochs.pop(source.id, None)
                raise
            snapshot = self._snapshot_source(source)
        self._emit_event(
            "feed_added",
            {"source_id": source.id, "url": source.url, "title": source.title},
        )
        logger.info("Feed aggiunto: %s", normalized)
        return snapshot

    def remove(self, source_id: str) -> None:
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            removed = self._sources.pop(source_id)
            removed_epoch = self._source_epochs.pop(source_id)
            try:
                self.save()
            except Exception:
                self._sources[source_id] = removed
                self._source_epochs[source_id] = removed_epoch
                raise
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

    @staticmethod
    def _normalize_fetch_result(raw: Any, requested_url: str) -> FeedFetchResult:
        if isinstance(raw, FeedFetchResult):
            return raw
        title, items, resolved_url = raw
        return FeedFetchResult(title, items, resolved_url or requested_url)

    def _fetch_effective_url(
        self,
        source: FeedSource,
        url: str,
        cancel_event: threading.Event | None,
    ) -> FeedFetchResult:
        try:
            kwargs: dict[str, Any] = {}
            if source.http_etag:
                kwargs["etag"] = source.http_etag
            if source.http_last_modified:
                kwargs["last_modified"] = source.http_last_modified
            if cancel_event is not None:
                kwargs["cancel_event"] = cancel_event
            raw = fetch_and_parse_resolved(url, source.id, **kwargs)
            return self._normalize_fetch_result(raw, url)
        except RefreshCancelledError:
            raise
        except (FeedFetchError, FeedParseError):
            if not source.http_etag and not source.http_last_modified:
                raise
            logger.info(
                "Richiesta condizionale fallita per %s; riprovo senza validator",
                url,
            )
            source.http_etag = ""
            source.http_last_modified = ""
            self._raise_if_cancelled(cancel_event)
            if cancel_event is None:
                raw = fetch_and_parse_resolved(url, source.id)
            else:
                raw = fetch_and_parse_resolved(
                    url,
                    source.id,
                    cancel_event=cancel_event,
                )
            return self._normalize_fetch_result(raw, url)

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
    ) -> tuple[FeedSource, list[FeedItem]] | None:
        self._raise_if_cancelled(cancel_event)
        with self._lock:
            if not self._source_is_current(source_id, epoch):
                return None
            current = self._sources[source_id]
            previous = self._snapshot_source(current)
            try:
                if result.not_modified:
                    self._store_fetch_metadata(current, result)
                    current.last_updated = datetime.now(timezone.utc)
                    current.last_error = ""
                    brand_new: list[FeedItem] = []
                else:
                    if not current.title or current.title == current.url:
                        current.title = result.title
                    self._store_fetch_metadata(current, result)
                    brand_new = current.replace_items(visible_items or [])
                self.save()
            except Exception:
                self._sources[source_id] = previous
                raise
            committed = self._snapshot_source(current)
        return committed, brand_new

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
                if not self._source_is_current(source_id, epoch):
                    self._emit_event(
                        "feed_refresh_cancelled",
                        {"source_id": source_id, "url": source.url},
                    )
                    raise RefreshCancelledError() from exc
                self._sources[source_id].last_error = str(exc)
            self._emit_event(
                "feed_refresh_failed",
                {"source_id": source_id, "error": str(exc)},
            )
            logger.error("Refresh fallito per %s: %s", source.url, exc)
            raise

        visible_items: list[FeedItem] | None = None
        if not result.not_modified:
            cutoff = self._age_cutoff()
            visible_items = [
                item for item in result.items if item.published >= cutoff
            ][: FeedDefaults.MAX_ITEMS_PER_FEED]

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

        committed_source, brand_new = committed
        self._emit_refresh_completed(
            source_id,
            committed_source,
            brand_new,
            not_modified=result.not_modified,
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
                if cancel_event is None:
                    future = executor.submit(self.refresh, source.id)
                else:
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
            source = self._sources.get(source_id)
            if not source:
                raise FeedNotFoundError(source_id)
            previous_items = list(source.items)
            changed = source.mark_read(item_id)
            if not changed:
                raise FeedError(f"Articolo non trovato: {item_id}")
        try:
            self.save()
        except Exception:
            with self._lock:
                source.items = previous_items
            raise
        self._emit_event(
            "item_read_changed",
            {"source_id": source_id, "item_id": item_id, "read": True},
        )

    def rename_feed(self, source_id: str, new_title: str) -> FeedSource:
        cleaned = (new_title or "").strip()
        if not cleaned:
            raise FeedError("Il nuovo titolo non può essere vuoto")
        with self._lock:
            source = self._sources.get(source_id)
            if not source:
                raise FeedNotFoundError(source_id)
            previous = source.title
            source.title = cleaned
        try:
            self.save()
        except Exception:
            with self._lock:
                source.title = previous
            raise
        self._emit_event(
            "feed_renamed",
            {"source_id": source_id, "new_title": cleaned},
        )
        logger.info("Feed %s rinominato in %r", source_id, cleaned)
        return self._snapshot_source(source)

    def set_category(self, source_id: str, category: str) -> FeedSource:
        cleaned = (category or "").strip()
        with self._lock:
            source = self._sources.get(source_id)
            if not source:
                raise FeedNotFoundError(source_id)
            previous = source.category
            source.category = cleaned
        try:
            self.save()
        except Exception:
            with self._lock:
                source.category = previous
            raise
        self._emit_event(
            "feed_category_changed",
            {"source_id": source_id, "category": cleaned},
        )
        logger.info(
            "Feed %s assegnato a categoria %r",
            source_id,
            cleaned or "(nessuna)",
        )
        return self._snapshot_source(source)

    def get_categories(self) -> list[str]:
        with self._lock:
            return sorted(
                {source.category for source in self._sources.values() if source.category}
            )

    def get_feeds_by_category(self, category: str) -> list[FeedSource]:
        with self._lock:
            return [
                self._snapshot_source(source)
                for source in self._sources.values()
                if source.category == category
            ]

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
        if brand_new:
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
