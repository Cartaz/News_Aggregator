"""Foglio di stile QSS legacy per il tema Breeze Dark.

DEPRECATO: questo modulo è conservato per riferimento storico ma non è
più utilizzato dall'applicazione. Il tema attivo è Neumorphism, vedi
``ui.styles.neumorphism``.

Tutti i selettori referenziavano esclusivamente i token di ``ThemeColors``,
``ThemeFonts`` e ``ThemeSpacing``. Nessun valore hardcoded (vincolo §5.1.5).
"""

from __future__ import annotations

from config.theme import ThemeColors, ThemeFonts, ThemeSpacing, ThemeTypography


def build_global_qss() -> str:
    """Genera il QSS legacy Breeze Dark (non più usato).

    Returns:
        Stringa QSS pronta per ``QApplication.setStyleSheet``.

    Note:
        Questo modulo è deprecato. Usare
        ``ui.styles.neumorphism.build_global_qss`` invece.
    """
    c = ThemeColors
    f = ThemeFonts
    s = ThemeSpacing
    t = ThemeTypography
    return f"""
QWidget {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_PRIMARY};
    font-family: "{f.SANS}", "{f.FALLBACK_SANS}";
    font-size: {t.BODY_SIZE}px;
}}

QMainWindow, QDialog {{
    background-color: {c.BG_MAIN};
}}

QStatusBar {{
    background-color: {c.BG_CARD};
    color: {c.TEXT_SECONDARY};
    border-top: 1px solid {c.BORDER};
}}

QToolTip {{
    background-color: {c.BG_TOOLTIP};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER};
    border-radius: 3px;
    padding: 4px 8px;
}}

QPushButton {{
    background-color: {c.PRIMARY_DARK};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER};
    border-radius: {s.BORDER_RADIUS}px;
    padding: 8px 16px;
    font-size: {t.BUTTON_SIZE}px;
    font-weight: {t.BUTTON_WEIGHT};
}}
QPushButton:hover {{
    background-color: {c.PRIMARY};
    border: 1px solid {c.PRIMARY};
}}
QPushButton:pressed {{
    background-color: {c.PRIMARY_DARK};
}}
""".strip()


__all__ = ["build_global_qss"]
