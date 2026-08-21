"""Hard acceptance checks for the new monochrome neumorphic palette."""

from __future__ import annotations

from config.theme import ThemeColors


def test_locked_key_colors() -> None:
    assert ThemeColors.SURFACE == "#141414"
    assert ThemeColors.PRIMARY == "#FF6600"
    assert ThemeColors.BG_CARD == ThemeColors.SURFACE
    assert ThemeColors.BG_INPUT == ThemeColors.SURFACE
    assert ThemeColors.BG_ELEVATED == ThemeColors.SURFACE
    assert ThemeColors.SHADOW_LIGHT == "#4B4B4B"
    assert ThemeColors.SHADOW_DARK == "#000000"
