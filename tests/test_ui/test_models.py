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
