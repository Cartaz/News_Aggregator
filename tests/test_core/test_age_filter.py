"""Test per il filtro 48 ore sugli articoli."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from core.feed_manager import FeedManager
from core.models import FeedItem


@pytest.fixture
def manager(tmp_paths: Path, reset_event_bus: None) -> FeedManager:
    """Restituisce un FeedManager con storage temporaneo."""
    FeedManager._instance = None  # type: ignore[attr-defined]
    return FeedManager()


def _make_item(item_id: str, source_id: str, hours_ago: float) -> FeedItem:
    """Crea un FeedItem pubblicato `hours_ago` ore fa."""
    return FeedItem(
        id=item_id,
        source_id=source_id,
        title=f"Articolo {item_id}",
        link=f"https://example.com/{item_id}",
        summary="Testo",
        published=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
    )


def test_old_items_pruned_on_refresh(manager: FeedManager) -> None:
    """Gli articoli più vecchi di 48h devono essere eliminati dopo il refresh."""
    source = manager.add("https://example.com/feed.xml")
    # Simula refresh con articoli di età diversa
    items = [
        _make_item("recent", source.id, 1),  # 1h fa → deve rimanere
        _make_item("mid", source.id, 24),    # 24h fa → deve rimanere
        _make_item("old", source.id, 50),    # 50h fa → deve essere eliminato
        _make_item("veryold", source.id, 100),  # 100h fa → eliminato
    ]
    with patch(
        "core.feed_manager.fetch_and_parse",
        return_value=("Title", items),
    ):
        manager.refresh(source.id)
    refreshed = manager.get(source.id)
    ids = {it.id for it in refreshed.items}
    assert "recent" in ids
    assert "mid" in ids
    assert "old" not in ids
    assert "veryold" not in ids


def test_get_all_items_filters_old(manager: FeedManager) -> None:
    """get_all_items deve escludere articoli più vecchi di 48h."""
    source = manager.add("https://example.com/feed.xml")
    items = [
        _make_item("recent", source.id, 2),
        _make_item("borderline", source.id, 47),
        _make_item("old", source.id, 49),
    ]
    with patch(
        "core.feed_manager.fetch_and_parse",
        return_value=("Title", items),
    ):
        manager.refresh(source.id)
    # Abbassa MAX_ITEM_AGE_HOURS per verificare il filtro
    all_items = manager.get_all_items(limit=500)
    ids = {it.id for it in all_items}
    assert "recent" in ids
    assert "borderline" in ids
    assert "old" not in ids


def test_get_items_by_category_filters_old(manager: FeedManager) -> None:
    """get_items_by_category deve escludere articoli più vecchi di 48h."""
    source = manager.add("https://example.com/feed.xml")
    manager.set_category(source.id, "Tech")
    items = [
        _make_item("recent", source.id, 1),
        _make_item("old", source.id, 72),
    ]
    with patch(
        "core.feed_manager.fetch_and_parse",
        return_value=("Title", items),
    ):
        manager.refresh(source.id)
    tech_items = manager.get_items_by_category("Tech")
    ids = {it.id for it in tech_items}
    assert "recent" in ids
    assert "old" not in ids


def test_recent_items_at_boundary_kept(manager: FeedManager) -> None:
    """Articoli esattamente a 47h devono essere mantenuti, 49h eliminati."""
    source = manager.add("https://example.com/feed.xml")
    items = [
        _make_item("h47", source.id, 47),
        _make_item("h49", source.id, 49),
    ]
    with patch(
        "core.feed_manager.fetch_and_parse",
        return_value=("Title", items),
    ):
        manager.refresh(source.id)
    refreshed = manager.get(source.id)
    ids = {it.id for it in refreshed.items}
    assert "h47" in ids
    assert "h49" not in ids
