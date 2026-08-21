"""System tray integration for the web-based desktop UI."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QFontMetrics, QIcon, QPainter, QPixmap
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
        canvas = QPixmap(64, 64)
        canvas.fill(Qt.GlobalColor.transparent)

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Reserve the right side exclusively for the count so the digits never
        # overlap the application glyph after the desktop scales the tray icon.
        base_pixmap = self._base_icon.pixmap(40, 40)
        if not base_pixmap.isNull():
            painter.drawPixmap(0, 12, base_pixmap)

        text = "99+" if self._unread_count > 99 else str(self._unread_count)
        font = QFont("Sans Serif")
        font.setWeight(QFont.Weight.Black)
        font.setPixelSize(36)
        text_rect = QRect(31, 4, 33, 56)

        # Keep the largest possible digits inside the dedicated right-hand area.
        metrics = QFontMetrics(font)
        while metrics.horizontalAdvance(text) > text_rect.width() - 2 and font.pixelSize() > 17:
            font.setPixelSize(font.pixelSize() - 2)
            metrics = QFontMetrics(font)
        painter.setFont(font)

        # A dark outline belongs to the glyph itself, not to a badge/circle. It
        # keeps orange digits readable on both light and dark system panels.
        painter.setPen(QColor("#141414"))
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            painter.drawText(text_rect.translated(dx, dy), Qt.AlignmentFlag.AlignCenter, text)
        painter.setPen(QColor("#FF6600"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        self.setIcon(QIcon(canvas))

    def notify_new_items(self, count: int, source_title: str) -> None:
        if count <= 0:
            return
        label = "nuovo articolo" if count == 1 else "nuovi articoli"
        self.showMessage(AppMeta.DISPLAY_NAME, f"{count} {label} da {source_title}", self._base_icon, 4500)


__all__ = ["TrayIcon"]
