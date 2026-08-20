"""Palette lock for the user's final color decision."""

from __future__ import annotations

import hashlib
from pathlib import Path

from config.theme import ThemeColors


EXPECTED_THEME_SHA256 = "8ef1b1e4c94c0ecb8b92d41d931f347b506cf8084d77ef8b2c2a7749e9b1d806"


def test_theme_palette_file_is_locked() -> None:
    path = Path(__file__).resolve().parents[2] / "config" / "theme.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_THEME_SHA256


def test_locked_key_colors() -> None:
    assert ThemeColors.BG_MAIN == "#141414"
    assert ThemeColors.PRIMARY == "#FF6600"
    assert ThemeColors.BG_CARD == "#181818"
    assert ThemeColors.BG_INPUT == "#171717"
    assert ThemeColors.SHADOW_LIGHT == "#3A3A3A"
    assert ThemeColors.SHADOW_DARK == "#000000"
    assert ThemeColors.BG_SELECTION == "#3A2518"
