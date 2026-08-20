"""Test per config/settings.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from config.settings import Settings, SettingsManager
from core.exceptions import ConfigError, ConfigValidationError


def test_default_settings(tmp_paths: Path) -> None:
    """Le impostazioni di default devono avere valori attesi."""
    SettingsManager._instance = None  # reset singleton
    manager: SettingsManager = SettingsManager()
    assert manager.settings.refresh_interval_minutes == 1  # 60 secondi
    assert manager.settings.max_items_per_feed == 50
    assert manager.settings.mark_read_on_select is True


def test_save_and_load(tmp_paths: Path) -> None:
    """Il salvataggio deve persistere e il caricamento deve ripristinare."""
    SettingsManager._instance = None
    manager: SettingsManager = SettingsManager()
    manager.set("refresh_interval_minutes", 30)
    SettingsManager._instance = None
    loaded: SettingsManager = SettingsManager()
    assert loaded.settings.refresh_interval_minutes == 30


def test_invalid_value_raises(tmp_paths: Path) -> None:
    """Valori fuori limite devono sollevare ConfigValidationError."""
    SettingsManager._instance = None
    manager: SettingsManager = SettingsManager()
    with pytest.raises(ConfigValidationError):
        manager.set("refresh_interval_minutes", -1)
    with pytest.raises(ConfigValidationError):
        manager.set("max_items_per_feed", 0)
    with pytest.raises(ConfigValidationError):
        manager.set("font_scale_factor", 5.0)


def test_invalid_key_raises(tmp_paths: Path) -> None:
    """Chiavi inesistenti devono sollevare ConfigError."""
    SettingsManager._instance = None
    manager: SettingsManager = SettingsManager()
    with pytest.raises(ConfigError):
        manager.get("nonexistent_key")
    with pytest.raises(ConfigError):
        manager.set("nonexistent_key", 1)


def test_reset(tmp_paths: Path) -> None:
    """reset() deve ripristinare i valori predefiniti."""
    SettingsManager._instance = None
    manager: SettingsManager = SettingsManager()
    manager.set("refresh_interval_minutes", 30)
    manager.reset()
    assert manager.settings.refresh_interval_minutes == 1  # 60 secondi


def test_corrupt_file_falls_back(tmp_paths: Path) -> None:
    """File corrotto deve ricadere sui valori predefiniti."""
    SettingsManager._instance = None
    settings_path: Path = tmp_paths / "config" / "news-aggregator" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("{ invalid json", encoding="utf-8")
    manager: SettingsManager = SettingsManager()
    assert manager.settings.refresh_interval_minutes == 1  # 60 secondi
