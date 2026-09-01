"""Gerarchia delle eccezioni personalizzate del livello core.

Le eccezioni di dominio core derivano da ``AppError`` definita in
``config/exceptions.py``. Il livello core solleva eccezioni specifiche;
il livello UI le cattura e le presenta all'utente in un dialogo.
"""

from __future__ import annotations

from config.exceptions import AppError, ConfigError, ConfigValidationError


class FeedError(AppError):
    """Errore generico durante l'operazione su un feed."""


class FeedParseError(FeedError):
    """Il contenuto recuperato non è un feed RSS/Atom valido."""

    def __init__(self, url: str, message: str = "") -> None:
        self.url = url
        super().__init__(f"Impossibile analizzare il feed {url}: {message}")


class FeedFetchError(FeedError):
    """Errore di rete durante il recupero del feed."""

    def __init__(self, url: str, cause: str = "") -> None:
        self.url = url
        super().__init__(f"Errore di rete per {url}: {cause}")


class FeedNotFoundError(FeedError):
    """Il feed richiesto non esiste nella raccolta."""

    def __init__(self, feed_id: str) -> None:
        self.feed_id = feed_id
        super().__init__(f"Feed non trovato: {feed_id}")


class FeedDuplicateError(FeedError):
    """Un feed con questo URL esiste già."""

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Feed già presente: {url}")


class RefreshCancelledError(FeedError):
    """Un refresh è stato annullato durante lo shutdown o prima del commit."""

    def __init__(self) -> None:
        super().__init__("Aggiornamento annullato")


class UIError(AppError):
    """Errore generico del livello UI."""


__all__ = [
    "AppError",
    "ConfigError",
    "ConfigValidationError",
    "FeedError",
    "FeedParseError",
    "FeedFetchError",
    "FeedNotFoundError",
    "FeedDuplicateError",
    "RefreshCancelledError",
    "UIError",
]
