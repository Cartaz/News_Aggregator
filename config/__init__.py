"""Public configuration surface for constants and application settings.

This package is declarative and does not import from ``core`` or ``ui``.
Presentation tokens belong to ``ui/web/styles.css``; native Qt presentation
keeps its small platform-specific styling inside ``ui``.
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
]
