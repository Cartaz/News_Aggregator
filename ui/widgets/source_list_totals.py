"""Helper per ricalcolare i contatori ``Da leggere`` dei nodi padre.

Estratto da ``source_list.py`` per rispettare il limite di 300 righe
per file (§5.1.3).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

if TYPE_CHECKING:
    from ui.widgets.source_list import SourceList

logger = logging.getLogger(__name__)


def refresh_unread_totals(owner: "SourceList") -> None:
    """Ricalcola i contatori ``Da leggere`` dei nodi padre.

    Per ogni nodo categoria somma i contatori dei feed figli diretti.
    Per il nodo ``KIND_ALL`` ("Tutti gli articoli") somma i contatori
    di tutti i feed di tutte le categorie (compresi quelli senza
    categoria). Garantisce che il counter sia sempre coerente dopo
    operazioni di mark-as-read o refresh.

    Args:
        owner: Istanza ``SourceList``.
    """
    tree = owner._tree  # type: ignore[attr-defined]
    for top_idx in range(tree.topLevelItemCount()):
        top: QTreeWidgetItem = tree.topLevelItem(top_idx)
        kind: str = top.data(
            owner.COL_TITLE,  # type: ignore[attr-defined]
            Qt.ItemDataRole.UserRole + owner.KEY_KIND,  # type: ignore[attr-defined]
        ) or ""
        if kind == owner.KIND_ALL:  # type: ignore[attr-defined]
            _update_all_node(owner, top)
        elif kind == owner.KIND_CATEGORY:  # type: ignore[attr-defined]
            _update_category_node(owner, top)


def _update_all_node(owner: "SourceList", top: QTreeWidgetItem) -> None:
    """Somma i contatori di tutti i feed di tutte le categorie."""
    tree = owner._tree  # type: ignore[attr-defined]
    total: int = 0
    for cat_idx in range(tree.topLevelItemCount()):
        cat_node: QTreeWidgetItem = tree.topLevelItem(cat_idx)
        cat_kind: str = cat_node.data(
            owner.COL_TITLE,  # type: ignore[attr-defined]
            Qt.ItemDataRole.UserRole + owner.KEY_KIND,  # type: ignore[attr-defined]
        ) or ""
        if cat_kind != owner.KIND_CATEGORY:  # type: ignore[attr-defined]
            continue
        for child_idx in range(cat_node.childCount()):
            child: QTreeWidgetItem = cat_node.child(child_idx)
            child_kind: str = child.data(
                owner.COL_TITLE,  # type: ignore[attr-defined]
                Qt.ItemDataRole.UserRole + owner.KEY_KIND,  # type: ignore[attr-defined]
            ) or ""
            if child_kind == owner.KIND_SOURCE:  # type: ignore[attr-defined]
                try:
                    total += int(
                        child.text(owner.COL_UNREAD) or "0"  # type: ignore[attr-defined]
                    )
                except ValueError:
                    pass
    top.setText(owner.COL_UNREAD, str(total) if total else "")  # type: ignore[attr-defined]


def _update_category_node(owner: "SourceList", top: QTreeWidgetItem) -> None:
    """Somma i contatori dei feed figli diretti di una categoria."""
    total: int = 0
    for child_idx in range(top.childCount()):
        child: QTreeWidgetItem = top.child(child_idx)
        child_kind: str = child.data(
            owner.COL_TITLE,  # type: ignore[attr-defined]
            Qt.ItemDataRole.UserRole + owner.KEY_KIND,  # type: ignore[attr-defined]
        ) or ""
        if child_kind == owner.KIND_SOURCE:  # type: ignore[attr-defined]
            try:
                total += int(
                    child.text(owner.COL_UNREAD) or "0"  # type: ignore[attr-defined]
                )
            except ValueError:
                pass
    top.setText(owner.COL_UNREAD, str(total) if total else "")  # type: ignore[attr-defined]


__all__ = ["refresh_unread_totals"]
