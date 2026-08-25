"""Persistent user settings behind one validated Python abstraction."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from config.constants import AppMeta, FeedDefaults, Paths, UIConstraints
from config.exceptions import ConfigError, ConfigValidationError

logger = logging.getLogger(__name__)

ChangeCallback = Callable[["Settings"], None]


@dataclass
class Settings:
    """Schema and defaults for persisted user settings."""

    refresh_interval_minutes: int = 1
    max_items_per_feed: int = FeedDefaults.MAX_ITEMS_PER_FEED
    mark_read_on_select: bool = True
    show_unread_only: bool = False
    font_scale_factor: float = 1.0
    window_width: int = UIConstraints.WINDOW_DEFAULT_WIDTH
    window_height: int = UIConstraints.WINDOW_DEFAULT_HEIGHT
    source_split_width: int = UIConstraints.SOURCE_LIST_MIN_WIDTH
    notify_new_items: bool = False
    close_to_tray: bool = True

    def validate(self) -> None:
        if self.refresh_interval_minutes < 1:
            raise ConfigValidationError(
                "refresh_interval_minutes deve essere >= 1"
            )
        if self.max_items_per_feed < 1 or self.max_items_per_feed > 500:
            raise ConfigValidationError(
                "max_items_per_feed deve essere tra 1 e 500"
            )
        if not 0.5 <= self.font_scale_factor <= 2.0:
            raise ConfigValidationError(
                "font_scale_factor deve essere tra 0.5 e 2.0"
            )


class SettingsManager:
    """Load, validate and atomically persist application settings."""

    _instance: SettingsManager | None = None

    def __new__(cls, *args: Any, **kwargs: Any) -> SettingsManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, path: Path | None = None) -> None:
        if getattr(self, "_initialized", False):
            return
        self._path: Path = path or Paths.SETTINGS_FILE
        self._settings: Settings = Settings()
        self._callbacks: list[ChangeCallback] = []
        self._initialized = True
        self.load()

    @property
    def settings(self) -> Settings:
        """Return the canonical settings object for read access."""
        return self._settings

    def snapshot(self) -> Settings:
        """Return a detached copy suitable for external consumers."""
        return Settings(**asdict(self._settings))

    def register_change_callback(self, cb: ChangeCallback) -> None:
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def load(self) -> Settings:
        Paths.ensure_user_dirs()
        if not self._path.exists():
            logger.info("File impostazioni non trovato, uso default: %s", self._path)
            self._settings = Settings()
            return self._settings
        try:
            raw: dict[str, Any] = json.loads(self._path.read_text(encoding="utf-8"))
            candidate = Settings(**raw)
            candidate.validate()
            self._settings = candidate
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Impostazioni corrotte, reset ai default: %s", exc)
            self._settings = Settings()
        except ConfigValidationError as exc:
            logger.warning("Impostazioni non valide, reset ai default: %s", exc)
            self._settings = Settings()
        return self._settings

    def save(self) -> None:
        """Persist the canonical settings atomically, then notify listeners."""
        Paths.ensure_user_dirs()
        self._settings.validate()
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        try:
            temporary.write_text(
                json.dumps(asdict(self._settings), indent=2),
                encoding="utf-8",
            )
            temporary.replace(self._path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logger.debug("Impossibile rimuovere settings temporanee", exc_info=True)
            raise ConfigError(f"Impossibile salvare le impostazioni: {exc}") from exc
        self._notify_change()

    def get(self, key: str) -> Any:
        if not hasattr(self._settings, key):
            raise ConfigError(f"Chiave impostazione non valida: {key}")
        return getattr(self._settings, key)

    def update(self, changes: Mapping[str, Any]) -> Settings:
        """Validate a complete candidate before replacing canonical settings."""
        candidate = self.snapshot()
        for key, value in changes.items():
            if not hasattr(candidate, key):
                raise ConfigError(f"Chiave impostazione non valida: {key}")
            setattr(candidate, key, value)
        candidate.validate()

        previous = self._settings
        self._settings = candidate
        try:
            self.save()
        except Exception:
            self._settings = previous
            raise
        return self.snapshot()

    def set(self, key: str, value: Any) -> None:
        self.update({key: value})

    def reset(self) -> None:
        previous = self._settings
        self._settings = Settings()
        try:
            self.save()
        except Exception:
            self._settings = previous
            raise

    def _notify_change(self) -> None:
        snapshot = self.snapshot()
        for cb in self._callbacks:
            try:
                cb(snapshot)
            except Exception as exc:
                logger.error(
                    "Errore in callback change_callback: %s",
                    exc,
                    exc_info=True,
                )


__all__ = ["Settings", "SettingsManager", "ChangeCallback", "AppMeta"]
