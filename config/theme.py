"""Centralized Dark Neumorphism design tokens.

The visible application background is exactly ``rgb(20, 20, 20)`` /
``#141414``.

Depth is not simulated by 1 px QSS bevels.  Real multi-layer inset/outset
shadows are rendered by :mod:`ui.styles.box_shadow_effect`, a pure-PySide6
``QGraphicsEffect`` implementation.

Geometry tokens intentionally match the stable application baseline.
"""

from __future__ import annotations


class ThemeColors:
    """Semantic palette for the single dark-neumorphic theme."""

    PRIMARY: str = "#FF6600"
    PRIMARY_DARK: str = "#CC5200"
    PRIMARY_SOFT: str = "#FF8A3D"

    DANGER: str = "#E56A65"
    DANGER_DARK: str = "#B04F4B"
    GOOD: str = "#55C98F"

    # Mandatory base material.
    BG_MAIN: str = "#141414"

    # Surfaces are intentionally close to the base. Light/shadow creates shape.
    BG_CARD: str = "#181818"
    BG_ELEVATED: str = "#1B1B1B"
    BG_INPUT: str = "#171717"
    BG_HOVER: str = "#1D1D1D"
    BG_TOOLTIP: str = "#1B1B1B"
    BG_SELECTION: str = "#3A2518"

    SURFACE_HIGH: str = "#1E1E1E"
    SURFACE_MID: str = "#191919"
    SURFACE_LOW: str = "#161616"

    # One virtual light source: upper-left.
    SHADOW_LIGHT: str = "#3A3A3A"
    SHADOW_LIGHT_SOFT: str = "#303030"
    SHADOW_DARK: str = "#000000"
    SHADOW_DARK_SOFT: str = "#050505"

    BORDER: str = "#242424"
    BORDER_DARK: str = "#080808"
    BORDER_SUBTLE: str = "#202020"
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
    # Stable geometry tokens — deliberately unchanged.
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
    DURATION_FAST_MS: int = 150
    DURATION_NORMAL_MS: int = 250
    DURATION_SLOW_MS: int = 300

    EASE_OUT: str = "OutCubic"
    EASE_IN_OUT: str = "InOutCubic"


class ThemeDepth:
    """Pure rendering tokens — no layout dimensions are defined here."""

    # Raised control source is painted slightly inside its existing QWidget
    # rect so the blurred lobes have room without changing the widget geometry.
    BUTTON_SURFACE_INSET: float = 5.0
    BADGE_SURFACE_INSET: float = 2.5

    BUTTON_BLUR: float = 8.0
    BUTTON_OFFSET: float = 5.5
    BUTTON_DARK_ALPHA: int = 215
    BUTTON_LIGHT_ALPHA: int = 178

    BUTTON_HOVER_BLUR: float = 9.0
    BUTTON_HOVER_OFFSET: float = 5.0
    BUTTON_HOVER_DARK_ALPHA: int = 225
    BUTTON_HOVER_LIGHT_ALPHA: int = 195

    BADGE_BLUR: float = 5.5
    BADGE_OFFSET: float = 3.5
    BADGE_DARK_ALPHA: int = 205
    BADGE_LIGHT_ALPHA: int = 155

    INPUT_BLUR: float = 8.0
    INPUT_OFFSET: float = 5.0
    INPUT_DARK_ALPHA: int = 220
    INPUT_LIGHT_ALPHA: int = 105

    PANEL_BLUR: float = 11.0
    PANEL_OFFSET: float = 6.0
    PANEL_DARK_ALPHA: int = 190
    PANEL_LIGHT_ALPHA: int = 85
