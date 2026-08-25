"""Test per config/settings.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from config.settings import Settings, SettingsManager
from core.exceptions import ConfigError, ConfigValidationError


def test_default_settings(tmp_paths: Path) -> None:
    SettingsManager._instance = None
    manager = SettingsManager()
    assert manager.settings.refresh_interval_minutes == 1
    assert manager.settings.max_items_per_feed == 50
    assert manager.settings.mark_read_on_select is True


def test_save_and_load(tmp_paths: Path) -> None:
    SettingsManager._instance = None
    manager = SettingsManager()
    manager.set("refresh_interval_minutes", 30)
    SettingsManager._instance = None
    loaded = SettingsManager()
    assert loaded.settings.refresh_interval_minutes == 30


def test_invalid_value_raises_without_mutating_canonical_state(tmp_paths: Path) -> None:
    SettingsManager._instance = None
    manager = SettingsManager()

    with pytest.raises(ConfigValidationError):
        manager.update({"refresh_interval_minutes": -1})

    assert manager.settings.refresh_interval_minutes == 1

    with pytest.raises(ConfigValidationError):
        manager.set("max_items_per_feed", 0)
    with pytest.raises(ConfigValidationError):
        manager.set("font_scale_factor", 5.0)


def test_update_commits_multiple_values_together(tmp_paths: Path) -> None:
    SettingsManager._instance = None
    manager = SettingsManager()

    updated = manager.update(
        {
            "refresh_interval_minutes": 30,
            "show_unread_only": True,
        }
    )

    assert updated.refresh_interval_minutes == 30
    assert updated.show_unread_only is True
    persisted = json.loads(manager._path.read_text(encoding="utf-8"))
    assert persisted["refresh_interval_minutes"] == 30
    assert persisted["show_unread_only"] is True


def test_snapshot_is_detached_from_canonical_settings(tmp_paths: Path) -> None:
    SettingsManager._instance = None
    manager = SettingsManager()
    snapshot = manager.snapshot()

    snapshot.refresh_interval_minutes = 60

    assert manager.settings.refresh_interval_minutes == 1


def test_invalid_key_raises(tmp_paths: Path) -> None:
    SettingsManager._instance = None
    manager = SettingsManager()
    with pytest.raises(ConfigError):
        manager.get("nonexistent_key")
    with pytest.raises(ConfigError):
        manager.set("nonexistent_key", 1)


def test_reset(tmp_paths: Path) -> None:
    SettingsManager._instance = None
    manager = SettingsManager()
    manager.set("refresh_interval_minutes", 30)
    manager.reset()
    assert manager.settings.refresh_interval_minutes == 1


def test_corrupt_file_falls_back(tmp_paths: Path) -> None:
    SettingsManager._instance = None
    settings_path = tmp_paths / "config" / "news-aggregator" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("{ invalid json", encoding="utf-8")
    manager = SettingsManager()
    assert manager.settings.refresh_interval_minutes == 1


def test_unreadable_file_falls_back_to_defaults(tmp_paths: Path) -> None:
    SettingsManager._instance = None
    settings_path = tmp_paths / "config" / "news-aggregator" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("{}", encoding="utf-8")

    with patch("pathlib.Path.read_text", side_effect=OSError("permission denied")):
        manager = SettingsManager()

    assert manager.settings.refresh_interval_minutes == 1
