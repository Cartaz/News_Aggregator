"""Helper di refresh della vista articoli per ``MainWindow``.

Estratto da ``main_window.py`` per rispettare il limite di 300 righe
per file (§5.1.3). Contiene i metodi che leggono gli articoli dal
controller e li passano a ``NewsView`` con la mappa ``source_titles``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.exceptions import FeedError
from core.models import FeedItem, FeedSource

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def _build_source_titles(window: "MainWindow") -> dict[str, str]:
    """Costruisce la mappa ``source_id -> nome visualizzato``.

    Usa il titolo personalizzato dall'utente (``source.title``) se
    presente, altrimenti l'URL. Mai il titolo estratto dal sito.

    Args:
        window: Finestra principale.

    Returns:
        Dizionario source_id -> titolo.
    """
    titles: dict[str, str] = {}
    for src in window._controller.get_all_feeds():  # type: ignore[attr-defined]
        titles[src.id] = src.title or src.url
    return titles


def refresh_by_source(
    window: "MainWindow", source_id: str | None
) -> None:
    """Aggiorna la vista articoli per la sorgente indicata.

    Args:
        window: Finestra principale.
        source_id: ID della sorgente; None per svuotare la vista.
    """
    items: list[FeedItem]
    if source_id is None:
        items = []
    else:
        try:
            source: FeedSource = window._controller.get_feed(source_id)  # type: ignore[attr-defined]
            items = list(source.items)
        except FeedError:
            items = []
    titles: dict[str, str] = _build_source_titles(window)
    window._news_view.set_items(items, titles)  # type: ignore[attr-defined]


def refresh_all(window: "MainWindow") -> None:
    """Mostra il mega-feed con tutti gli articoli di tutte le sorgenti."""
    items: list[FeedItem] = window._controller.get_all_items(limit=500)  # type: ignore[attr-defined]
    titles: dict[str, str] = _build_source_titles(window)
    window._news_view.set_items(items, titles)  # type: ignore[attr-defined]


def refresh_by_category(
    window: "MainWindow", category: str
) -> None:
    """Mostra gli articoli aggregati di una categoria.

    Args:
        window: Finestra principale.
        category: Nome categoria; stringa vuota = senza categoria.
    """
    items: list[FeedItem] = []
    if category:
        items = window._controller.get_items_by_category(category, limit=500)  # type: ignore[attr-defined]
    else:
        # "Senza categoria": articoli dei feed senza categoria
        sources: list[FeedSource] = window._controller.get_all_feeds()  # type: ignore[attr-defined]
        for src in sources:
            if not src.category:
                items.extend(src.items)
        items.sort(key=lambda it: it.published, reverse=True)
        items = items[:500]
    titles: dict[str, str] = _build_source_titles(window)
    window._news_view.set_items(items, titles)  # type: ignore[attr-defined]


__all__ = ["refresh_by_source", "refresh_all", "refresh_by_category"]
