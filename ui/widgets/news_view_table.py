"""Popolamento della tabella articoli in ``NewsView``.

Estratto da ``news_view.py`` per rispettare il limite di 300 righe
per file (§5.1.3).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QTableWidgetItem, QTableWidget

from config.theme import ThemeColors
from core.models import FeedItem

if TYPE_CHECKING:
    from ui.widgets.news_view import NewsView

logger = logging.getLogger(__name__)


def _format_date(dt: datetime) -> str:
    """Formatta la data in stile italiano ``gg/mm/aaaa``."""
    return dt.strftime("%d/%m/%Y")


def _format_time(dt: datetime) -> str:
    """Formatta l'ora in stile italiano ``HH:MM``."""
    return dt.strftime("%H:%M")


def populate_table(
    owner: "NewsView",
    items: list[FeedItem],
    source_titles: dict[str, str] | None = None,
) -> None:
    """Riempie la tabella articoli con la lista fornita.

    Args:
        owner: Istanza ``NewsView``.
        items: Lista articoli (più recenti per primi).
        source_titles: Mappa ``source_id -> nome visualizzato`` per la
            colonna Sorgente. Se None o mancante, cade su ``source_id``.
    """
    table: QTableWidget = owner._table  # type: ignore[attr-defined]
    table.setRowCount(len(items))
    secondary_brush: QBrush = QBrush(QColor(ThemeColors.TEXT_SECONDARY))
    titles: dict[str, str] = source_titles or {}
    # Allineamento centrato per colonne numeriche Data/Ora (migliora
    # la leggibilità di date e orari corti come "29/07/2026" e "19:44").
    center_align: Qt.AlignmentFlag = (
        Qt.AlignmentFlag.AlignCenter
    )
    # Chiave UserRole+1 con la coppia (source_id, item_id) impostata su
    # tutte le colonne, così item_activated viene emesso anche cliccando
    # su Ora, Sorgente o Titolo, non solo su Data.
    pair: tuple[str, str] = ("", "")
    for row, item in enumerate(items):
        pair = (item.source_id, item.id)
        source_name: str = titles.get(item.source_id, item.source_id)
        # Colonna Data (allineata al centro)
        date_item: QTableWidgetItem = QTableWidgetItem(
            _format_date(item.published)
        )
        date_item.setTextAlignment(center_align)
        date_item.setData(Qt.ItemDataRole.UserRole, item.id)
        date_item.setData(Qt.ItemDataRole.UserRole + 1, pair)
        date_item.setToolTip(
            f"{item.title}\n{item.author}\n"
            f"{_format_date(item.published)} {_format_time(item.published)}"
        )
        if item.read:
            date_item.setForeground(secondary_brush)
        table.setItem(row, owner.COL_DATE, date_item)  # type: ignore[attr-defined]

        # Colonna Ora (allineata al centro)
        time_item: QTableWidgetItem = QTableWidgetItem(
            _format_time(item.published)
        )
        time_item.setTextAlignment(center_align)
        time_item.setData(Qt.ItemDataRole.UserRole, item.id)
        time_item.setData(Qt.ItemDataRole.UserRole + 1, pair)
        if item.read:
            time_item.setForeground(secondary_brush)
        table.setItem(row, owner.COL_TIME, time_item)  # type: ignore[attr-defined]

        # Colonna Sorgente (nome personalizzato dall'utente, allineata a sinistra)
        source_item: QTableWidgetItem = QTableWidgetItem(source_name)
        source_item.setData(Qt.ItemDataRole.UserRole, item.id)
        source_item.setData(Qt.ItemDataRole.UserRole + 1, pair)
        source_item.setToolTip(source_name)
        if item.read:
            source_item.setForeground(secondary_brush)
        table.setItem(row, owner.COL_SOURCE, source_item)  # type: ignore[attr-defined]

        # Colonna Titolo (allineata a sinistra, default)
        title_item: QTableWidgetItem = QTableWidgetItem(item.title)
        title_item.setData(Qt.ItemDataRole.UserRole, item.id)
        title_item.setData(Qt.ItemDataRole.UserRole + 1, pair)
        title_item.setToolTip(item.title)
        if item.read:
            title_item.setForeground(secondary_brush)
        table.setItem(row, owner.COL_TITLE, title_item)  # type: ignore[attr-defined]


def format_date(dt: datetime) -> str:
    """Versione pubblica di _format_date (per test)."""
    return _format_date(dt)


def format_time(dt: datetime) -> str:
    """Versione pubblica di _format_time (per test)."""
    return _format_time(dt)


__all__ = ["populate_table", "format_date", "format_time"]
