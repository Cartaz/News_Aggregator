"""Desktop shell hosting the native HTML/CSS/JavaScript interface."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QCloseEvent, QDesktopServices, QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from config.constants import AppMeta, Paths, UIConstraints
from core.app_controller import AppController
from ui.bridge import WebBridge

logger = logging.getLogger(__name__)


class _AppPage(QWebEnginePage):
    """Keep the application document local and send web links to the OS browser."""

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame: bool) -> bool:  # type: ignore[no-untyped-def]
        if url.scheme().lower() in {"http", "https"}:
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class WebMainWindow(QMainWindow):
    """Thin Qt window; all application presentation lives in ``ui/web``."""

    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self._controller = controller
        self._force_close = False
        self.setWindowTitle(AppMeta.DISPLAY_NAME)
        self.setMinimumSize(UIConstraints.WINDOW_MIN_WIDTH, UIConstraints.WINDOW_MIN_HEIGHT)
        self.resize(controller.settings.window_width, controller.settings.window_height)
        self.setStyleSheet("QMainWindow { background: rgb(20, 20, 20); }")
        if Paths.APP_ICON.exists():
            self.setWindowIcon(QIcon(str(Paths.APP_ICON)))

        self.bridge = WebBridge(controller, self)
        self.bridge.requestQuit.connect(self.force_quit)
        self.bridge.requestHide.connect(self.hide_to_tray)

        self._view = QWebEngineView(self)
        self._page = _AppPage(self._view)
        self._page.setBackgroundColor(QColor(20, 20, 20))
        self._view.setPage(self._page)
        self._channel = QWebChannel(self._page)
        self._channel.registerObject("backend", self.bridge)
        self._page.setWebChannel(self._channel)
        self.setCentralWidget(self._view)

        web_root = Path(__file__).resolve().parent / "web"
        self._view.load(QUrl.fromLocalFile(str(web_root / "index.html")))

    def _persist_geometry(self) -> None:
        try:
            settings = self._controller.settings_manager.settings
            settings.window_width = self.width()
            settings.window_height = self.height()
            self._controller.settings_manager.save()
        except Exception:
            logger.warning("Impossibile salvare la geometria finestra", exc_info=True)

    def hide_to_tray(self) -> None:
        self._persist_geometry()
        self.hide()

    def force_quit(self) -> None:
        self._force_close = True
        self._persist_geometry()
        self._controller.shutdown()
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._persist_geometry()
        if self._controller.settings.close_to_tray and not self._force_close:
            event.ignore()
            self.hide()
            return
        self._controller.shutdown()
        event.accept()
        QApplication.quit()


__all__ = ["WebMainWindow"]
