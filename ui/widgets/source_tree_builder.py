"""Costruzione dell'albero delle sorgenti per ``SourceList``.

Estratto da ``source_list.py`` per rispettare il limite di 300 righe
per file (§5.1.3). Contiene funzioni pure che operano su un
``QTreeWidget`` esistente.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

from core.models import FeedSource

if TYPE_CHECKING:
    from ui.widgets.source_list import SourceList

logger = logging.getLogger(__name__)


def build_tree(
    owner: "SourceList",
    sources: list[FeedSource],
    categories: list[str] | None = None,
) -> None:
    """Costruisce l'intero albero sorgenti/categorie nel QTreeWidget.

    Args:
        owner: Istanza ``SourceList`` (per accedere a costanti e tree).
        sources: Lista sorgenti feed.
        categories: Lista nomi categoria; se None, derivate da sources.
    """
    tree = owner._tree  # type: ignore[attr-defined]
    tree.clear()

    # Nodo radice "Tutti gli articoli"
    all_item: QTreeWidgetItem = QTreeWidgetItem(tree)
    all_item.setText(owner.COL_TITLE, "Tutti gli articoli")
    all_item.setText(owner.COL_UNREAD, str(_sum_unread(sources)) or "")
    # Allinea a destra il contatore non letti (valore numerico)
    all_item.setTextAlignment(
        owner.COL_UNREAD,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    all_item.setData(
        owner.COL_TITLE, Qt.ItemDataRole.UserRole + owner.KEY_KIND, owner.KIND_ALL
    )
    all_item.setData(
        owner.COL_TITLE, Qt.ItemDataRole.UserRole + owner.KEY_ID, ""
    )
    font = all_item.font(owner.COL_TITLE)
    font.setBold(True)
    all_item.setFont(owner.COL_TITLE, font)
    tree.expandItem(all_item)

    # Categorie
    if categories is None:
        cats: set[str] = {s.category for s in sources if s.category}
        categories = sorted(cats)

    for cat in categories:
        cat_item: QTreeWidgetItem = QTreeWidgetItem(tree)
        cat_item.setText(owner.COL_TITLE, f"\U0001F4C1 {cat}")
        cat_sources: list[FeedSource] = [
            s for s in sources if s.category == cat
        ]
        cat_item.setText(
            owner.COL_UNREAD,
            str(_sum_unread(cat_sources)) or "",
        )
        # Allinea a destra il contatore non letti della categoria
        cat_item.setTextAlignment(
            owner.COL_UNREAD,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        cat_item.setData(
            owner.COL_TITLE,
            Qt.ItemDataRole.UserRole + owner.KEY_KIND,
            owner.KIND_CATEGORY,
        )
        cat_item.setData(
            owner.COL_TITLE, Qt.ItemDataRole.UserRole + owner.KEY_ID, cat
        )
        cat_font = cat_item.font(owner.COL_TITLE)
        cat_font.setBold(True)
        cat_item.setFont(owner.COL_TITLE, cat_font)
        tree.expandItem(cat_item)
        for src in cat_sources:
            _add_source_item(owner, cat_item, src)

    # Senza categoria
    uncategorized: list[FeedSource] = [s for s in sources if not s.category]
    if uncategorized:
        unc_item: QTreeWidgetItem = QTreeWidgetItem(tree)
        unc_item.setText(owner.COL_TITLE, "Senza categoria")
        unc_item.setText(
            owner.COL_UNREAD,
            str(_sum_unread(uncategorized)) or "",
        )
        # Allinea a destra il contatore non letti
        unc_item.setTextAlignment(
            owner.COL_UNREAD,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        unc_item.setData(
            owner.COL_TITLE,
            Qt.ItemDataRole.UserRole + owner.KEY_KIND,
            owner.KIND_CATEGORY,
        )
        unc_item.setData(
            owner.COL_TITLE, Qt.ItemDataRole.UserRole + owner.KEY_ID, ""
        )
        unc_font = unc_item.font(owner.COL_TITLE)
        unc_font.setBold(True)
        unc_font.setItalic(True)
        unc_item.setFont(owner.COL_TITLE, unc_font)
        tree.expandItem(unc_item)
        for src in uncategorized:
            _add_source_item(owner, unc_item, src)


def _add_source_item(
    owner: "SourceList",
    parent: QTreeWidgetItem,
    source: FeedSource,
) -> None:
    """Aggiunge un nodo figlio per una sorgente.

    Se ``source.last_error`` è non vuoto, aggiunge un indicatore
    visivo ``⚠`` al titolo e include l'errore nel tooltip.
    """
    item: QTreeWidgetItem = QTreeWidgetItem(parent)
    title: str = source.title or source.url
    tooltip: str = source.url
    if source.last_error:
        title += "  \u26a0"  # ⚠ WARNING SIGN
        tooltip += f"\n\nUltimo errore: {source.last_error}"
    item.setText(owner.COL_TITLE, title)
    item.setToolTip(owner.COL_TITLE, tooltip)
    item.setText(
        owner.COL_UNREAD,
        str(source.unread_count) if source.unread_count else "",
    )
    # Allinea a destra il contatore non letti della singola sorgente
    item.setTextAlignment(
        owner.COL_UNREAD,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    item.setData(
        owner.COL_TITLE,
        Qt.ItemDataRole.UserRole + owner.KEY_KIND,
        owner.KIND_SOURCE,
    )
    item.setData(
        owner.COL_TITLE, Qt.ItemDataRole.UserRole + owner.KEY_ID, source.id
    )


def _sum_unread(sources: list[FeedSource]) -> int:
    return sum(s.unread_count for s in sources)


__all__ = ["build_tree"]
