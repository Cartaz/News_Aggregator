"""Regression coverage for explicit application composition without singletons."""

from __future__ import annotations

from pathlib import Path

from config.settings import SettingsManager
from core.app_controller import AppController
from core.feed_manager import FeedManager


def test_settings_manager_instances_are_independent(tmp_paths: Path) -> None:
    first = SettingsManager(tmp_paths / "settings-first.json")
    second = SettingsManager(tmp_paths / "settings-second.json")

    assert first is not second

    first.update({"refresh_interval_minutes": 30})

    assert first.settings.refresh_interval_minutes == 30
    assert second.settings.refresh_interval_minutes == 1


def test_app_controller_instances_do_not_share_canonical_state(tmp_paths: Path) -> None:
    first = AppController(
        FeedManager(tmp_paths / "feeds-first.json"),
        SettingsManager(tmp_paths / "controller-first.json"),
    )
    second = AppController(
        FeedManager(tmp_paths / "feeds-second.json"),
        SettingsManager(tmp_paths / "controller-second.json"),
    )

    try:
        assert first is not second
        first.add_feed("https://example.com/first.xml", "First")

        assert [feed.title for feed in first.get_all_feeds()] == ["First"]
        assert second.get_all_feeds() == []
    finally:
        first.shutdown(wait_timeout=1.0)
        second.shutdown(wait_timeout=1.0)


def test_singleton_hooks_are_absent_from_production_classes() -> None:
    root = Path(__file__).resolve().parents[2]
    sources = (
        (root / "core" / "app_controller.py").read_text(encoding="utf-8"),
        (root / "config" / "settings.py").read_text(encoding="utf-8"),
    )

    for source in sources:
        assert "_instance" not in source
        assert "def __new__(" not in source
        assert "_initialized" not in source
