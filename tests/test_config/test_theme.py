"""Tests for the native-shell tokens matching the web design contract."""

from __future__ import annotations

from config.constants import UIConstraints
from config.theme import ThemeColors, ThemeDepth, ThemeSpacing


def test_all_declared_surfaces_are_the_same_material() -> None:
    surfaces = {
        ThemeColors.BG_MAIN,
        ThemeColors.BG_CARD,
        ThemeColors.BG_ELEVATED,
        ThemeColors.BG_INPUT,
        ThemeColors.BG_HOVER,
        ThemeColors.BG_TOOLTIP,
        ThemeColors.BG_SELECTION,
        ThemeColors.SURFACE_HIGH,
        ThemeColors.SURFACE_MID,
        ThemeColors.SURFACE_LOW,
    }
    assert surfaces == {"#141414"}


def test_exact_accent_and_neutral_text_scale() -> None:
    assert ThemeColors.PRIMARY == "#FF6600"
    assert ThemeColors.TEXT_PRIMARY == "#E1E1E1"
    assert ThemeColors.TEXT_SECONDARY == "#878787"
    assert ThemeColors.TEXT_DISABLED == "#5A5A5A"


def test_depth_is_directional_and_radius_hierarchy_matches_contract() -> None:
    assert ThemeDepth.BUTTON_OFFSET > 0
    assert ThemeDepth.BUTTON_BLUR > ThemeDepth.BUTTON_OFFSET
    assert ThemeDepth.INPUT_OFFSET > 0
    assert ThemeDepth.INPUT_BLUR > ThemeDepth.INPUT_OFFSET
    assert (
        ThemeSpacing.BORDER_RADIUS_SM,
        ThemeSpacing.BORDER_RADIUS,
        ThemeSpacing.BORDER_RADIUS_LG,
        ThemeSpacing.BORDER_RADIUS_XL,
    ) == (12, 16, 22, 28)
    assert UIConstraints.WINDOW_MIN_WIDTH == 900
    assert UIConstraints.WINDOW_MIN_HEIGHT == 600
