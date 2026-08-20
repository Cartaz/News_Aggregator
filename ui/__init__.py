"""Pacchetto ui: interfaccia utente Qt/PySide6.

Esporta l'interfaccia pubblica del livello UI. Questo livello importa
da ``core/`` e ``config/``, MAI da ``main.py``. Per aggiornamenti GUI
thread-safe, usare ``EventBridge``.
"""

from __future__ import annotations

from ui.event_bridge import EventBridge
from ui.main_window import MainWindow
from ui.main_window_actions import MainWindowActions
from ui.main_window_close import handle_close_event, save_window_geometry
from ui.main_window_handlers import MainWindowHandlers
from ui.main_window_init import load_initial_state, subscribe_events
from ui.news_view_refresher import (
    refresh_all,
    refresh_by_category,
    refresh_by_source,
)
from ui.tray_icon import TrayIcon

__all__ = [
    "EventBridge",
    "MainWindow",
    "MainWindowActions",
    "MainWindowHandlers",
    "TrayIcon",
    "save_window_geometry",
    "handle_close_event",
    "subscribe_events",
    "load_initial_state",
    "refresh_all",
    "refresh_by_category",
    "refresh_by_source",
]
