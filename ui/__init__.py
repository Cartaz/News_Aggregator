"""Presentation layer for News Aggregator.

The desktop shell is implemented with Qt WebEngine while the application
interface itself is native HTML/CSS/JavaScript. The business layer remains
framework-agnostic in :mod:`core`.
"""

from ui.window import WebMainWindow
from ui.tray import TrayIcon

__all__ = ["WebMainWindow", "TrayIcon"]
