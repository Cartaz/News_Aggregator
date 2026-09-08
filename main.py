"""Application composition root for News Aggregator."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Any

from core.native_memory import bootstrap_allocator, trim_process_memory


def setup_logging() -> None:
    from config.constants import Paths

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
    # This must run before importing Qt, networking or the application graph so
    # the replacement Linux/glibc process starts with the measured arena limit.
    bootstrap_allocator()

    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import QApplication

    from config.constants import AppMeta, Paths
    from core.app_controller import AppController
    from ui.controller import UiController
    from ui.native_actions import open_external_url
    from ui.tray import TrayIcon
    from ui.window import QmlMainWindow

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Avvio %s v%s", AppMeta.NAME, AppMeta.VERSION)

    app = QApplication(sys.argv)
    app.setApplicationName(AppMeta.NAME)
    app.setApplicationDisplayName(AppMeta.DISPLAY_NAME)
    app.setApplicationVersion(AppMeta.VERSION)
    app.setOrganizationName(AppMeta.AUTHOR)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Cantarell"))
    if Paths.APP_ICON.exists():
        app.setWindowIcon(QIcon(str(Paths.APP_ICON)))

    controller = AppController()
    ui_controller = UiController(controller, open_external=open_external_url)

    def reclaim_memory_after_refresh(
        event_name: str,
        payload: dict[str, Any],
    ) -> None:
        if event_name == "refresh_state_changed" and not bool(
            payload.get("active", False)
        ):
            # Controller events are emitted by the refresh worker, so this trim
            # does not block the Qt GUI thread during normal operation.
            trim_process_memory()

    controller.register_event_listener(reclaim_memory_after_refresh)

    window: QmlMainWindow | None = None
    exit_code: int | None = None
    try:
        controller.start_auto_refresh()
        window = QmlMainWindow(controller, ui_controller)
        tray = TrayIcon(window)

        tray.showWindowRequested.connect(window.restore_from_tray)
        tray.messageClicked.connect(window.restore_from_tray)
        tray.refreshAllRequested.connect(ui_controller.refreshAll)
        tray.quitRequested.connect(window.force_quit)
        ui_controller.unreadCountChanged.connect(tray.set_unread_count)

        def on_new_items(count: int, source_title: str) -> None:
            tray.set_unread_count(controller.get_total_unread_count())
            if controller.settings.notify_new_items:
                tray.notify_new_items(count, source_title)

        ui_controller.newItemsDetected.connect(on_new_items)
        tray.set_unread_count(controller.get_total_unread_count())
        tray.show()
        window.show()

        exit_code = app.exec()
        return exit_code
    finally:
        if window is not None:
            window.shutdown()
        else:
            ui_controller.shutdown()
        controller.unregister_event_listener(reclaim_memory_after_refresh)
        controller.shutdown()
        if exit_code is None:
            logger.info("Shutdown completato durante avvio o event loop interrotto")
        else:
            logger.info("Uscita con codice %d", exit_code)


if __name__ == "__main__":
    sys.exit(main())
