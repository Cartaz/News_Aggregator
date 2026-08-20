"""Punto di ingresso dell'applicazione News Aggregator.

Questo modulo è un orchestratore puro: istanzia le dipendenze
(AppController, MainWindow, TrayIcon), applica il tema Neumorphism e
avvia il loop eventi Qt. NON contiene logica applicativa (§5.1.3).
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from config.constants import AppMeta, Paths
from config.theme import ThemeFonts
from core.app_controller import AppController
from ui.main_window import MainWindow
from ui.styles import build_global_qss
from ui.tray_icon import TrayIcon


def setup_logging() -> None:
    """Configura il logging su file rotante e console stderr."""
    Paths.ensure_user_dirs()
    formatter: logging.Formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler: RotatingFileHandler = RotatingFileHandler(
        Paths.LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler: logging.StreamHandler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    root: logging.Logger = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


def setup_fonts(app: QApplication) -> None:
    """Imposta ``Noto Sans`` come font predefinito dell'applicazione.

    Se il font non è installato, Qt userà il fallback di sistema.
    """
    font_family: str = ThemeFonts.SANS
    app.setFont(QFont(font_family, 11))


def main() -> int:
    """Avvia l'applicazione News Aggregator.

    Returns:
        Codice di uscita di Qt (0 = OK).
    """
    setup_logging()
    logger: logging.Logger = logging.getLogger(__name__)
    logger.info("Avvio %s v%s", AppMeta.NAME, AppMeta.VERSION)

    app: QApplication = QApplication(sys.argv)
    app.setApplicationName(AppMeta.NAME)
    app.setApplicationDisplayName(AppMeta.DISPLAY_NAME)
    app.setApplicationVersion(AppMeta.VERSION)
    app.setOrganizationName(AppMeta.AUTHOR)
    # CRITICO: con close_to_tray=True la finestra viene nascosta alla
    # chiusura (X), non distrutta. Senza questa impostazione Qt chiude
    # l'app non appena non ci sono più finestre visibili, anche se
    # la tray icon è ancora attiva. Disattiviamo il quit automatico:
    # l'app esce SOLO quando l'utente sceglie "Esci" dal menu tray
    # o preme Ctrl+Q.
    app.setQuitOnLastWindowClosed(False)

    setup_fonts(app)
    app.setStyleSheet(build_global_qss())

    controller: AppController = AppController()
    controller.start_auto_refresh()

    window: MainWindow = MainWindow(controller)
    window.show()

    tray: TrayIcon = TrayIcon()
    tray.setObjectName("TrayIcon")
    # Riferimento diretto per permettere a MainWindow di inoltrare
    # le notifiche "nuovi articoli" al tray (findChild non funziona
    # perché il tray non ha parent=MainWindow).
    window._tray = tray  # type: ignore[attr-defined]
    tray.show_window_requested.connect(window.showNormal)
    tray.show_window_requested.connect(window.activateWindow)
    tray.refresh_all_requested.connect(
        lambda: window._refresh_all_btn.click()
    )
    # "Esci" dal menu tray → shutdown pulito del controller + QApplication.quit().
    # NB: NON usiamo window.close() qui, perché con close_to_tray=True
    # la closeEvent nasconderebbe la finestra invece di uscire.
    # tray.quit_requested è già connesso a QApplication.quit in
    # TrayIcon._build_menu; qui aggiungiamo il cleanup del controller.
    def _on_tray_quit() -> None:
        controller.shutdown()
        QApplication.quit()

    tray.quit_requested.connect(_on_tray_quit)
    tray.show()

    # Badge iniziale: ricalcola articoli non letti appena parte l'app
    # (gli handler refresh_completed aggiorneranno il badge ad ogni refresh)
    window._refresh_tray_badge()

    exit_code: int = app.exec()
    logger.info("Uscita con codice %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
