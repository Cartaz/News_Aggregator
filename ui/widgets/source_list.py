"""Lista laterale delle sorgenti feed organizzate per categoria.

La struttura, i segnali e il comportamento sono invariati.  Il container è una
superficie neumorfica raised e il QTreeWidget è una cavità inset.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHeaderView, QTreeWidgetItem, QVBoxLayout, QWidget

from core.models import FeedSource
from ui.widgets.neumorphic_surfaces import NeumorphicPanel, NeumorphicTreeWidget
from ui.widgets.source_list_menu import show_context_menu
from ui.widgets.source_tree_builder import build_tree

logger = logging.getLogger(__name__)


class SourceList(NeumorphicPanel):
    all_selected = Signal()
    category_selected = Signal(str)
    source_selected = Signal(str)
    refresh_requested = Signal(str)
    remove_requested = Signal(str)
    rename_requested = Signal(str, str)
    category_change_requested = Signal(str, str)

    COL_TITLE: int = 0
    COL_UNREAD: int = 1

    KEY_KIND: int = 0
    KEY_ID: int = 1

    KIND_ALL: str = "all"
    KIND_CATEGORY: str = "category"
    KIND_SOURCE: str = "source"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, radius=16.0, tone="base")
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._tree: NeumorphicTreeWidget = NeumorphicTreeWidget(self)
        self._tree.setHeaderLabels(["Sorgente", "Da leggere"])
        self._tree.setRootIsDecorated(True)
        self._tree.setUniformRowHeights(True)
        self._tree.setAlternatingRowColors(False)

        header: QHeaderView = self._tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(self.COL_TITLE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            self.COL_UNREAD,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._tree.setColumnWidth(self.COL_UNREAD, 64)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._tree.setHeaderHidden(False)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.setExpandsOnDoubleClick(False)
        layout.addWidget(self._tree)

        self._surface_overlay.raise_()

    def _connect_signals(self) -> None:
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.customContextMenuRequested.connect(
            lambda pos: show_context_menu(self, pos)
        )

    def set_sources(
        self,
        sources: list[FeedSource],
        categories: list[str] | None = None,
    ) -> None:
        build_tree(self, sources, categories)

    def add_source(self, source: FeedSource) -> None:
        parent: QTreeWidgetItem | None = self._find_category_parent(source.category)
        if parent is None:
            self.set_sources(
                self._collect_sources_plus(source),
                self._collect_categories_plus(source.category),
            )
            return
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
        self,
        parent: QTreeWidgetItem,
        source: FeedSource,
    ) -> None:
        item: QTreeWidgetItem = QTreeWidgetItem(parent)
        title: str = source.title or source.url
        tooltip: str = source.url
        if source.last_error:
            title += "  \u26a0"
            tooltip += f"\n\nUltimo errore: {source.last_error}"
        item.setText(self.COL_TITLE, title)
        item.setToolTip(self.COL_TITLE, tooltip)
        item.setText(
            self.COL_UNREAD,
            str(source.unread_count) if source.unread_count else "",
        )
        item.setTextAlignment(
            self.COL_UNREAD,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        item.setData(
            self.COL_TITLE,
            Qt.ItemDataRole.UserRole + self.KEY_KIND,
            self.KIND_SOURCE,
        )
        item.setData(
            self.COL_TITLE,
            Qt.ItemDataRole.UserRole + self.KEY_ID,
            source.id,
        )

    def update_source(self, source: FeedSource) -> None:
        item: QTreeWidgetItem | None = self._find_source_item(source.id)
        if item is None:
            self.add_source(source)
            self.refresh_unread_totals()
            return
        title: str = source.title or source.url
        tooltip: str = source.url
        if source.last_error:
            title += "  \u26a0"
            tooltip += f"\n\nUltimo errore: {source.last_error}"
        item.setText(self.COL_TITLE, title)
        item.setToolTip(self.COL_TITLE, tooltip)
        item.setText(
            self.COL_UNREAD,
            str(source.unread_count) if source.unread_count else "",
        )
        expected_parent: QTreeWidgetItem | None = self._find_category_parent(
            source.category
        )
        if expected_parent is not None and item.parent() is not expected_parent:
            current_parent: QTreeWidgetItem | None = item.parent()
            if current_parent is not None:
                current_parent.removeChild(item)
            expected_parent.addChild(item)
            self._tree.expandItem(expected_parent)
        self.refresh_unread_totals()

    def refresh_unread_totals(self) -> None:
        from ui.widgets.source_list_totals import refresh_unread_totals

        refresh_unread_totals(self)

    def remove_source(self, source_id: str) -> None:
        item: QTreeWidgetItem | None = self._find_source_item(source_id)
        if item is None:
            return
        parent: QTreeWidgetItem | None = item.parent()
        if parent is not None:
            parent.removeChild(item)

    def clear_selection(self) -> None:
        self._tree.clearSelection()

    def get_selected(self) -> tuple[str, str]:
        items: list[QTreeWidgetItem] = self._tree.selectedItems()
        if not items:
            return ("", "")
        item: QTreeWidgetItem = items[0]
        kind: str = item.data(
            self.COL_TITLE,
            Qt.ItemDataRole.UserRole + self.KEY_KIND,
        ) or ""
        id_val: str = item.data(
            self.COL_TITLE,
            Qt.ItemDataRole.UserRole + self.KEY_ID,
        ) or ""
        return (kind, id_val)

    def get_selected_id(self) -> str | None:
        kind, id_val = self.get_selected()
        if kind == self.KIND_SOURCE and id_val:
            return id_val
        return None

    def _find_category_parent(self, category: str) -> QTreeWidgetItem | None:
        target_label: str = (
            f"\U0001F4C1 {category}" if category else "Senza categoria"
        )
        for idx in range(self._tree.topLevelItemCount()):
            top: QTreeWidgetItem = self._tree.topLevelItem(idx)
            kind: str = top.data(
                self.COL_TITLE,
                Qt.ItemDataRole.UserRole + self.KEY_KIND,
            ) or ""
            if kind == self.KIND_CATEGORY and top.text(self.COL_TITLE) == target_label:
                return top
        return None

    def _find_source_item(self, source_id: str) -> QTreeWidgetItem | None:
        from ui.widgets.source_list_collectors import find_source_item

        return find_source_item(self, source_id)

    def _collect_sources_plus(self, new_source: FeedSource) -> list[FeedSource]:
        from ui.widgets.source_list_collectors import collect_sources_plus

        return collect_sources_plus(self, new_source)

    def _collect_categories_plus(self, new_cat: str) -> list[str]:
        from ui.widgets.source_list_collectors import collect_categories_plus

        return collect_categories_plus(self, new_cat)

    def _on_item_clicked(
        self,
        item: QTreeWidgetItem,
        column: int,
    ) -> None:
        kind: str = item.data(
            self.COL_TITLE,
            Qt.ItemDataRole.UserRole + self.KEY_KIND,
        ) or ""
        id_val: str = item.data(
            self.COL_TITLE,
            Qt.ItemDataRole.UserRole + self.KEY_ID,
        ) or ""
        if kind == self.KIND_ALL:
            self.all_selected.emit()
        elif kind == self.KIND_CATEGORY:
            self.category_selected.emit(id_val)
        elif kind == self.KIND_SOURCE:
            self.source_selected.emit(id_val)


__all__ = ["SourceList"]
