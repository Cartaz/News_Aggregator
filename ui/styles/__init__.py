"""Pacchetto stili: fogli QSS per il tema Neumorphism.

Il tema attivo è Neumorphism. ``breeze_dark`` è conservato come
modulo legacy per eventuale fallback, ma non è più usato
dall'applicazione.
"""

from __future__ import annotations

from ui.styles.neumorphism import build_global_qss

__all__ = ["build_global_qss"]
