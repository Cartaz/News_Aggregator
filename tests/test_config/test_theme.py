"""Regression tests for Dark Neumorphism v6 tokens."""

from __future__ import annotations

from config.constants import UIConstraints
from config.theme import ThemeColors, ThemeDepth, ThemeSpacing, ThemeTypography


def _relative_luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    channels = [int(raw[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def linearize(value: float) -> float:
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(value) for value in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(foreground: str, background: str) -> float:
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def test_exact_background() -> None:
    assert ThemeColors.BG_MAIN.lower() == "#141414"


def test_exact_accent() -> None:
    assert ThemeColors.PRIMARY.lower() == "#ff6600"


def test_true_shadow_pair_has_large_luminance_span() -> None:
    assert ThemeColors.SHADOW_LIGHT.lower() == "#3a3a3a"
    assert ThemeColors.SHADOW_DARK.lower() == "#000000"


def test_shadow_geometry_is_directional() -> None:
    assert ThemeDepth.BUTTON_OFFSET > 0
    assert ThemeDepth.BUTTON_BLUR > ThemeDepth.BUTTON_OFFSET
    assert ThemeDepth.INPUT_OFFSET > 0
    assert ThemeDepth.INPUT_BLUR > ThemeDepth.INPUT_OFFSET


def test_text_contrast() -> None:
    assert _contrast(ThemeColors.TEXT_PRIMARY, ThemeColors.BG_MAIN) >= 4.5
    assert _contrast(ThemeColors.TEXT_SECONDARY, ThemeColors.BG_MAIN) >= 4.5
    assert _contrast(ThemeColors.TEXT_ON_PRIMARY, ThemeColors.PRIMARY) >= 4.5


def test_geometry_tokens_unchanged() -> None:
    assert UIConstraints.WINDOW_MIN_WIDTH == 900
    assert UIConstraints.WINDOW_MIN_HEIGHT == 600
    assert UIConstraints.SOURCE_LIST_MIN_WIDTH == 240
    assert UIConstraints.SOURCE_LIST_MAX_WIDTH == 480

    assert ThemeSpacing.BORDER_RADIUS_SM == 8
    assert ThemeSpacing.BORDER_RADIUS == 12
    assert ThemeSpacing.BORDER_RADIUS_LG == 16
    assert ThemeSpacing.BORDER_RADIUS_XL == 24

    assert ThemeTypography.BODY_SIZE == 12
    assert ThemeTypography.TITLE_SIZE == 16
