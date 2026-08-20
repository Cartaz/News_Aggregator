"""Bridge thread-safe tra ``EventBus`` (core) e il thread Qt principale.

Quando un evento viene emesso da un thread worker, il callback viene
marshallato sul thread Qt principale tramite un **segnale Qt cross-thread**
(``_dispatch_signal``). Il segnale è connesso al metodo ``_on_dispatched``
con ``Qt.AutoConnection``, che diventa ``Qt.QueuedConnection`` quando
il mittente e il ricevitore sono in thread diversi.

Questo è il pattern corretto per PySide6: ``QTimer.singleShot`` da un
thread Python non-Qt NON marshalla in modo affidabile al thread
principale, e causa warning come::

    QBasicTimer::start: Timers cannot be started from another thread

Regola critica (Appendice D.1): ``QApplication.invokeLater`` NON ESISTE
in PySide6/PyQt6.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class EventBridge(QObject):
    """Iscrive handler Qt-safe agli eventi del bus.

    Gli handler registrati tramite questo bridge sono garantiti
    eseguiti sul thread Qt principale, anche se l'evento è emesso da
    un thread worker, tramite un segnale Qt cross-thread.

    Args:
        parent: QObject genitore opzionale.
    """

    # Segnale cross-thread: emesso dal worker thread, ricevuto nel main.
    # Il payload è ``dict[str, Any]`` ma usiamo ``object`` per evitare
    # problemi di risoluzione del tipo al momento della connessione.
    _dispatch_signal = Signal(str, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._bus: EventBus = EventBus()
        self._callbacks: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        self._wrappers: list[tuple[str, Callable[[dict[str, Any]], None]]] = []
        # AutoConnection diventa QueuedConnection cross-thread.
        self._dispatch_signal.connect(self._on_dispatched)

    def subscribe(
        self,
        event_name: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        """Registra un callback Qt-safe per un evento.

        Args:
            event_name: Nome evento sull'EventBus.
            callback: Funzione richiamata sul thread Qt principale.
        """
        self._callbacks.setdefault(event_name, []).append(callback)

        def _wrapper(data: dict[str, Any]) -> None:
            # Emesso dal worker thread; il ricevitore è nel main thread,
            # quindi Qt usa QueuedConnection automaticamente.
            self._dispatch_signal.emit(event_name, data)

        self._wrappers.append((event_name, _wrapper))
        self._bus.subscribe(event_name, _wrapper)
        logger.debug("EventBridge iscritto a '%s'", event_name)

    @Slot(str, object)
    def _on_dispatched(
        self, event_name: str, data: object
    ) -> None:
        """Esegue i callback registrati per l'evento (main thread).

        Args:
            event_name: Nome evento.
            data: Payload dell'evento.
        """
        callbacks: list[Callable[[dict[str, Any]], None]] = self._callbacks.get(
            event_name, []
        )
        payload: dict[str, Any] = data if isinstance(data, dict) else {}
        for cb in callbacks:
            try:
                cb(payload)
            except Exception as exc:
                logger.error(
                    "Errore in handler Qt-safe per evento '%s': %s",
                    event_name,
                    exc,
                    exc_info=True,
                )

    def unsubscribe_all(self) -> None:
        """Deregistra tutti gli handler registrati dal bridge."""
        for event_name, wrapper in self._wrappers:
            self._bus.unsubscribe(event_name, wrapper)
        self._wrappers.clear()
        self._callbacks.clear()


__all__ = ["EventBridge"]
