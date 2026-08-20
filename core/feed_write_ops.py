"""Operazioni di scrittura su ``FeedManager``: rename e category.

Estratto da ``feed_manager.py`` per rispettare il limite di 300 righe
per file (§5.1.3).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.event_bus import EventBus
from core.exceptions import FeedError, FeedNotFoundError
from core.models import FeedSource

if TYPE_CHECKING:
    from core.feed_manager import FeedManager

logger = logging.getLogger(__name__)


def rename_feed(
    manager: "FeedManager", source_id: str, new_title: str
) -> FeedSource:
    """Rinomina una sorgente feed.

    Args:
        manager: Istanza di ``FeedManager``.
        source_id: ID della sorgente.
        new_title: Nuovo titolo personalizzato (non vuoto).

    Returns:
        La sorgente aggiornata.

    Raises:
        FeedNotFoundError: Se l'ID non esiste.
        FeedError: Se il nuovo titolo è vuoto.
    """
    cleaned: str = (new_title or "").strip()
    if not cleaned:
        raise FeedError("Il nuovo titolo non può essere vuoto")
    with manager._lock:  # type: ignore[attr-defined]
        source = manager._sources.get(source_id)  # type: ignore[attr-defined]
        if not source:
            raise FeedNotFoundError(source_id)
        source.title = cleaned
    manager.save()  # type: ignore[attr-defined]
    bus: EventBus = EventBus()
    bus.emit(
        "feed_renamed",
        {"source_id": source_id, "new_title": cleaned},
    )
    logger.info("Feed %s rinominato in %r", source_id, cleaned)
    return source


def set_category(
    manager: "FeedManager", source_id: str, category: str
) -> FeedSource:
    """Assegna (o rimuove, se vuota) la categoria di una sorgente.

    Args:
        manager: Istanza di ``FeedManager``.
        source_id: ID della sorgente.
        category: Nome della categoria; stringa vuota per rimuovere.

    Returns:
        La sorgente aggiornata.
    """
    cleaned: str = (category or "").strip()
    with manager._lock:  # type: ignore[attr-defined]
        source = manager._sources.get(source_id)  # type: ignore[attr-defined]
        if not source:
            raise FeedNotFoundError(source_id)
        source.category = cleaned
    manager.save()  # type: ignore[attr-defined]
    bus: EventBus = EventBus()
    bus.emit(
        "feed_category_changed",
        {"source_id": source_id, "category": cleaned},
    )
    logger.info(
        "Feed %s assegnato a categoria %r",
        source_id,
        cleaned or "(nessuna)",
    )
    return source


__all__ = ["rename_feed", "set_category"]
