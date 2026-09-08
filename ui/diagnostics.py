"""Focused QML adapter for bounded application diagnostics."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Property, Signal, Slot

from core.app_controller import AppController

logger = logging.getLogger(__name__)


class DiagnosticsAdapter(QObject):
    """Expose a bounded log snapshot without leaking file access to QML."""

    changed = Signal()
    loadFailed = Signal(str)

    def __init__(self, controller: AppController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._path = ""
        self._text = ""

    @Property(str, notify=changed)
    def path(self) -> str:
        return self._path

    @Property(str, notify=changed)
    def text(self) -> str:
        return self._text

    @Slot(result=bool)
    def load(self) -> bool:
        try:
            payload = self._controller.get_log_tail(300)
            self._path = str(payload.get("path", ""))
            lines = payload.get("lines", [])
            self._text = (
                "\n".join(str(line) for line in lines)
                if isinstance(lines, list)
                else ""
            )
            self.changed.emit()
            return True
        except Exception as exc:
            logger.exception("Lettura log fallita")
            self.loadFailed.emit(str(exc) or "Log non disponibile")
            return False

    @Slot()
    def clear(self) -> None:
        """Release the transient log snapshot after the diagnostics dialog closes."""
        if not self._path and not self._text:
            return
        self._path = ""
        self._text = ""
        self.changed.emit()


__all__ = ["DiagnosticsAdapter"]
