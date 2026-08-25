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
            for src_data in raw_sources:
                try:
                    source = deserialize_source(src_data)
                    loaded[source.id] = source
                except (KeyError, TypeError, ValueError) as exc:
                    logger.warning("Feed ignorato (dati non validi): %s", exc)
            self._sources = loaded

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
            self._sources[source.id] = source
        try:
            self.save()
        except Exception:
            with self._lock:
                self._sources.pop(source.id, None)
            raise
        self._emit_event(
            "feed_added",
            {"source_id": source.id, "url": source.url, "title": source.title},
        )
        logger.info("Feed aggiunto: %s", normalized)
        return self._snapshot_source(source)

    def remove(self, source_id: str) -> None:
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            removed = self._sources.pop(source_id)
        try:
            self.save()
        except Exception:
            with self._lock:
                self._sources[source_id] = removed
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

    def _clear_validators(self, source: FeedSource) -> None:
        with self._lock:
            current = self._sources.get(source.id)
            if current is not None:
                current.http_etag = ""
                current.http_last_modified = ""

    def _fetch_effective_url(
        self, source: FeedSource, url: str
    ) -> FeedFetchResult:
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

    @staticmethod
    def _store_fetch_metadata(source: FeedSource, result: FeedFetchResult) -> None:
        source.resolved_feed_url = (
            result.resolved_url
            if result.resolved_url and result.resolved_url != source.url
            else ""
        )
        source.http_etag = result.etag
        source.http_last_modified = result.last_modified

    def _restore_source(self, source_id: str, snapshot: FeedSource) -> None:
        with self._lock:
            self._sources[source_id] = snapshot

    def refresh(self, source_id: str) -> int:
        with self._lock:
            if source_id not in self._sources:
                raise FeedNotFoundError(source_id)
            source = self._sources[source_id]

        self._emit_event(
            "feed_refresh_started",
            {"source_id": source_id, "url": source.url},
        )
        try:
            result = self._fetch_source(source)
        except (FeedFetchError, FeedParseError) as exc:
            with self._lock:
                current = self._sources.get(source_id)
                if current:
                    current.last_error = str(exc)
            self._emit_event(
                "feed_refresh_failed",
                {"source_id": source_id, "error": str(exc)},
            )
            logger.error("Refresh fallito per %s: %s", source.url, exc)
            raise

        previous = self._snapshot_source(source)
        if result.not_modified:
            with self._lock:
                self._store_fetch_metadata(source, result)
                source.last_updated = datetime.now(timezone.utc)
                source.last_error = ""
            try:
                self.save()
            except Exception:
                self._restore_source(source_id, previous)
                raise
            self._emit_refresh_completed(source_id, source, [], not_modified=True)
            logger.info("Feed %s non modificato (HTTP 304)", source.url)
            return 0

        cutoff = self._age_cutoff()
        visible_items = [
            item for item in result.items if item.published >= cutoff
        ][: FeedDefaults.MAX_ITEMS_PER_FEED]

        with self._lock:
            if not source.title or source.title == source.url:
                source.title = result.title
            self._store_fetch_metadata(source, result)
            brand_new = source.replace_items(visible_items)

        try:
            self.save()
        except Exception:
            self._restore_source(source_id, previous)
            raise
        self._emit_refresh_completed(source_id, source, brand_new)
        logger.info(
            "Feed %s aggiornato: %d nuovi articoli", source.url, len(brand_new)
        )
        return len(brand_new)

    def refresh_all(
        self,
        progress_cb: Callable[[str, int, int], None] | None = None,
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
                        except Exception:
                            logger.exception("Callback progresso refresh fallita")

        return {"success": success, "failed": len(errors), "errors": errors}

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