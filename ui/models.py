"""Qt models exposed to the QML presentation layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt

from core.models import FeedItem


@dataclass(frozen=True)
class SourceRowData:
    kind: str
    identifier: str
    title: str
    unread_count: int
    selected: bool = False
    status: str = ""
    error: str = ""
    first_feed: bool = False


@dataclass(frozen=True)
class ArticleRowData:
    item: FeedItem
    source_title: str
    published_relative: str
    published_full: str


class _SourceRole(IntEnum):
    Kind = Qt.ItemDataRole.UserRole + 1
    Identifier = Kind + 1
    Title = Kind + 2
    UnreadCount = Kind + 3
    Selected = Kind + 4
    Status = Kind + 5
    Error = Kind + 6
    FirstFeed = Kind + 7


class SourceListModel(QAbstractListModel):
    """Flat navigation model for all/category/feed rows."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[SourceRowData] = []

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802 - Qt API
        return {
            int(_SourceRole.Kind): b"kind",
            int(_SourceRole.Identifier): b"identifier",
            int(_SourceRole.Title): b"title",
            int(_SourceRole.UnreadCount): b"unreadCount",
            int(_SourceRole.Selected): b"selected",
            int(_SourceRole.Status): b"status",
            int(_SourceRole.Error): b"error",
            int(_SourceRole.FirstFeed): b"firstFeed",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        mapping: dict[int, Any] = {
            int(_SourceRole.Kind): row.kind,
            int(_SourceRole.Identifier): row.identifier,
            int(_SourceRole.Title): row.title,
            int(_SourceRole.UnreadCount): row.unread_count,
            int(_SourceRole.Selected): row.selected,
            int(_SourceRole.Status): row.status,
            int(_SourceRole.Error): row.error,
            int(_SourceRole.FirstFeed): row.first_feed,
        }
        return mapping.get(int(role))

    def replace(self, rows: list[SourceRowData]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row(self, index: int) -> SourceRowData | None:
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    def index_for(self, kind: str, identifier: str) -> int:
        for index, row in enumerate(self._rows):
            if row.kind == kind and row.identifier == identifier:
                return index
        return -1


class _ArticleRole(IntEnum):
    ItemId = Qt.ItemDataRole.UserRole + 1
    SourceId = ItemId + 1
    SourceTitle = ItemId + 2
    Title = ItemId + 3
    Link = ItemId + 4
    Summary = ItemId + 5
    Published = ItemId + 6
    PublishedRelative = ItemId + 7
    Author = ItemId + 8
    Read = ItemId + 9


class ArticleListModel(QAbstractListModel):
    """Visible article rows for the currently selected scope and filters."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._all_rows: list[ArticleRowData] = []
        self._visible_rows: list[ArticleRowData] = []
        self._search_query = ""
        self._unread_only = False

    def roleNames(self) -> dict[int, bytes]:  # noqa: N802 - Qt API
        return {
            int(_ArticleRole.ItemId): b"itemId",
            int(_ArticleRole.SourceId): b"sourceId",
            int(_ArticleRole.SourceTitle): b"sourceTitle",
            int(_ArticleRole.Title): b"title",
            int(_ArticleRole.Link): b"link",
            int(_ArticleRole.Summary): b"summary",
            int(_ArticleRole.Published): b"published",
            int(_ArticleRole.PublishedRelative): b"publishedRelative",
            int(_ArticleRole.Author): b"author",
            int(_ArticleRole.Read): b"read",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._visible_rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._visible_rows):
            return None
        row = self._visible_rows[index.row()]
        item = row.item
        mapping: dict[int, Any] = {
            int(_ArticleRole.ItemId): item.id,
            int(_ArticleRole.SourceId): item.source_id,
            int(_ArticleRole.SourceTitle): row.source_title,
            int(_ArticleRole.Title): item.title or "Senza titolo",
            int(_ArticleRole.Link): item.link,
            int(_ArticleRole.Summary): item.summary,
            int(_ArticleRole.Published): row.published_full,
            int(_ArticleRole.PublishedRelative): row.published_relative,
            int(_ArticleRole.Author): item.author,
            int(_ArticleRole.Read): item.read,
        }
        return mapping.get(int(role))

    def replace_items(self, items: list[FeedItem], source_titles: dict[str, str]) -> None:
        now = datetime.now(timezone.utc)
        rows = [
            ArticleRowData(
                item=item,
                source_title=source_titles.get(item.source_id, item.source_id),
                published_relative=_relative_time(item.published, now),
                published_full=item.published.astimezone().strftime("%d/%m/%Y %H:%M"),
            )
            for item in items
        ]
        self._all_rows = rows
        self._apply_filter()

    def set_filter(self, search_query: str, unread_only: bool) -> None:
        normalized = (search_query or "").strip().casefold()
        unread_only = bool(unread_only)
        if normalized == self._search_query and unread_only == self._unread_only:
            return
        self._search_query = normalized
        self._unread_only = unread_only
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self._search_query
        rows = [
            row
            for row in self._all_rows
            if (not self._unread_only or not row.item.read)
            and (
                not query
                or query in row.item.title.casefold()
                or query in row.source_title.casefold()
                or query in row.item.summary.casefold()
                or query in row.item.author.casefold()
            )
        ]
        self.beginResetModel()
        self._visible_rows = rows
        self.endResetModel()

    def row(self, index: int) -> ArticleRowData | None:
        if 0 <= index < len(self._visible_rows):
            return self._visible_rows[index]
        return None

    def total_count(self) -> int:
        return len(self._all_rows)

    def index_for_item(self, item_id: str) -> int:
        for index, row in enumerate(self._visible_rows):
            if row.item.id == item_id:
                return index
        return -1


def _relative_time(published: datetime, now: datetime) -> str:
    value = published if published.tzinfo is not None else published.replace(tzinfo=timezone.utc)
    seconds = max(0, int((now - value.astimezone(timezone.utc)).total_seconds()))
    if seconds < 60:
        return "adesso"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} h"
    days = hours // 24
    return f"{days} g"


__all__ = [
    "ArticleListModel",
    "ArticleRowData",
    "SourceListModel",
    "SourceRowData",
]
