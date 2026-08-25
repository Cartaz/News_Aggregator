"""Focused Qt-native actions kept outside the WebChannel bridge."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def open_external_url(raw_url: str) -> tuple[bool, str]:
    """Validate and open one HTTP(S) URL in the system browser."""
    url = QUrl.fromUserInput((raw_url or "").strip())
    if not url.isValid() or url.scheme().lower() not in {"http", "https"}:
        return False, "Link non valido"
    if not QDesktopServices.openUrl(url):
        return False, "Impossibile aprire il browser"
    return True, "Link aperto"


__all__ = ["open_external_url"]
