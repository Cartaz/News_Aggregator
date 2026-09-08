"""Persistent user settings behind one validated Python abstraction."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
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

    def __init__(self, path: Path | None = None) -> None:
        self._path: Path = path or Paths.SETTINGS_FILE
        self._settings: Settings = Settings()
        self._callbacks: list[ChangeCallback] = []
        self._state_lock = threading.RLock()
        self._write_lock = threading.Lock()
        self.load()

    @property
    def settings(self) -> Settings:
        """Return a detached read snapshot; writes go through ``update``."""
        return self.snapshot()

    def snapshot(self) -> Settings:
        """Return a detached copy without waiting for filesystem I/O."""
        with self._state_lock:
            return Settings(**asdict(self._settings))

    def register_change_callback(self, cb: ChangeCallback) -> None:
        with self._state_lock:
            if cb not in self._callbacks:
                self._callbacks.append(cb)

    @staticmethod
    def _candidate_from_raw(raw: Any) -> Settings:
        """Build a current-schema candidate while tolerating obsolete keys."""
        if not isinstance(raw, dict):
            raise TypeError("Il file impostazioni deve contenere un oggetto JSON")

        known_keys = {field.name for field in fields(Settings)}
        unknown_keys = sorted(set(raw) - known_keys)
        if unknown_keys:
            logger.info(
                "Ignoro chiavi impostazioni obsolete o sconosciute: %s",
                ", ".join(unknown_keys),
            )

        candidate = Settings(
            **{key: value for key, value in raw.items() if key in known_keys}
        )
        candidate.validate()
        return candidate

    def load(self) -> Settings:
        """Load one validated candidate and publish it atomically in memory."""
        Paths.ensure_user_dirs()
        candidate = Settings()
        if not self._path.exists():
            logger.info("File impostazioni non trovato, uso default: %s", self._path)
        else:
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                candidate = self._candidate_from_raw(raw)
            except OSError as exc:
                logger.warning("Impostazioni non leggibili, uso default: %s", exc)
                candidate = Settings()
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning("Impostazioni corrotte, reset ai default: %s", exc)
                candidate = Settings()
            except ConfigValidationError as exc:
                logger.warning("Impostazioni non valide, reset ai default: %s", exc)
                candidate = Settings()

        with self._state_lock:
            self._settings = candidate
        return self.snapshot()

    def _persist(self, candidate: Settings) -> None:
        """Write one detached validated candidate without publishing it in memory."""
        Paths.ensure_user_dirs()
        candidate.validate()
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        try:
            temporary.write_text(
                json.dumps(asdict(candidate), indent=2),
                encoding="utf-8",
            )
            temporary.replace(self._path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logger.debug("Impossibile rimuovere settings temporanee", exc_info=True)
            raise ConfigError(f"Impossibile salvare le impostazioni: {exc}") from exc

    def save(self) -> None:
        """Persist the current canonical snapshot, then notify listeners."""
        with self._write_lock:
            candidate = self.snapshot()
            self._persist(candidate)
        self._notify_change(candidate)

    def get(self, key: str) -> Any:
        snapshot = self.snapshot()
        if not hasattr(snapshot, key):
            raise ConfigError(f"Chiave impostazione non valida: {key}")
        return getattr(snapshot, key)

    def update(self, changes: Mapping[str, Any]) -> Settings:
        """Persist a validated candidate before publishing it as canonical state."""
        with self._write_lock:
            candidate = self.snapshot()
            for key, value in changes.items():
                if not hasattr(candidate, key):
                    raise ConfigError(f"Chiave impostazione non valida: {key}")
                setattr(candidate, key, value)
            candidate.validate()
            self._persist(candidate)
            with self._state_lock:
                self._settings = candidate

        committed = self.snapshot()
        self._notify_change(committed)
        return committed

    def set(self, key: str, value: Any) -> None:
        self.update({key: value})

    def reset(self) -> None:
        candidate = Settings()
        with self._write_lock:
            self._persist(candidate)
            with self._state_lock:
                self._settings = candidate
        self._notify_change(candidate)

    def _notify_change(self, settings: Settings | None = None) -> None:
        snapshot = (
            Settings(**asdict(settings))
            if settings is not None
            else self.snapshot()
        )
        with self._state_lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(Settings(**asdict(snapshot)))
            except Exception as exc:
                logger.error(
                    "Errore in callback change_callback: %s",
                    exc,
                    exc_info=True,
                )


__all__ = ["Settings", "SettingsManager", "ChangeCallback", "AppMeta"]
