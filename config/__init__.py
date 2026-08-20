"""Pacchetto config: costanti, tema e impostazioni dell'applicazione.

Esporta l'interfaccia pubblica del livello configurazione. Questo livello
è puramente dichiarativo e non importa da ``core/`` o ``ui/``.
"""

from __future__ import annotations

from config.constants import (
    AppMeta,
    FeedDefaults,
    Paths,
    Shortcuts,
    UIConstraints,
)
from config.exceptions import AppError, ConfigError, ConfigValidationError
from config.settings import Settings, SettingsManager
from config.theme import (
    ThemeAnimation,
    ThemeColors,
    ThemeFonts,
    ThemeSpacing,
    ThemeTypography,
)

__all__ = [
    "AppMeta",
    "FeedDefaults",
    "Paths",
    "Shortcuts",
    "UIConstraints",
    "AppError",
    "ConfigError",
    "ConfigValidationError",
    "Settings",
    "SettingsManager",
    "ThemeColors",
    "ThemeFonts",
    "ThemeSpacing",
    "ThemeTypography",
    "ThemeAnimation",
]
