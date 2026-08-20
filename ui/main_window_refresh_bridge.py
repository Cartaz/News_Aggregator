"""Helper per il marshalling cross-thread dei callback ``on_done``.

Estratto da ``main_window.py`` per rispettare il limite di 300 righe
per file (§5.1.3). Contiene gli slot Qt-safe che girano nel main thread.

I segnali cross-thread sono definiti direttamente in ``MainWindow``
(``refresh_single_done``, ``refresh_all_done``) e connessi ai metodi
di questa classe tramite ``window.refresh_X_done.connect(self._on_X_qt)``
in ``MainWindow._connect_refresh_signals``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class RefreshDoneDispatcher:
    """Dispatcher per i callback ``on_done`` cross-thread.

    Istanziato una volta per ``MainWindow`` e registrato come QObject
    figlio della finestra, così vive quanto lei. I segnali della
    finestra vengono connessi ai metodi ``_on_*_qt`` di questa classe,
    che a loro volta chiamano gli static method di ``MainWindowActions``
    nel main thread.
    """

    def __init__(self, window: "MainWindow") -> None:
        self._window: MainWindow = window

    def on_refresh_single_done_qt(
        self, source_id: str, success: bool, message: str
    ) -> None:
        """Slot Qt-safe eseguito nel main thread al refresh singolo."""
        from ui.main_window_actions import MainWindowActions

        MainWindowActions._single_done(
            self._window, source_id, success, message
        )

    def on_refresh_all_done_qt(self, result: dict[str, Any]) -> None:
        """Slot Qt-safe eseguito nel main thread al refresh tutti."""
        from ui.main_window_actions import MainWindowActions

        MainWindowActions._refresh_all_done(self._window, result)


__all__ = ["RefreshDoneDispatcher"]
