"""Helper per inizializzazione eventi e stato iniziale di ``MainWindow``.

Estratto da ``main_window.py`` per rispettare il limite di 300 righe
per file (§5.1.3).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget

from core.models import FeedSource
from ui.widgets.status_indicator import StatusIndicator

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def subscribe_events(window: "MainWindow") -> None:
    """Iscrive gli handler Qt-safe dell'EventBus per la finestra.

    Args:
        window: Finestra principale.
    """
    from ui.main_window_handlers import MainWindowHandlers

    h = MainWindowHandlers
    bridge = window._bridge  # type: ignore[attr-defined]
    bridge.subscribe("feed_added", lambda d: h.on_feed_added(window, d))
    bridge.subscribe("feed_removed", lambda d: h.on_feed_removed(window, d))
    bridge.subscribe(
        "feed_refresh_started", lambda d: h.on_refresh_started(window, d)
    )
    bridge.subscribe(
        "feed_refresh_completed", lambda d: h.on_refresh_completed(window, d)
    )
    bridge.subscribe(
        "feed_refresh_failed", lambda d: h.on_refresh_failed(window, d)
    )
    bridge.subscribe(
        "new_items_available", lambda d: h.on_new_items(window, d)
    )
    bridge.subscribe(
        "item_read_changed", lambda d: h.on_item_read(window, d)
    )
    bridge.subscribe(
        "feed_renamed", lambda d: h.on_feed_renamed(window, d)
    )
    bridge.subscribe(
        "feed_category_changed",
        lambda d: h.on_feed_category_changed(window, d),
    )


def load_initial_state(window: "MainWindow") -> None:
    """Carica feed e categorie dal controller all'avvio.

    Args:
        window: Finestra principale.
    """
    sources: list[FeedSource] = window._controller.get_all_feeds()  # type: ignore[attr-defined]
    categories: list[str] = window._controller.get_categories()  # type: ignore[attr-defined]
    window._source_list.set_sources(sources, categories)  # type: ignore[attr-defined]
    # All'avvio mostra il mega-feed "Tutti gli articoli"
    window._refresh_news_view_all()  # type: ignore[attr-defined]
    window._set_status("Pronto", StatusIndicator.State.STOPPED)  # type: ignore[attr-defined]


__all__ = ["subscribe_events", "load_initial_state"]
