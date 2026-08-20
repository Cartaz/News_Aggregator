"""Operazioni su categorie e mega-feed.

Estratto da ``feed_manager.py`` per rispettare il limite di 300 righe
per file (§5.1.3). Contiene le funzioni pure che operano su ``FeedManager``
per gestire categorie, raggruppamenti e mega-feed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from config.constants import FeedDefaults
from core.models import FeedItem, FeedSource

if TYPE_CHECKING:
    from core.feed_manager import FeedManager

logger = logging.getLogger(__name__)


def _age_cutoff() -> datetime:
    """Restituisce il timestamp di cutoff per gli articoli da mostrare."""
    return datetime.now(timezone.utc) - timedelta(
        hours=FeedDefaults.MAX_ITEM_AGE_HOURS
    )


def list_categories(manager: "FeedManager") -> list[str]:
    """Restituisce l'elenco ordinato delle categorie in uso.

    Args:
        manager: Istanza di ``FeedManager``.

    Returns:
        Lista di nomi di categoria ordinati alfabeticamente.
    """
    with manager._lock:  # type: ignore[attr-defined]
        cats: set[str] = {
            s.category for s in manager._sources.values() if s.category  # type: ignore[attr-defined]
        }
    return sorted(cats)


def get_feeds_by_category(
    manager: "FeedManager", category: str
) -> list[FeedSource]:
    """Restituisce tutte le sorgenti assegnate a una categoria.

    Args:
        manager: Istanza di ``FeedManager``.
        category: Nome della categoria.

    Returns:
        Lista di sorgenti (copia difensiva).
    """
    with manager._lock:  # type: ignore[attr-defined]
        return [
            s for s in manager._sources.values() if s.category == category  # type: ignore[attr-defined]
        ]


def get_items_by_category(
    manager: "FeedManager", category: str, limit: int = 200
) -> list[FeedItem]:
    """Restituisce gli articoli aggregati di tutti i feed in una categoria.

    Args:
        manager: Istanza di ``FeedManager``.
        category: Nome della categoria.
        limit: Numero massimo di articoli (più recenti per primi).

    Returns:
        Lista di articoli ordinati per data di pubblicazione decrescente,
        filtrati per età <= ``FeedDefaults.MAX_ITEM_AGE_HOURS``.
    """
    items: list[FeedItem] = []
    cutoff: datetime = _age_cutoff()
    with manager._lock:  # type: ignore[attr-defined]
        for source in manager._sources.values():  # type: ignore[attr-defined]
            if source.category == category:
                items.extend(
                    it for it in source.items if it.published >= cutoff
                )
    items.sort(key=lambda it: it.published, reverse=True)
    return items[:limit]


def get_all_items(
    manager: "FeedManager", limit: int = 200
) -> list[FeedItem]:
    """Restituisce tutti gli articoli di tutte le sorgenti (mega-feed).

    Args:
        manager: Istanza di ``FeedManager``.
        limit: Numero massimo di articoli (più recenti per primi).

    Returns:
        Lista di articoli ordinati per data di pubblicazione decrescente,
        filtrati per età <= ``FeedDefaults.MAX_ITEM_AGE_HOURS``.
    """
    items: list[FeedItem] = []
    cutoff: datetime = _age_cutoff()
    with manager._lock:  # type: ignore[attr-defined]
        for source in manager._sources.values():  # type: ignore[attr-defined]
            items.extend(
                it for it in source.items if it.published >= cutoff
            )
    items.sort(key=lambda it: it.published, reverse=True)
    return items[:limit]


__all__ = [
    "list_categories",
    "get_feeds_by_category",
    "get_items_by_category",
    "get_all_items",
]
