"""Application entry point for News Aggregator."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from config.constants import AppMeta, Paths
from core.app_controller import AppController
from ui.tray import TrayIcon
from ui.window import WebMainWindow


def setup_logging() -> None:
    """Configure rotating application logging.

    Production logs default to INFO. Set ``NEWS_AGGREGATOR_LOG_LEVEL=DEBUG``
    when detailed HTTP/EventBus diagnostics are needed.
    """
    Paths.ensure_user_dirs()
    level_name = os.environ.get("NEWS_AGGREGATOR_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        Paths.LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(console_handler)


def main() -> int:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Avvio %s v%s", AppMeta.NAME, AppMeta.VERSION)

    app = QApplication(sys.argv)
    app.setApplicationName(AppMeta.NAME)
    app.setApplicationDisplayName(AppMeta.DISPLAY_NAME)
    app.setApplicationVersion(AppMeta.VERSION)
    app.setOrganizationName(AppMeta.AUTHOR)
    app.setQuitOnLastWindowClosed(False)
    if Paths.APP_ICON.exists():
        app.setWindowIcon(QIcon(str(Paths.APP_ICON)))

    controller = AppController()
    controller.start_auto_refresh()
    window = WebMainWindow(controller)
    tray = TrayIcon(window)

    tray.showWindowRequested.connect(window.restore_from_tray)
    tray.messageClicked.connect(window.restore_from_tray)
    tray.refreshAllRequested.connect(window.bridge.refreshAll)
    tray.quitRequested.connect(window.force_quit)
    window.bridge.unreadCountChanged.connect(tray.set_unread_count)

    def on_new_items(count: int, source_title: str) -> None:
        tray.set_unread_count(controller.get_total_unread_count())
        if controller.settings.notify_new_items:
            tray.notify_new_items(count, source_title)

    window.bridge.newItemsDetected.connect(on_new_items)
    tray.set_unread_count(controller.get_total_unread_count())
    tray.show()
    window.show()

    exit_code = app.exec()
    controller.shutdown()
    logger.info("Uscita con codice %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
