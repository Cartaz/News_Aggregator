"""Helper per ricostruire l'albero delle sorgenti in ``SourceList``.

Estratto da ``source_list.py`` per rispettare il limite di 300 righe
per file (§5.1.3). Contiene la logica di raccolta sorgenti/categorie
quando si aggiunge un feed a una categoria nuova, più la ricerca di
nodi sorgente per ID.
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


def find_source_item(
    owner: "SourceList", source_id: str
) -> QTreeWidgetItem | None:
    """Cerca un nodo sorgente per ID in tutto l'albero.

    Args:
        owner: Istanza ``SourceList``.
        source_id: ID della sorgente da cercare.

    Returns:
        Il ``QTreeWidgetItem`` corrispondente, o None se non trovato.
    """
    tree = owner._tree  # type: ignore[attr-defined]
    for top_idx in range(tree.topLevelItemCount()):
        top: QTreeWidgetItem = tree.topLevelItem(top_idx)
        for child_idx in range(top.childCount()):
            child: QTreeWidgetItem = top.child(child_idx)
            kind: str = child.data(
                owner.COL_TITLE,  # type: ignore[attr-defined]
                Qt.ItemDataRole.UserRole + owner.KEY_KIND,  # type: ignore[attr-defined]
            ) or ""
            if kind == owner.KIND_SOURCE:  # type: ignore[attr-defined]
                id_val: str = child.data(
                    owner.COL_TITLE,  # type: ignore[attr-defined]
                    Qt.ItemDataRole.UserRole + owner.KEY_ID,  # type: ignore[attr-defined]
                ) or ""
                if id_val == source_id:
                    return child
    return None


def collect_sources_plus(
    owner: "SourceList", new_source: FeedSource
) -> list[FeedSource]:
    """Raccoglie tutte le sorgenti note dall'albero + quella nuova.

    Args:
        owner: Istanza ``SourceList``.
        new_source: Nuova sorgente da aggiungere.

    Returns:
        Lista di tutte le sorgenti (esistenti + nuova).
    """
    sources: list[FeedSource] = []
    for top_idx in range(owner._tree.topLevelItemCount()):  # type: ignore[attr-defined]
        top: QTreeWidgetItem = owner._tree.topLevelItem(top_idx)  # type: ignore[attr-defined]
        for child_idx in range(top.childCount()):
            child: QTreeWidgetItem = top.child(child_idx)
            kind: str = child.data(
                owner.COL_TITLE,  # type: ignore[attr-defined]
                Qt.ItemDataRole.UserRole + owner.KEY_KIND,  # type: ignore[attr-defined]
            ) or ""
            if kind == owner.KIND_SOURCE:  # type: ignore[attr-defined]
                title_text: str = child.text(owner.COL_TITLE)  # type: ignore[attr-defined]
                # Rimuovi il suffisso " ⚠" aggiunto quando source.last_error
                # è truthy. NON usare rstrip() perché tronca caratteri
                # legittimi (es. "C++!" diventa "C++").
                if title_text.endswith("  \u26a0"):
                    title_text = title_text[:-2]
                sources.append(
                    FeedSource(
                        url=child.toolTip(owner.COL_TITLE),  # type: ignore[attr-defined]
                        title=title_text,
                    )
                )
    sources.append(new_source)
    return sources


def collect_categories_plus(
    owner: "SourceList", new_cat: str
) -> list[str]:
    """Raccoglie tutte le categorie note dall'albero + quella nuova.

    Args:
        owner: Istanza ``SourceList``.
        new_cat: Nome della nuova categoria (può essere vuoto).

    Returns:
        Lista ordinata di nomi di categoria.
    """
    cats: set[str] = set()
    for top_idx in range(owner._tree.topLevelItemCount()):  # type: ignore[attr-defined]
        top: QTreeWidgetItem = owner._tree.topLevelItem(top_idx)  # type: ignore[attr-defined]
        kind: str = top.data(
            owner.COL_TITLE,  # type: ignore[attr-defined]
            Qt.ItemDataRole.UserRole + owner.KEY_KIND,  # type: ignore[attr-defined]
        ) or ""
        if kind == owner.KIND_CATEGORY:  # type: ignore[attr-defined]
            id_val: str = top.data(
                owner.COL_TITLE,  # type: ignore[attr-defined]
                Qt.ItemDataRole.UserRole + owner.KEY_ID,  # type: ignore[attr-defined]
            ) or ""
            if id_val:
                cats.add(id_val)
    if new_cat:
        cats.add(new_cat)
    return sorted(cats)


__all__ = ["collect_sources_plus", "collect_categories_plus"]
