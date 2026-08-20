"""Helper per la chiusura e persistenza geometria di ``MainWindow``.

Estratto da ``main_window.py`` per rispettare il limite di 300 righe
per file (§5.1.3).

Comportamento chiusura:
- Se ``settings.close_to_tray`` è True (default), la X nasconde la
  finestra e mantiene attiva la tray icon. Per uscire davvero,
  usare Ctrl+Q o "Esci" dal menu tray.
- Se ``close_to_tray`` è False, la X esce come prima (shutdown +
  QApplication.quit).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtGui import QCloseEvent

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def save_window_geometry(window: "MainWindow") -> None:
    """Persiste larghezza e altezza finestra nelle impostazioni.

    Args:
        window: Finestra principale.
    """
    size = window.size()  # type: ignore[attr-defined]
    try:
        window._controller.settings_manager.set(  # type: ignore[attr-defined]
            "window_width", size.width()
        )
        window._controller.settings_manager.set(  # type: ignore[attr-defined]
            "window_height", size.height()
        )
    except Exception as exc:
        logger.warning("Impossibile salvare geometria: %s", exc)


def handle_close_event(
    window: "MainWindow", event: QCloseEvent
) -> None:
    """Gestisce il closeEvent: salva geometria e decide se uscire o nascondere.

    Logica a 3 rami:

    1. ``window._force_quit_requested`` True (da Ctrl+Q o "Esci" tray):
       esci davvero — shutdown controller + QApplication.quit().

    2. ``settings.close_to_tray`` True e nessun force_quit (la X):
       nasconde la finestra, l'app resta viva nel tray. Per uscire
       davvero usare Ctrl+Q o "Esci" dal menu tray.

    3. ``settings.close_to_tray`` False (vecchio comportamento):
       shutdown + quit_requested → QApplication.quit().

    Args:
        window: Finestra principale.
        event: Evento di chiusura Qt.
    """
    save_window_geometry(window)

    # Reset del flag in ogni caso (sempre meglio, così il prossimo close
    # parte pulito a meno che non venga esplicitamente richiesto)
    force_quit: bool = bool(
        getattr(window, "_force_quit_requested", False)
    )
    window._force_quit_requested = False  # type: ignore[attr-defined]

    # Ramo 1: uscita esplicita richiesta
    if force_quit:
        window._controller.shutdown()  # type: ignore[attr-defined]
        window.quit_requested.emit()  # type: ignore[attr-defined]
        event.accept()
        return

    # Verifica close_to_tray dalle impostazioni
    close_to_tray: bool = False
    try:
        close_to_tray = bool(
            window._controller.settings.close_to_tray  # type: ignore[attr-defined]
        )
    except AttributeError:
        # Settings o controller mancanti in qualche mock di test:
        # comportamento conservativo = esci
        close_to_tray = False

    # Ramo 2: chiudi con la X ma resta nel tray
    if close_to_tray:
        logger.info("close_to_tray attivo: nascondo finestra, resto nel tray")
        window.hide()  # type: ignore[attr-defined]
        event.ignore()  # CRITICO: dice a Qt di NON propagare la chiusura
        return

    # Ramo 3: comportamento classico, esci dall'app
    window._controller.shutdown()  # type: ignore[attr-defined]
    window.quit_requested.emit()  # type: ignore[attr-defined]
    event.accept()


__all__ = ["save_window_geometry", "handle_close_event"]
