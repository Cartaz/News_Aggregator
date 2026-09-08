"""Focused QML adapter for persisted application preferences."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Property, Qt, Signal, Slot

from config.constants import UIConstraints
from core.app_controller import AppController

logger = logging.getLogger(__name__)


class PreferencesAdapter(QObject):
    """Project canonical settings to QML and persist edits asynchronously."""

    changed = Signal()
    saveFinished = Signal(bool, str)
    sidebarPersistFailed = Signal(str)
    _commandRelay = Signal(str, bool, str)

    def __init__(self, controller: AppController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._commandRelay.connect(self._deliver, Qt.ConnectionType.QueuedConnection)

    @Property(int, notify=changed)
    def refreshIntervalMinutes(self) -> int:  # noqa: N802
        return self._controller.settings.refresh_interval_minutes

    @Property(bool, notify=changed)
    def markReadOnSelect(self) -> bool:  # noqa: N802
        return self._controller.settings.mark_read_on_select

    @Property(bool, notify=changed)
    def notifyNewItems(self) -> bool:  # noqa: N802
        return self._controller.settings.notify_new_items

    @Property(bool, notify=changed)
    def closeToTray(self) -> bool:  # noqa: N802
        return self._controller.settings.close_to_tray

    @Property(float, notify=changed)
    def fontScaleFactor(self) -> float:  # noqa: N802
        return float(self._controller.settings.font_scale_factor)

    @Property(int, notify=changed)
    def sidebarWidth(self) -> int:  # noqa: N802
        return int(self._controller.settings.source_split_width)

    def sync(self) -> None:
        """Notify QML that canonical settings may have changed."""
        self.changed.emit()

    @Slot(int, bool, bool, bool, float)
    def saveSettings(
        self,
        refresh_interval: int,
        mark_read_on_select: bool,
        notify_new_items: bool,
        close_to_tray: bool,
        font_scale_factor: float,
    ) -> None:  # noqa: N802
        changes = {
            "refresh_interval_minutes": int(refresh_interval),
            "mark_read_on_select": bool(mark_read_on_select),
            "notify_new_items": bool(notify_new_items),
            "close_to_tray": bool(close_to_tray),
            "font_scale_factor": float(font_scale_factor),
        }
        self._submit("save", changes)

    @Slot(int)
    def setSidebarWidth(self, width: int) -> None:  # noqa: N802
        width = max(
            UIConstraints.SOURCE_LIST_MIN_WIDTH,
            min(int(width), UIConstraints.SOURCE_LIST_MAX_WIDTH),
        )
        self._submit("sidebar", {"source_split_width": width})

    def _submit(self, action: str, changes: dict[str, Any]) -> None:
        def done(_operation_id: str, _result: object, error: Exception | None) -> None:
            self._commandRelay.emit(
                action,
                error is None,
                "" if error is None else (str(error) or "Impostazioni non salvate"),
            )

        try:
            operation_id = self._controller.update_settings_async(changes, done)
        except Exception as exc:
            logger.exception("Aggiornamento preferenze %s non avviato", action)
            self._deliver(action, False, str(exc) or "Impostazioni non salvate")
            return
        if operation_id is None:
            self._deliver(
                action,
                False,
                "Operazione non accettata: applicazione in chiusura",
            )

    @Slot(str, bool, str)
    def _deliver(self, action: str, success: bool, error_message: str) -> None:
        if not success:
            message = error_message or "Impostazioni non salvate"
            if action == "save":
                self.saveFinished.emit(False, message)
            else:
                self.sidebarPersistFailed.emit(message)
            self.changed.emit()
            return

        self.changed.emit()
        if action == "save":
            self.saveFinished.emit(True, "Impostazioni salvate")


__all__ = ["PreferencesAdapter"]
