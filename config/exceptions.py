"""Eccezioni del livello configurazione.

Definisce la classe base ``AppError`` per tutte le eccezioni
dell'applicazione e le eccezioni specifiche del dominio configurazione.

Questo modulo è il livello più basso della gerarchia delle eccezioni:
NON importa da ``core/`` né da ``ui/``. Le eccezioni specifiche del
dominio core (FeedError, ecc.) in ``core/exceptions.py`` derivano da
``AppError`` definita qui.
"""

from __future__ import annotations


class AppError(Exception):
    """Classe base per tutte le eccezioni dell'applicazione."""


class ConfigError(AppError):
    """Errore nella gestione della configurazione o delle impostazioni."""


class ConfigValidationError(ConfigError):
    """Validazione fallita per un valore di configurazione."""


__all__ = ["AppError", "ConfigError", "ConfigValidationError"]
