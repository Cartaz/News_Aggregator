"""Lista laterale delle sorgenti feed organizzate per categoria.

Mostra un albero gerarchico:
- Nodo radice "Tutti gli articoli" (mega-feed virtuale)
- Un nodo per ogni categoria (es. Tech, Games, Economia)
- Sotto ogni categoria, le sorgenti assegnate
- Sorgenti senza categoria appaiono sotto "Senza categoria"

La costruzione dell'albero è delegata a ``source_tree_builder``; il menu
contestuale è delegato a ``source_list_menu`` — tutto per rispettare il
limite di 300 righe per file (§5.1.3).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.models import FeedSource
from ui.widgets.source_list_menu import show_context_menu
from ui.widgets.source_tree_builder import build_tree

logger = logging.getLogger(__name__)


class SourceList(QWidget):
    """Pannello con elenco sorgenti feed organizzate per categoria.

    Args:
        parent: Widget genitore.

    Signals:
        all_selected: Emesso quando l'utente seleziona "Tutti gli articoli".
        category_selected: Emesso con il nome categoria.
        source_selected: Emesso con ``source_id``.
        refresh_requested: Emesso con ``source_id`` per refresh singolo.
        remove_requested: Emesso con ``source_id`` per rimozione.
        rename_requested: Emesso con (source_id, new_title).
        category_change_requested: Emesso con (source_id, new_category).
    """

    all_selected = Signal()
    category_selected = Signal(str)
    source_selected = Signal(str)
    refresh_requested = Signal(str)
    remove_requested = Signal(str)
    rename_requested = Signal(str, str)
    category_change_requested = Signal(str, str)

    COL_TITLE: int = 0
    COL_UNREAD: int = 1

    # UserRole keys (offset rispetto a Qt.ItemDataRole.UserRole)
    KEY_KIND: int = 0  # "all" | "category" | "source"
    KEY_ID: int = 1  # source_id o category name

    KIND_ALL: str = "all"
    KIND_CATEGORY: str = "category"
    KIND_SOURCE: str = "source"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Costruisce la struttura del widget."""
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._tree: QTreeWidget = QTreeWidget(self)
        self._tree.setHeaderLabels(["Sorgente", "Da leggere"])
        self._tree.setRootIsDecorated(True)
        self._tree.setUniformRowHeights(True)
        self._tree.setAlternatingRowColors(False)
        # Colonna 0 (Sorgente): Stretch - si espande per riempire lo spazio
        # disponibile ed evita il troncamento del testo ("Tutti gli articoli"
        # non viene più tagliato a ".tti gli articoli").
        # Colonna 1 (Da leggere): ResizeToContents - si adatta al contenuto
        # (numero ad 1-3 cifre) senza rubare spazio alla colonna 0.
        header: QHeaderView = self._tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(
            self.COL_TITLE, QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            self.COL_UNREAD, QHeaderView.ResizeMode.ResizeToContents
        )
        # Larghezza minima sensata per la colonna "Da leggere"
        self._tree.setColumnWidth(self.COL_UNREAD, 64)
        # Allineamento a destra per l'intestazione "Da leggere" e per le
        # celle numeriche (i conteggi non letti sono valori numerici).
        header_model = self._tree.header()
        header_model.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        # Nascondi scrollbar orizzontale (vincolo utente #2): ora non più
        # necessario dato che la colonna 0 è in Stretch e non va in overflow.
        self._tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._tree.setHeaderHidden(False)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.setExpandsOnDoubleClick(False)
        layout.addWidget(self._tree)

    def _connect_signals(self) -> None:
        """Collega segnali interni."""
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.customContextMenuRequested.connect(
            lambda pos: show_context_menu(self, pos)
        )

    # --- Public API ---

    def set_sources(
        self,
        sources: list[FeedSource],
        categories: list[str] | None = None,
    ) -> None:
        """Sostituisce l'intero albero sorgenti/categorie."""
        build_tree(self, sources, categories)

    def add_source(self, source: FeedSource) -> None:
        """Aggiunge una sorgente all'albero.

        Se la categoria non ha ancora un nodo, ricostruisce l'albero.
        """
        parent: QTreeWidgetItem | None = self._find_category_parent(source.category)
        if parent is None:
            # Categoria nuova: ricostruisci tutto
            self.set_sources(
                self._collect_sources_plus(source),
                self._collect_categories_plus(source.category),
            )
            return
        # Evita duplicati
        for idx in range(parent.childCount()):
            child: QTreeWidgetItem = parent.child(idx)
            if (
                child.data(self.COL_TITLE, Qt.ItemDataRole.UserRole + self.KEY_KIND)
                == self.KIND_SOURCE
                and child.data(self.COL_TITLE, Qt.ItemDataRole.UserRole + self.KEY_ID)
                == source.id
            ):
                return
        self._add_source_item(parent, source)

    def _add_source_item(
        self, parent: QTreeWidgetItem, source: FeedSource
    ) -> None:
        """Aggiunge un nodo figlio per una sorgente.

        Se ``source.last_error`` è non vuoto, aggiunge ``⚠`` al titolo
        e include l'errore nel tooltip.
        """
        item: QTreeWidgetItem = QTreeWidgetItem(parent)
        title: str = source.title or source.url
        tooltip: str = source.url
        if source.last_error:
            title += "  \u26a0"  # ⚠ WARNING SIGN
            tooltip += f"\n\nUltimo errore: {source.last_error}"
        item.setText(self.COL_TITLE, title)
        item.setToolTip(self.COL_TITLE, tooltip)
        item.setText(
            self.COL_UNREAD,
            str(source.unread_count) if source.unread_count else "",
        )
        # Allinea a destra il contatore non letti (valore numerico)
        item.setTextAlignment(
            self.COL_UNREAD,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        item.setData(
            self.COL_TITLE, Qt.ItemDataRole.UserRole + self.KEY_KIND, self.KIND_SOURCE
        )
        item.setData(
            self.COL_TITLE, Qt.ItemDataRole.UserRole + self.KEY_ID, source.id
        )

    def update_source(self, source: FeedSource) -> None:
        """Aggiorna i dati visualizzati di una sorgente.

        Dopo aver aggiornato il nodo sorgente, ricalcola anche i
        contatori ``Da leggere`` dei nodi padre (categoria e "Tutti
        gli articoli") sommando i figli.
        """
        item: QTreeWidgetItem | None = self._find_source_item(source.id)
        if item is None:
            self.add_source(source)
            self.refresh_unread_totals()
            return
        title: str = source.title or source.url
        tooltip: str = source.url
        if source.last_error:
            title += "  \u26a0"  # ⚠ WARNING SIGN
            tooltip += f"\n\nUltimo errore: {source.last_error}"
        item.setText(self.COL_TITLE, title)
        item.setToolTip(self.COL_TITLE, tooltip)
        item.setText(
            self.COL_UNREAD,
            str(source.unread_count) if source.unread_count else "",
        )
        expected_parent: QTreeWidgetItem | None = self._find_category_parent(source.category)
        if expected_parent is not None and item.parent() is not expected_parent:
            current_parent: QTreeWidgetItem | None = item.parent()
            if current_parent is not None:
                current_parent.removeChild(item)
            expected_parent.addChild(item)
            self._tree.expandItem(expected_parent)
        # Ricalcola i totali dei nodi padre
        self.refresh_unread_totals()

    def refresh_unread_totals(self) -> None:
        """Ricalcola i contatori ``Da leggere`` dei nodi padre.

        Delegato a ``source_list_totals.refresh_unread_totals`` per
        rispettare il limite di 300 righe per file (§5.1.3).
        """
        from ui.widgets.source_list_totals import refresh_unread_totals
        refresh_unread_totals(self)

    def remove_source(self, source_id: str) -> None:
        """Rimuove una sorgente dall'albero per ID."""
        item: QTreeWidgetItem | None = self._find_source_item(source_id)
        if item is None:
            return
        parent: QTreeWidgetItem | None = item.parent()
        if parent is not None:
            parent.removeChild(item)

    def clear_selection(self) -> None:
        """Deseleziona tutti gli elementi."""
        self._tree.clearSelection()

    def get_selected(self) -> tuple[str, str]:
        """Restituisce (kind, id) dell'elemento selezionato, o ("", "")."""
        items: list[QTreeWidgetItem] = self._tree.selectedItems()
        if not items:
            return ("", "")
        item: QTreeWidgetItem = items[0]
        kind: str = item.data(
            self.COL_TITLE, Qt.ItemDataRole.UserRole + self.KEY_KIND
        ) or ""
        id_val: str = item.data(
            self.COL_TITLE, Qt.ItemDataRole.UserRole + self.KEY_ID
        ) or ""
        return (kind, id_val)

    def get_selected_id(self) -> str | None:
        """Restituisce il ``source_id`` della sorgente selezionata, o None.

        Utile per le azioni che operano solo su sorgenti (non su categorie
        o sul nodo "Tutti gli articoli").
        """
        kind, id_val = self.get_selected()
        if kind == self.KIND_SOURCE and id_val:
            return id_val
        return None

    # --- Helpers ---

    def _find_category_parent(self, category: str) -> QTreeWidgetItem | None:
        """Trova il nodo padre per una categoria."""
        target_label: str = f"\U0001F4C1 {category}" if category else "Senza categoria"
        for idx in range(self._tree.topLevelItemCount()):
            top: QTreeWidgetItem = self._tree.topLevelItem(idx)
            kind: str = top.data(
                self.COL_TITLE, Qt.ItemDataRole.UserRole + self.KEY_KIND
            ) or ""
            if kind == self.KIND_CATEGORY and top.text(self.COL_TITLE) == target_label:
                return top
        return None

    def _find_source_item(self, source_id: str) -> QTreeWidgetItem | None:
        """Cerca un nodo sorgente per ID in tutto l'albero."""
        from ui.widgets.source_list_collectors import find_source_item
        return find_source_item(self, source_id)

    def _collect_sources_plus(self, new_source: FeedSource) -> list[FeedSource]:
        """Raccoglie tutte le sorgenti note + quella nuova."""
        from ui.widgets.source_list_collectors import collect_sources_plus
        return collect_sources_plus(self, new_source)

    def _collect_categories_plus(self, new_cat: str) -> list[str]:
        """Raccoglie tutte le categorie note + quella nuova."""
        from ui.widgets.source_list_collectors import collect_categories_plus
        return collect_categories_plus(self, new_cat)

    # --- Signal handlers ---

    def _on_item_clicked(
        self, item: QTreeWidgetItem, column: int
    ) -> None:
        """Gestisce il click emettendo il segnale appropriato."""
        kind: str = item.data(
            self.COL_TITLE, Qt.ItemDataRole.UserRole + self.KEY_KIND
        ) or ""
        id_val: str = item.data(
            self.COL_TITLE, Qt.ItemDataRole.UserRole + self.KEY_ID
        ) or ""
        if kind == self.KIND_ALL:
            self.all_selected.emit()
        elif kind == self.KIND_CATEGORY:
            self.category_selected.emit(id_val)
        elif kind == self.KIND_SOURCE:
            self.source_selected.emit(id_val)


__all__ = ["SourceList"]
