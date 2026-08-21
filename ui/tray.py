"""System tray integration for the web-based desktop UI."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from config.constants import AppMeta, Paths


class TrayIcon(QSystemTrayIcon):
    showWindowRequested = Signal()
    refreshAllRequested = Signal()
    quitRequested = Signal()

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        self._base_icon = QIcon(str(Paths.APP_ICON)) if Paths.APP_ICON.exists() else QIcon()
        super().__init__(self._base_icon, parent)
        self._unread_count = 0
        self.setToolTip(AppMeta.DISPLAY_NAME)
        menu = QMenu()
        show_action = QAction("Mostra", menu)
        refresh_action = QAction("Aggiorna tutti", menu)
        quit_action = QAction("Esci", menu)
        show_action.triggered.connect(self.showWindowRequested.emit)
        refresh_action.triggered.connect(self.refreshAllRequested.emit)
        quit_action.triggered.connect(self.quitRequested.emit)
        menu.addAction(show_action)
        menu.addAction(refresh_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.showWindowRequested.emit()

    def set_unread_count(self, count: int) -> None:
        self._unread_count = max(0, int(count))
        if self._unread_count <= 0:
            self.setIcon(self._base_icon)
            self.setToolTip(AppMeta.DISPLAY_NAME)
            return
        self.setToolTip(f"{AppMeta.DISPLAY_NAME} — {self._unread_count} non letti")
        pixmap = self._base_icon.pixmap(64, 64)
        if pixmap.isNull():
            pixmap = QPixmap(64, 64)
            pixmap.fill(QColor("#141414"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#141414"))
        painter.setBrush(QColor("#FF6600"))
        painter.drawEllipse(34, 34, 29, 29)
        painter.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        text = "99+" if self._unread_count > 99 else str(self._unread_count)
        painter.drawText(34, 34, 29, 29, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        self.setIcon(QIcon(pixmap))

    def notify_new_items(self, count: int, source_title: str) -> None:
        if count <= 0:
            return
        label = "nuovo articolo" if count == 1 else "nuovi articoli"
        self.showMessage(AppMeta.DISPLAY_NAME, f"{count} {label} da {source_title}", self._base_icon, 4500)


__all__ = ["TrayIcon"]
