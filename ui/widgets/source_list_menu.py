"""Handler menu contestuale e dialog per ``SourceList``.

Estratto da ``source_list.py`` per rispettare il limite di 300 righe
per file (§5.1.3).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QInputDialog, QMenu, QTreeWidgetItem

if TYPE_CHECKING:
    from ui.widgets.source_list import SourceList

logger = logging.getLogger(__name__)


def show_context_menu(
    owner: "SourceList",
    pos: object,
) -> None:
    """Mostra il menu contestuale per le sorgenti.

    Args:
        owner: Istanza ``SourceList``.
        pos: Posizione relativa al viewport dell'albero.
    """
    point: QPoint = pos if isinstance(pos, QPoint) else QPoint(0, 0)
    item: QTreeWidgetItem | None = owner._tree.itemAt(point)  # type: ignore[attr-defined]
    if not item:
        return
    kind: str = item.data(
        owner.COL_TITLE,  # type: ignore[attr-defined]
        Qt.ItemDataRole.UserRole + owner.KEY_KIND,  # type: ignore[attr-defined]
    ) or ""
    if kind != owner.KIND_SOURCE:  # type: ignore[attr-defined]
        return
    source_id: str = item.data(
        owner.COL_TITLE,  # type: ignore[attr-defined]
        Qt.ItemDataRole.UserRole + owner.KEY_ID,  # type: ignore[attr-defined]
    ) or ""
    if not source_id:
        return
    menu: QMenu = QMenu(owner)  # type: ignore[arg-type]
    rename_action: QAction = QAction("Rinomina…", menu)
    category_action: QAction = QAction("Assegna categoria…", menu)
    clear_cat_action: QAction = QAction("Rimuovi categoria", menu)
    refresh_action: QAction = QAction("Aggiorna", menu)
    remove_action: QAction = QAction("Elimina", menu)
    rename_action.triggered.connect(lambda: _do_rename(owner, source_id))
    category_action.triggered.connect(
        lambda: _do_set_category(owner, source_id)
    )
    clear_cat_action.triggered.connect(
        lambda: owner.category_change_requested.emit(source_id, "")  # type: ignore[attr-defined]
    )
    refresh_action.triggered.connect(
        lambda: owner.refresh_requested.emit(source_id)  # type: ignore[attr-defined]
    )
    remove_action.triggered.connect(
        lambda: owner.remove_requested.emit(source_id)  # type: ignore[attr-defined]
    )
    menu.addAction(rename_action)
    menu.addAction(category_action)
    menu.addAction(clear_cat_action)
    menu.addSeparator()
    menu.addAction(refresh_action)
    menu.addAction(remove_action)
    menu.exec(owner._tree.viewport().mapToGlobal(point))  # type: ignore[attr-defined]


def _do_rename(owner: "SourceList", source_id: str) -> None:
    """Apre un dialog di input per il rename."""
    title, ok = QInputDialog.getText(
        owner,  # type: ignore[arg-type]
        "Rinomina feed",
        "Nuovo nome del feed:",
        text="",
    )
    if ok and title.strip():
        owner.rename_requested.emit(source_id, title.strip())  # type: ignore[attr-defined]


def _do_set_category(owner: "SourceList", source_id: str) -> None:
    """Apre un dialog di input per assegnare una categoria."""
    cat, ok = QInputDialog.getText(
        owner,  # type: ignore[arg-type]
        "Assegna categoria",
        "Nome categoria (es. Tech, Games, Economia):",
        text="",
    )
    if ok:
        owner.category_change_requested.emit(source_id, cat.strip())  # type: ignore[attr-defined]


__all__ = ["show_context_menu"]
