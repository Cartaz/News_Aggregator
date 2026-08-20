"""Event bus centrale per la comunicazione tra moduli.

Implementa un sistema publish/subscribe tipizzato a runtime. Il bus è
un singleton accessibile globalmente. Non blocca il thread emittente:
gli handler vengono eseguiti sincronamente nel thread dell'emittente;
per operazioni lunghe, delegare a un worker thread.

Regola critica (Appendice D.1): questo modulo NON importa MAI moduli Qt
(``PySide6``, ``PyQt6``). Per aggiornamenti GUI thread-safe, usare il
bridge nel livello ``ui/event_bridge.py``.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], None]


class EventBus:
    """Canale di comunicazione asincrona tra tutti i moduli.

    Pattern singleton. Supporta registrazione, emissione e
    deregistrazione di handler per tipo di evento.
    """

    _instance: EventBus | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> EventBus:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._init_state()
                    cls._instance = instance
        return cls._instance

    def _init_state(self) -> None:
        """Inizializza lo stato interno (chiamato una sola volta)."""
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._event_lock: threading.RLock = threading.RLock()

    @classmethod
    def reset(cls) -> None:
        """Resetta il singleton (per test)."""
        with cls._lock:
            cls._instance = None

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Registra un handler per un tipo di evento.

        Args:
            event_name: Nome evento (pattern ``modulo_azione_stato``).
            handler: Callable richiamato con il payload dict.
        """
        with self._event_lock:
            if handler not in self._handlers[event_name]:
                self._handlers[event_name].append(handler)
        logger.debug("Handler registrato per evento '%s'", event_name)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Deregistra un handler precedentemente registrato."""
        with self._event_lock:
            if handler in self._handlers[event_name]:
                self._handlers[event_name].remove(handler)
                logger.debug("Handler rimosso per evento '%s'", event_name)

    def emit(self, event_name: str, payload: dict[str, Any] | None = None) -> None:
        """Emette un evento a tutti gli handler registrati.

        Gli handler sono eseguiti sincronamente nel thread corrente.
        Le eccezioni in un handler non bloccano gli altri handler.

        Args:
            event_name: Nome evento.
            payload: Dati associati all'evento.
        """
        data: dict[str, Any] = payload or {}
        with self._event_lock:
            handlers: list[EventHandler] = list(self._handlers.get(event_name, []))
        logger.debug(
            "Evento '%s' emesso a %d handler", event_name, len(handlers)
        )
        for handler in handlers:
            try:
                handler(data)
            except Exception as exc:
                logger.error(
                    "Errore in handler per evento '%s': %s",
                    event_name,
                    exc,
                    exc_info=True,
                )

    def clear(self) -> None:
        """Rimuove tutti gli handler (per test)."""
        with self._event_lock:
            self._handlers.clear()

    def handler_count(self, event_name: str) -> int:
        """Restituisce il numero di handler registrati per evento."""
        with self._event_lock:
            return len(self._handlers.get(event_name, []))


__all__ = ["EventBus", "EventHandler"]
