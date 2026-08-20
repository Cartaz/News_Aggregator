"""Helper per marcare una riga della tabella articoli come letta.

Estratto da ``news_view.py`` per rispettare il limite di 300 righe
per file (§5.1.3).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QTableWidgetItem

from config.theme import ThemeColors
from core.models import FeedItem

if TYPE_CHECKING:
    from ui.widgets.news_view import NewsView

logger = logging.getLogger(__name__)


def mark_item_read(owner: "NewsView", item_id: str) -> None:
    """Cambia il colore della riga di un articolo marcato come letto.

    Aggiorna anche lo stato interno ``FeedItem.read`` della cache
    ``_items``, così la riga appare in colore secondary (grigio)
    come gli altri articoli già letti.

    Args:
        owner: Istanza ``NewsView``.
        item_id: ID dell'articolo da marcare come letto.
    """
    # Aggiorna lo stato interno della cache
    for idx, it in enumerate(owner._items):  # type: ignore[attr-defined]
        if it.id == item_id and not it.read:
            owner._items[idx] = FeedItem(  # type: ignore[attr-defined]
                id=it.id,
                source_id=it.source_id,
                title=it.title,
                link=it.link,
                summary=it.summary,
                published=it.published,
                author=it.author,
                read=True,
            )
            break
    # Aggiorna il colore della riga nella tabella
    secondary_brush: QBrush = QBrush(QColor(ThemeColors.TEXT_SECONDARY))
    table = owner._table  # type: ignore[attr-defined]
    for row in range(table.rowCount()):
        for col in (owner.COL_DATE, owner.COL_TIME, owner.COL_SOURCE, owner.COL_TITLE):  # type: ignore[attr-defined]
            cell: QTableWidgetItem | None = table.item(row, col)
            if not cell:
                continue
            cell_id: str | None = cell.data(0x100)  # Qt.ItemDataRole.UserRole
            if cell_id == item_id:
                cell.setForeground(secondary_brush)


__all__ = ["mark_item_read"]
