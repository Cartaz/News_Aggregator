"""Gestione delle impostazioni utente persistenti.

Le impostazioni sono salvate in JSON nella directory XDG appropriata
(~/.config/news-aggregator/settings.json). Il modulo espone un hook di
callback ``register_change_callback`` che altri moduli (es. il controller)
possono usare per reagire ai cambiamenti senza creare dipendenze inverse.

Questo modulo NON importa dal livello ``core/`` né da ``ui/``:
``config/`` è puramente dichiarativo (vincolo §5.1.4).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from config.constants import AppMeta, FeedDefaults, Paths, UIConstraints
from config.exceptions import ConfigError, ConfigValidationError

logger = logging.getLogger(__name__)

ChangeCallback = Callable[["Settings"], None]


@dataclass
class Settings:
    """Schema delle impostazioni utente con valori predefiniti.

    Attributes:
        refresh_interval_minutes: Intervallo di refresh automatico.
        max_items_per_feed: Numero massimo di articoli mantenuti per feed.
        mark_read_on_select: Marca automaticamente un articolo come letto
            quando viene selezionato.
        show_unread_only: Mostra solo gli articoli non letti nella vista.
        font_scale_factor: Fattore di scala tipografico accessibilità.
        window_width: Larghezza ultima finestra.
        window_height: Altezza ultima finestra.
        source_split_width: Larghezza pannello sorgenti.
        notify_new_items: Mostra notifica desktop per nuovi articoli.
        close_to_tray: Se True, la chiusura della finestra con la X
            nasconde la finestra e mantiene attiva la tray icon (con
            badge del numero di articoli non letti). Per uscire
            davvero usare Ctrl+Q o "Esci" dal menu tray.
    """

    refresh_interval_minutes: int = 1  # 60 secondi (vincolo utente #3)
    max_items_per_feed: int = FeedDefaults.MAX_ITEMS_PER_FEED
    mark_read_on_select: bool = True
    show_unread_only: bool = False
    font_scale_factor: float = 1.0
    window_width: int = UIConstraints.WINDOW_DEFAULT_WIDTH
    window_height: int = UIConstraints.WINDOW_DEFAULT_HEIGHT
    source_split_width: int = UIConstraints.SOURCE_LIST_MIN_WIDTH
    notify_new_items: bool = False  # l'utente non vuole essere disturbato
    # Quando True, la chiusura della finestra con la X NON esce dall'app:
    # nasconde la finestra e mantiene attiva la tray icon con il badge
    # del numero di articoli non letti. Per uscire davvero usare Ctrl+Q
    # o "Esci" dal menu tray.
    close_to_tray: bool = True

    def validate(self) -> None:
        """Valida i vincoli delle impostazioni.

        Raises:
            ConfigValidationError: Se un valore è fuori dai limiti ammessi.
        """
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
    """Loader/saver delle impostazioni utente in formato JSON.

    Implementa il pattern singleton con stato incapsulato. Le modifiche
    vengono notificate ai callback registrati tramite
    ``register_change_callback`` (tipicamente l'AppController, che poi
    emette ``config_changed`` sull'EventBus).
    """

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
        self._initialized: bool = True
        self.load()

    @property
    def settings(self) -> Settings:
        """Restituisce l'istanza corrente delle impostazioni."""
        return self._settings

    def register_change_callback(self, cb: ChangeCallback) -> None:
        """Registra un callback richiamato a ogni modifica salvata.

        Args:
            cb: Funzione che riceve le nuove impostazioni.
        """
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def load(self) -> Settings:
        """Carica le impostazioni da disco.

        Returns:
            Le impostazioni caricate.
        """
        Paths.ensure_user_dirs()
        if not self._path.exists():
            logger.info("File impostazioni non trovato, uso default: %s", self._path)
            self._settings = Settings()
            return self._settings
        try:
            raw: dict[str, Any] = json.loads(self._path.read_text(encoding="utf-8"))
            self._settings = Settings(**raw)
            self._settings.validate()
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Impostazioni corrotte, reset ai default: %s", exc)
            self._settings = Settings()
        except ConfigValidationError as exc:
            logger.warning("Impostazioni non valide, reset ai default: %s", exc)
            self._settings = Settings()
        return self._settings

    def save(self) -> None:
        """Salva le impostazioni su disco e notifica i callback.

        Raises:
            ConfigError: Se la scrittura su disco fallisce.
        """
        Paths.ensure_user_dirs()
        self._settings.validate()
        try:
            self._path.write_text(
                json.dumps(asdict(self._settings), indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ConfigError(f"Impossibile salvare le impostazioni: {exc}") from exc
        self._notify_change()

    def get(self, key: str) -> Any:
        """Restituisce il valore di un'impostazione per chiave."""
        if not hasattr(self._settings, key):
            raise ConfigError(f"Chiave impostazione non valida: {key}")
        return getattr(self._settings, key)

    def set(self, key: str, value: Any) -> None:
        """Imposta un valore e salva immediatamente.

        Args:
            key: Nome dell'attributo in ``Settings``.
            value: Nuovo valore.

        Raises:
            ConfigError: Se la chiave non esiste.
            ConfigValidationError: Se il valore non è valido.
        """
        if not hasattr(self._settings, key):
            raise ConfigError(f"Chiave impostazione non valida: {key}")
        setattr(self._settings, key, value)
        self._settings.validate()
        self.save()

    def reset(self) -> None:
        """Ripristina i valori predefiniti."""
        self._settings = Settings()
        self.save()

    def _notify_change(self) -> None:
        """Notifica tutti i callback registrati del cambiamento."""
        snapshot: Settings = Settings(**asdict(self._settings))
        for cb in self._callbacks:
            try:
                cb(snapshot)
            except Exception as exc:
                logger.error(
                    "Errore in callback change_callback: %s",
                    exc,
                    exc_info=True,
                )


# Compatibility re-export per non rompere i client esistenti
# che facevano from config.settings import EventBus (mai usato realmente)
__all__ = ["Settings", "SettingsManager", "ChangeCallback", "AppMeta"]
