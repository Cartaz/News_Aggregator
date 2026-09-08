"""Qt models exposed to the QML presentation layer."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt

from core.models import FeedItem


@dataclass(frozen=True, slots=True)
class SourceRowData:
    kind: str
    identifier: str
    title: str
    unread_count: int
    selected: bool = False
    status: str = ""
    error: str = ""
    first_feed: bool = False
    icon_source: str = ""


@dataclass(frozen=True, slots=True)
class ArticleRowData:
    item: FeedItem
    source_title: str


class _SourceRole(IntEnum):
    Kind = Qt.ItemDataRole.UserRole + 1
    Identifier = Kind + 1
    Title = Kind + 2
    UnreadCount = Kind + 3
    Selected = Kind + 4
    Status = Kind + 5
    Error = Kind + 6
    FirstFeed = Kind + 7
    IconSource = Kind + 8


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
            int(_SourceRole.IconSource): b"iconSource",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        role = int(role)
        if role == int(_SourceRole.Kind):
            return row.kind
        if role == int(_SourceRole.Identifier):
            return row.identifier
        if role == int(_SourceRole.Title):
            return row.title
        if role == int(_SourceRole.UnreadCount):
            return row.unread_count
        if role == int(_SourceRole.Selected):
            return row.selected
        if role == int(_SourceRole.Status):
            return row.status
        if role == int(_SourceRole.Error):
            return row.error
        if role == int(_SourceRole.FirstFeed):
            return row.first_feed
        if role == int(_SourceRole.IconSource):
            return row.icon_source
        return None

    @staticmethod
    def _identity(row: SourceRowData) -> tuple[str, str]:
        return row.kind, row.identifier

    @staticmethod
    def _changed_roles(previous: SourceRowData, current: SourceRowData) -> list[int]:
        roles: list[int] = []
        if previous.title != current.title:
            roles.append(int(_SourceRole.Title))
        if previous.unread_count != current.unread_count:
            roles.append(int(_SourceRole.UnreadCount))
        if previous.selected != current.selected:
            roles.append(int(_SourceRole.Selected))
        if previous.status != current.status:
            roles.append(int(_SourceRole.Status))
        if previous.error != current.error:
            roles.append(int(_SourceRole.Error))
        if previous.first_feed != current.first_feed:
            roles.append(int(_SourceRole.FirstFeed))
        if previous.icon_source != current.icon_source:
            roles.append(int(_SourceRole.IconSource))
        return roles

    def replace(self, rows: list[SourceRowData]) -> None:
        """Refresh rows without resetting QML delegates when structure is stable."""
        incoming = list(rows)
        if len(incoming) == len(self._rows) and all(
            self._identity(previous) == self._identity(current)
            for previous, current in zip(self._rows, incoming, strict=True)
        ):
            for row_index, current in enumerate(incoming):
                previous = self._rows[row_index]
                if previous == current:
                    continue
                roles = self._changed_roles(previous, current)
                self._rows[row_index] = current
                if roles:
                    model_index = self.index(row_index, 0)
                    self.dataChanged.emit(model_index, model_index, roles)
            return

        self.beginResetModel()
        self._rows = incoming
        self.endResetModel()

    def set_selected(self, row_index: int) -> bool:
        """Change navigation selection without resetting the source ListView."""
        if not 0 <= row_index < len(self._rows):
            return False
        selected_indexes = [
            index for index, row in enumerate(self._rows) if row.selected
        ]
        if selected_indexes == [row_index]:
            return False

        changed_indexes = set(selected_indexes)
        changed_indexes.add(row_index)
        for index in changed_indexes:
            row = self._rows[index]
            selected = index == row_index
            if row.selected == selected:
                continue
            self._rows[index] = replace(row, selected=selected)
            model_index = self.index(index, 0)
            self.dataChanged.emit(
                model_index,
                model_index,
                [int(_SourceRole.Selected)],
            )
        return True

    def set_icon_source(self, identifier: str, icon_source: str) -> bool:
        """Update one feed icon without rebuilding navigation state."""
        for row_index, row in enumerate(self._rows):
            if row.kind != "feed" or row.identifier != identifier:
                continue
            if row.icon_source == icon_source:
                return False
            self._rows[row_index] = replace(row, icon_source=icon_source)
            model_index = self.index(row_index, 0)
            self.dataChanged.emit(
                model_index,
                model_index,
                [int(_SourceRole.IconSource)],
            )
            return True
        return False

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
        self._visible_rows: list[ArticleRowData] = self._all_rows
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
        role = int(role)
        if role == int(_ArticleRole.ItemId):
            return item.id
        if role == int(_ArticleRole.SourceId):
            return item.source_id
        if role == int(_ArticleRole.SourceTitle):
            return row.source_title
        if role == int(_ArticleRole.Title):
            return item.title or "Senza titolo"
        if role == int(_ArticleRole.Link):
            return item.link
        if role == int(_ArticleRole.Summary):
            return item.summary
        if role == int(_ArticleRole.Published):
            return item.published.astimezone().strftime("%d/%m/%Y %H:%M")
        if role == int(_ArticleRole.PublishedRelative):
            return _relative_time(item.published, datetime.now(timezone.utc))
        if role == int(_ArticleRole.Author):
            return item.author
        if role == int(_ArticleRole.Read):
            return item.read
        return None

    def replace_items(self, items: list[FeedItem], source_titles: dict[str, str]) -> None:
        self._all_rows = [
            ArticleRowData(
                item=item,
                source_title=source_titles.get(item.source_id, item.source_id),
            )
            for item in items
        ]
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
        if not query and not self._unread_only:
            rows = self._all_rows
        else:
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
