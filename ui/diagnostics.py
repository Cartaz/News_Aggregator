"""Focused QML adapter for bounded application diagnostics."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Property, Qt, Signal, Slot

from core.app_controller import AppController

logger = logging.getLogger(__name__)


class DiagnosticsAdapter(QObject):
    """Expose a bounded log snapshot without leaking file access to QML."""

    changed = Signal()
    loadFailed = Signal(str)
    _loaded = Signal(int, object, object)

    def __init__(self, controller: AppController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._path = ""
        self._text = ""
        self._generation = 0
        self._loaded.connect(self._deliver, Qt.ConnectionType.QueuedConnection)

    @Property(str, notify=changed)
    def path(self) -> str:
        return self._path

    @Property(str, notify=changed)
    def text(self) -> str:
        return self._text

    @Slot(result=bool)
    def load(self) -> bool:
        """Accept an asynchronous load; True means queued, not yet completed."""
        self._generation += 1
        generation = self._generation

        def done(_operation_id: str, result: object, error: Exception | None) -> None:
            self._loaded.emit(generation, result, error)

        try:
            accepted = self._controller.get_log_tail_async(300, done)
            if accepted is None:
                self.loadFailed.emit("Applicazione in chiusura")
                return False
            return True
        except Exception as exc:
            logger.exception("Lettura log fallita")
            self.loadFailed.emit(str(exc) or "Log non disponibile")
            return False

    @Slot(int, object, object)
    def _deliver(self, generation: int, payload: object, error: object) -> None:
        if generation != self._generation:
            return
        if error is not None:
            self.loadFailed.emit(str(error) or "Log non disponibile")
            return
        data = payload if isinstance(payload, dict) else {}
        self._path = str(data.get("path", ""))
        lines = data.get("lines", [])
        self._text = "\n".join(str(line) for line in lines) if isinstance(lines, list) else ""
        self.changed.emit()

    @Slot()
    def clear(self) -> None:
        """Release the transient log snapshot after the diagnostics dialog closes."""
        self._generation += 1
        if not self._path and not self._text:
            return
        self._path = ""
        self._text = ""
        self.changed.emit()


__all__ = ["DiagnosticsAdapter"]
