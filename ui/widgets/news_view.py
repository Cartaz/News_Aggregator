"""Vista centrale articoli con presentation layer Dark Neumorphism.

Layout, splitter, colonne, segnali e comportamento restano invariati.  Solo le
superfici Qt sono sostituite con equivalenti custom-painted.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.theme import ThemeColors
from core.models import FeedItem
from ui.widgets.news_view_table import format_date, format_time, populate_table
from ui.widgets.neumorphic_surfaces import (
    NeumorphicPanel,
    NeumorphicTableWidget,
    NeumorphicTextBrowser,
)

logger = logging.getLogger(__name__)


class NewsView(NeumorphicPanel):
    item_activated = Signal(str, str)
    open_in_browser = Signal(str)

    COL_DATE: int = 0
    COL_TIME: int = 1
    COL_SOURCE: int = 2
    COL_TITLE: int = 3

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, radius=16.0, tone="base")
        self._items: list[FeedItem] = []
        self._source_titles: dict[str, str] = {}
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        splitter: QSplitter = QSplitter(Qt.Orientation.Vertical, self)

        self._table: NeumorphicTableWidget = NeumorphicTableWidget(
            0,
            4,
            splitter,
        )
        self._table.setHorizontalHeaderLabels(
            ["Data", "Ora", "Sorgente", "Titolo"]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(
            NeumorphicTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            NeumorphicTableWidget.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(
            NeumorphicTableWidget.EditTrigger.NoEditTriggers
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(self.COL_DATE, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(self.COL_DATE, 100)
        header.setSectionResizeMode(self.COL_TIME, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(self.COL_TIME, 70)
        header.setSectionResizeMode(
            self.COL_SOURCE,
            QHeaderView.ResizeMode.Interactive,
        )
        header.resizeSection(self.COL_SOURCE, 150)
        header.setMinimumSectionSize(80)
        header.setSectionResizeMode(
            self.COL_TITLE,
            QHeaderView.ResizeMode.Stretch,
        )

        header_model = self._table.model()
        if header_model is not None:
            header_model.setHeaderData(
                self.COL_DATE,
                Qt.Orientation.Horizontal,
                Qt.AlignmentFlag.AlignCenter,
                Qt.ItemDataRole.TextAlignmentRole,
            )
            header_model.setHeaderData(
                self.COL_TIME,
                Qt.Orientation.Horizontal,
                Qt.AlignmentFlag.AlignCenter,
                Qt.ItemDataRole.TextAlignmentRole,
            )

        detail_widget: NeumorphicPanel = NeumorphicPanel(
            splitter,
            radius=16.0,
            tone="elevated",
        )
        detail_widget.setProperty("detailPanel", True)
        detail_layout: QVBoxLayout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(12, 10, 12, 4)
        detail_layout.setSpacing(6)

        self._title_label: QLabel = QLabel("", detail_widget)
        self._title_label.setProperty("title", True)
        self._title_label.setWordWrap(True)
        detail_layout.addWidget(self._title_label)

        self._meta_label: QLabel = QLabel("", detail_widget)
        self._meta_label.setProperty("secondary", True)
        self._meta_label.setWordWrap(True)
        detail_layout.addWidget(self._meta_label)

        self._detail: NeumorphicTextBrowser = NeumorphicTextBrowser(
            detail_widget
        )
        self._detail.setOpenExternalLinks(True)
        self._detail.anchorClicked.connect(self._on_link_clicked)
        detail_layout.addWidget(self._detail, stretch=1)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([420, 220])
        layout.addWidget(splitter, stretch=1)

        self._empty_label: QLabel = QLabel(
            "Nessun articolo da mostrare.\n"
            "Aggiungi un feed URL e premi Ctrl+R per aggiornare.",
            self,
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setProperty("secondary", True)
        layout.addWidget(self._empty_label)
        self._empty_label.hide()

        self._open_shortcut: QShortcut = QShortcut(
            QKeySequence("Ctrl+O"),
            self,
        )
        self._open_shortcut.activated.connect(self._open_current_in_browser)

        self._surface_overlay.raise_()
        detail_widget._surface_overlay.raise_()

    def _connect_signals(self) -> None:
        self._table.currentItemChanged.connect(self._on_item_changed)

    def set_items(
        self,
        items: list[FeedItem],
        source_titles: dict[str, str] | None = None,
    ) -> None:
        prev_current: QTableWidgetItem | None = self._table.currentItem()
        prev_item_id: str | None = (
            prev_current.data(Qt.ItemDataRole.UserRole)
            if prev_current is not None
            else None
        )
        prev_scroll: int = self._table.verticalScrollBar().value()

        self._items = list(items)
        if source_titles is not None:
            self._source_titles = source_titles

        self._table.blockSignals(True)
        self._table.setRowCount(0)
        if not self._items:
            self._table.blockSignals(False)
            self._empty_label.show()
            self._title_label.setText("")
            self._meta_label.setText("")
            self._detail.clear()
            return

        self._empty_label.hide()
        populate_table(self, self._items, self._source_titles)
        self._table.blockSignals(False)

        target_row: int = -1
        if prev_item_id:
            for row in range(self._table.rowCount()):
                row_item: QTableWidgetItem | None = self._table.item(
                    row,
                    self.COL_TITLE,
                )
                if (
                    row_item is not None
                    and row_item.data(Qt.ItemDataRole.UserRole) == prev_item_id
                ):
                    target_row = row
                    break

        if target_row >= 0:
            self._table.setCurrentCell(target_row, 0)
            self._table.verticalScrollBar().setValue(prev_scroll)
        elif self._table.rowCount() > 0:
            self._table.selectRow(0)

    def filter_by_text(self, query: str) -> None:
        q: str = query.strip().lower()
        for row in range(self._table.rowCount()):
            title_item: QTableWidgetItem | None = self._table.item(
                row,
                self.COL_TITLE,
            )
            if not title_item:
                continue
            item_id: str | None = title_item.data(Qt.ItemDataRole.UserRole)
            feed_item: FeedItem | None = next(
                (it for it in self._items if it.id == item_id),
                None,
            )
            if not feed_item:
                continue
            matches: bool = (
                not q
                or q in feed_item.title.lower()
                or q in feed_item.summary.lower()
            )
            self._table.setRowHidden(row, not matches)

    def mark_item_read(self, item_id: str) -> None:
        from ui.widgets.news_view_marker import mark_item_read

        mark_item_read(self, item_id)

    def get_current_item(self) -> FeedItem | None:
        current: QTableWidgetItem | None = self._table.currentItem()
        if not current:
            return None
        item_id: str | None = current.data(Qt.ItemDataRole.UserRole)
        return next((it for it in self._items if it.id == item_id), None)

    def _on_item_changed(
        self,
        current: QTableWidgetItem | None,
        previous: QTableWidgetItem | None,
    ) -> None:
        if not current:
            self._title_label.setText("")
            self._meta_label.setText("")
            self._detail.clear()
            return

        item_id: str | None = current.data(Qt.ItemDataRole.UserRole)
        feed_item: FeedItem | None = next(
            (it for it in self._items if it.id == item_id),
            None,
        )
        if not feed_item:
            return

        self._title_label.setText(feed_item.title)
        meta_parts: list[str] = []
        if feed_item.author:
            meta_parts.append(feed_item.author)
        meta_parts.append(
            f"{format_date(feed_item.published)} "
            f"{format_time(feed_item.published)}"
        )
        self._meta_label.setText(" · ".join(meta_parts))
        self._detail.setHtml(self._build_html(feed_item))

        pair: tuple[str, str] | None = current.data(
            Qt.ItemDataRole.UserRole + 1
        )
        if pair:
            source_id, item_uid = pair
            self.item_activated.emit(source_id, item_uid)

    def _build_html(self, item: FeedItem) -> str:
        summary_escaped: str = (
            item.summary.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        link_escaped: str = item.link.replace("&", "&amp;")
        return (
            f"<div style='color: {ThemeColors.TEXT_PRIMARY}; "
            f"font-family: \"Noto Sans\", sans-serif; "
            f"font-size: 13px; line-height: 1.6;'>"
            f"<p style='margin: 0 0 14px 0;'>{summary_escaped}</p>"
            f"<hr style='border: none; "
            f"border-top: 1px solid {ThemeColors.SHADOW_DARK_SOFT}; "
            f"margin: 12px 0;'>"
            f"<p style='font-size: 11px; "
            f"color: {ThemeColors.TEXT_SECONDARY}; "
            f"margin: 0; letter-spacing: 0.04em; "
            f"text-transform: uppercase;'>Link originale</p>"
            f"<p style='margin: 4px 0 0 0;'>"
            f"<a href='{link_escaped}' "
            f"style='color: {ThemeColors.LINK}; "
            f"text-decoration: none; font-weight: 500;'>"
            f"{link_escaped}</a></p></div>"
        )

    def _on_link_clicked(self, url: object) -> None:
        if hasattr(url, "toString"):
            url_str: str = url.toString()
        else:
            url_str = str(url)
        self.open_in_browser.emit(url_str)

    def _open_current_in_browser(self) -> None:
        item: FeedItem | None = self.get_current_item()
        if item:
            self.open_in_browser.emit(item.link)


__all__ = ["NewsView"]
