"""Declarative visual tokens shared by the native desktop shell.

The HTML interface owns its full design system in CSS custom properties.
These values exist only for native Qt surfaces such as the system tray and
for compatibility with callers importing :mod:`config.theme`.
"""

from __future__ import annotations


class ThemeColors:
    """Mandatory monochrome dark-neumorphism palette."""

    SURFACE: str = "#141414"
    BG_MAIN: str = SURFACE
    BG_CARD: str = SURFACE
    BG_ELEVATED: str = SURFACE
    BG_INPUT: str = SURFACE
    BG_HOVER: str = SURFACE
    BG_TOOLTIP: str = SURFACE
    BG_SELECTION: str = SURFACE
    SURFACE_HIGH: str = SURFACE
    SURFACE_MID: str = SURFACE
    SURFACE_LOW: str = SURFACE

    PRIMARY: str = "#FF6600"
    BORDER_FOCUS: str = PRIMARY
    LINK: str = PRIMARY

    TEXT_PRIMARY: str = "#E1E1E1"
    TEXT_SECONDARY: str = "#878787"
    TEXT_DISABLED: str = "#5A5A5A"
    TEXT_ON_PRIMARY: str = SURFACE

    SHADOW_LIGHT: str = "#4B4B4B"
    SHADOW_DARK: str = "#000000"
    BORDER: str = "#141414"
    BORDER_SUBTLE: str = "#141414"


class ThemeFonts:
    SANS: str = "Inter"
    MONO: str = "ui-monospace"
    FALLBACK_SANS: str = "Sans Serif"
    FALLBACK_MONO: str = "Monospace"


class ThemeSpacing:
    XS: int = 4
    SM: int = 8
    MD: int = 12
    LG: int = 16
    XL: int = 24
    XXL: int = 32
    BORDER_RADIUS_SM: int = 12
    BORDER_RADIUS: int = 16
    BORDER_RADIUS_LG: int = 22
    BORDER_RADIUS_XL: int = 28
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
    DURATION_FAST_MS: int = 180
    DURATION_NORMAL_MS: int = 220
    DURATION_SLOW_MS: int = 220
    EASE_OUT: str = "OutCubic"
    EASE_IN_OUT: str = "InOutCubic"


class ThemeDepth:
    """Compatibility constants mirroring the CSS shadow direction."""

    BUTTON_SURFACE_INSET: float = 0.0
    BADGE_SURFACE_INSET: float = 0.0
    BUTTON_BLUR: float = 14.0
    BUTTON_OFFSET: float = 6.0
    BUTTON_DARK_ALPHA: int = 166
    BUTTON_LIGHT_ALPHA: int = 33
    BUTTON_HOVER_BLUR: float = 16.0
    BUTTON_HOVER_OFFSET: float = 7.0
    BUTTON_HOVER_DARK_ALPHA: int = 179
    BUTTON_HOVER_LIGHT_ALPHA: int = 38
    BADGE_BLUR: float = 12.0
    BADGE_OFFSET: float = 5.0
    BADGE_DARK_ALPHA: int = 166
    BADGE_LIGHT_ALPHA: int = 33
    INPUT_BLUR: float = 7.0
    INPUT_OFFSET: float = 3.0
    INPUT_DARK_ALPHA: int = 184
    INPUT_LIGHT_ALPHA: int = 28
    PANEL_BLUR: float = 24.0
    PANEL_OFFSET: float = 10.0
    PANEL_DARK_ALPHA: int = 199
    PANEL_LIGHT_ALPHA: int = 41
