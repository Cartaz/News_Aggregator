"""Unit coverage for the typed Qt models exposed to QML."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("PySide6")

from core.models import FeedItem
from ui.models import ArticleListModel, SourceListModel, SourceRowData


def item(source_id: str, title: str, *, read: bool = False) -> FeedItem:
    value = FeedItem.from_raw(
        source_id=source_id,
        title=title,
        link=f"https://example.com/{title.lower()}",
        summary=f"Summary {title}",
        published=datetime.now(timezone.utc) - timedelta(minutes=3),
        author="Author",
    )
    return replace(value, read=True) if read else value


def test_source_model_exposes_stable_role_names() -> None:
    model = SourceListModel()
    model.replace([SourceRowData("all", "", "Tutti gli articoli", 3, selected=True)])
    assert set(model.roleNames().values()) == {
        b"kind", b"identifier", b"title", b"unreadCount", b"selected",
        b"status", b"error", b"firstFeed", b"iconSource",
    }
    assert model.rowCount() == 1
    assert model.index_for("all", "") == 0


def test_source_model_updates_stable_rows_without_resetting_qml_view() -> None:
    model = SourceListModel()
    model.replace(
        [
            SourceRowData("all", "", "Tutti gli articoli", 3, selected=True),
            SourceRowData("feed", "feed-1", "Example", 2),
        ]
    )
    resets: list[bool] = []
    changes: list[bool] = []
    model.modelReset.connect(lambda: resets.append(True))
    model.dataChanged.connect(lambda *_args: changes.append(True))

    model.replace(
        [
            SourceRowData("all", "", "Tutti gli articoli", 2),
            SourceRowData("feed", "feed-1", "Example", 2, selected=True),
        ]
    )

    assert resets == []
    assert changes
    assert model.row(0) is not None and model.row(0).selected is False
    assert model.row(1) is not None and model.row(1).selected is True


def test_source_model_resets_when_navigation_structure_changes() -> None:
    model = SourceListModel()
    model.replace([SourceRowData("all", "", "Tutti gli articoli", 0, selected=True)])
    resets: list[bool] = []
    model.modelReset.connect(lambda: resets.append(True))

    model.replace(
        [
            SourceRowData("all", "", "Tutti gli articoli", 0, selected=True),
            SourceRowData("feed", "feed-1", "Example", 0),
        ]
    )

    assert resets == [True]


def test_source_model_updates_one_cached_icon_without_resetting_rows() -> None:
    model = SourceListModel()
    model.replace(
        [
            SourceRowData("all", "", "Tutti gli articoli", 0),
            SourceRowData("feed", "feed-1", "Example", 1),
        ]
    )

    assert model.set_icon_source("feed-1", "file:///tmp/example.svg") is True
    assert model.row(1) is not None
    assert model.row(1).icon_source == "file:///tmp/example.svg"
    assert model.set_icon_source("feed-1", "file:///tmp/example.svg") is False
    assert model.set_icon_source("missing", "file:///tmp/missing.svg") is False


def test_article_model_filters_without_duplicating_canonical_state() -> None:
    model = ArticleListModel()
    unread = item("feed", "Kernel News")
    read = item("feed", "Desktop News", read=True)
    model.replace_items([unread, read], {"feed": "Example"})
    assert model.rowCount() == 2

    model.set_filter("kernel", False)
    assert model.rowCount() == 1
    assert model.row(0).item.id == unread.id

    model.set_filter("", True)
    assert model.rowCount() == 1
    assert model.row(0).item.id == unread.id


def _counting(model: ArticleListModel) -> dict[str, int]:
    counts = {"reset": 0, "inserted": 0, "changed": 0}
    model.modelReset.connect(lambda: counts.__setitem__("reset", counts["reset"] + 1))
    model.rowsInserted.connect(lambda *_: counts.__setitem__("inserted", counts["inserted"] + 1))
    model.dataChanged.connect(lambda *_: counts.__setitem__("changed", counts["changed"] + 1))
    return counts


def test_article_model_reload_with_same_articles_does_not_reset() -> None:
    model = ArticleListModel()
    rows = [item("feed", "One"), item("feed", "Two")]
    model.replace_items(rows, {"feed": "Feed"})
    counts = _counting(model)

    model.replace_items([rows[0], replace(rows[1], read=True)], {"feed": "Feed"})

    assert counts["reset"] == 0
    assert counts["changed"] >= 1
    assert model.row(1).item.read is True


def test_article_model_inserts_new_articles_on_top_without_reset() -> None:
    model = ArticleListModel()
    old = [item("feed", "One"), item("feed", "Two")]
    model.replace_items(old, {"feed": "Feed"})
    counts = _counting(model)

    model.replace_items([item("feed", "Fresh"), *old], {"feed": "Feed"})

    assert counts == {"reset": 0, "inserted": 1, "changed": 1}
    assert model.rowCount() == 3
    assert model.row(0).item.title == "Fresh"


def test_article_model_marks_read_in_place() -> None:
    model = ArticleListModel()
    rows = [item("feed", "One"), item("feed", "Two")]
    model.replace_items(rows, {"feed": "Feed"})
    model.set_filter("", unread_only=True)
    counts = _counting(model)

    assert model.set_read(rows[0].id) is True

    assert counts["reset"] == 0
    assert model.rowCount() == 2  # stays visible until the filter is re-applied
    assert model.row(0).item.read is True
    assert model.set_read(rows[0].id) is False
