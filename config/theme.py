"""Centralized Dark Neumorphism design tokens.

The theme intentionally contains no application logic. Geometry tokens mirror the
stable UI baseline; rendering tokens only control how the same rectangles are
painted. The single interaction accent is #FF6600.
"""

from __future__ import annotations


class ThemeColors:
    """Semantic palette for the dark-neumorphic theme."""

    PRIMARY: str = "#FF6600"
    PRIMARY_DARK: str = "#C94F00"
    PRIMARY_SOFT: str = "#FF8A3D"

    DANGER: str = "#E56A65"
    DANGER_DARK: str = "#B04F4B"
    GOOD: str = "#55C98F"

    # Keep the established dark base; depth is created by neighbouring shades.
    BG_MAIN: str = "#141414"
    BG_CARD: str = "#191C20"
    BG_ELEVATED: str = "#1E2227"
    BG_INPUT: str = "#16191D"
    BG_HOVER: str = "#20242A"
    BG_TOOLTIP: str = "#1E2227"
    BG_SELECTION: str = "#332218"

    SURFACE_HIGH: str = "#22272C"
    SURFACE_MID: str = "#1B1F23"
    SURFACE_LOW: str = "#15181B"

    # One virtual light source: upper-left.
    SHADOW_LIGHT: str = "#30363D"
    SHADOW_LIGHT_SOFT: str = "#282E34"
    SHADOW_DARK: str = "#090B0D"
    SHADOW_DARK_SOFT: str = "#0D0F12"

    BORDER: str = "#252A30"
    BORDER_DARK: str = "#0E1013"
    BORDER_SUBTLE: str = "#20252A"
    BORDER_FOCUS: str = PRIMARY

    TEXT_PRIMARY: str = "#ECEFF1"
    TEXT_SECONDARY: str = "#A7ADB4"
    TEXT_DISABLED: str = "#6F757C"
    TEXT_ON_PRIMARY: str = "#111111"

    STATUS_RUNNING: str = GOOD
    STATUS_ERROR: str = DANGER
    STATUS_STOPPED: str = TEXT_DISABLED
    STATUS_PAUSED: str = PRIMARY

    LINK: str = PRIMARY
    LINK_VISITED: str = PRIMARY_SOFT


class ThemeFonts:
    SANS: str = "Noto Sans"
    MONO: str = "Sarasa Mono SC"
    FALLBACK_SANS: str = "Sans Serif"
    FALLBACK_MONO: str = "Monospace"


class ThemeSpacing:
    # Stable geometry tokens — deliberately unchanged from the baseline.
    XS: int = 4
    SM: int = 8
    MD: int = 12
    LG: int = 16
    XL: int = 24
    XXL: int = 32

    BORDER_RADIUS_SM: int = 8
    BORDER_RADIUS: int = 12
    BORDER_RADIUS_LG: int = 16
    BORDER_RADIUS_XL: int = 24

    BORDER_WIDTH: int = 1
    STATUS_INDICATOR_SIZE: int = 8


class ThemeTypography:
    CARD_HEADER_SIZE: int = 13
    CARD_HEADER_WEIGHT: int = 600
    CARD_HEADER_LETTER_SPACING: float = 0.5

    BUTTON_SIZE: int = 12
    BUTTON_WEIGHT: int = 600

    BODY_SIZE: int = 12
    BODY_WEIGHT: int = 400

    BADGE_SIZE: int = 10
    BADGE_WEIGHT: int = 500

    TITLE_SIZE: int = 16
    TITLE_WEIGHT: int = 700

    SUBTITLE_SIZE: int = 14
    SUBTITLE_WEIGHT: int = 500


class ThemeAnimation:
    DURATION_FAST_MS: int = 140
    DURATION_NORMAL_MS: int = 220
    DURATION_SLOW_MS: int = 300

    EASE_OUT: str = "OutCubic"
    EASE_IN_OUT: str = "InOutCubic"


class ThemeDepth:
    """Rendering-only tokens. They never participate in layouts."""

    BUTTON_SURFACE_INSET: float = 5.0
    BADGE_SURFACE_INSET: float = 3.0

    BUTTON_BLUR: float = 7.5
    BUTTON_OFFSET: float = 3.5
    BUTTON_DARK_ALPHA: int = 205
    BUTTON_LIGHT_ALPHA: int = 150

    BUTTON_HOVER_BLUR: float = 8.5
    BUTTON_HOVER_OFFSET: float = 3.5
    BUTTON_HOVER_DARK_ALPHA: int = 218
    BUTTON_HOVER_LIGHT_ALPHA: int = 176

    BADGE_BLUR: float = 5.0
    BADGE_OFFSET: float = 2.5
    BADGE_DARK_ALPHA: int = 185
    BADGE_LIGHT_ALPHA: int = 130

    INPUT_DEPTH: float = 10.0
    INPUT_DARK_ALPHA: int = 160
    INPUT_LIGHT_ALPHA: int = 82

    PANEL_DEPTH: float = 14.0
    PANEL_DARK_ALPHA: int = 138
    PANEL_LIGHT_ALPHA: int = 68


__all__ = [
    "ThemeAnimation",
    "ThemeColors",
    "ThemeDepth",
    "ThemeFonts",
    "ThemeSpacing",
    "ThemeTypography",
]
