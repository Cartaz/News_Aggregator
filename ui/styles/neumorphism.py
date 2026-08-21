"""Global QSS companion for the custom-painted Dark Neumorphism skin.

QSS owns typography, item delegates and platform controls that are not custom
painted. Raised/inset depth for primary controls and content panels is painted
in Python so the stylesheet never needs to fake multiple shadows with borders.
"""

from __future__ import annotations

from config.theme import ThemeColors, ThemeFonts, ThemeSpacing, ThemeTypography


def build_global_qss() -> str:
    c = ThemeColors
    f = ThemeFonts
    s = ThemeSpacing
    t = ThemeTypography

    return f"""
/* BASE MATERIAL */
QWidget {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_PRIMARY};
    font-family: \"{f.SANS}\", \"{f.FALLBACK_SANS}\";
    font-size: {t.BODY_SIZE}px;
}}
QMainWindow, QDialog {{ background-color: {c.BG_MAIN}; }}

/* CUSTOM-PAINTED BUTTONS: metrics are baseline-identical. */
QPushButton {{
    background: transparent;
    color: {c.TEXT_PRIMARY};
    border: none;
    border-radius: {s.BORDER_RADIUS}px;
    padding: 10px 20px;
    font-size: {t.BUTTON_SIZE}px;
    font-weight: {t.BUTTON_WEIGHT};
    margin: 2px;
}}
QPushButton:pressed, QPushButton:checked {{
    background: transparent;
    border: none;
    padding: 10px 20px;
}}
QPushButton:disabled {{ color: {c.TEXT_DISABLED}; }}
QPushButton[danger=\"true\"] {{ color: {c.DANGER}; }}

/* CUSTOM-PAINTED RECESSED INPUTS */
QLineEdit {{
    background: transparent;
    color: {c.TEXT_PRIMARY};
    border: none;
    border-radius: {s.BORDER_RADIUS}px;
    padding: 10px 14px;
    selection-background-color: {c.PRIMARY};
    selection-color: {c.TEXT_ON_PRIMARY};
}}
QLineEdit > QToolButton {{ background: transparent; border: none; padding: 2px; }}

/* DATA SURFACES: inset overlays create depth; QSS handles rows and states. */
QTreeWidget, QTableWidget {{
    background-color: {c.BG_INPUT};
    alternate-background-color: {c.SURFACE_MID};
    border: 1px solid {c.BORDER_DARK};
    border-radius: {s.BORDER_RADIUS}px;
    outline: 0;
    selection-background-color: {c.BG_SELECTION};
    selection-color: {c.TEXT_PRIMARY};
}}
QTreeWidget:focus, QTableWidget:focus {{
    border: 1px solid {c.PRIMARY};
}}
QTreeWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid {c.BORDER_SUBTLE};
    background: transparent;
}}
QTreeWidget::item:hover {{
    background-color: {c.BG_HOVER};
    color: {c.PRIMARY_SOFT};
}}
QTreeWidget::item:selected {{
    background-color: {c.BG_SELECTION};
    color: {c.TEXT_PRIMARY};
}}
QTableWidget::item {{ padding: 6px 8px; background: transparent; }}
QTableWidget::item:hover {{ background-color: {c.BG_HOVER}; }}
QTableWidget::item:selected {{
    background-color: {c.BG_SELECTION};
    color: {c.TEXT_PRIMARY};
}}

QHeaderView {{ background-color: {c.BG_MAIN}; }}
QHeaderView::section {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 {c.SURFACE_HIGH},
        stop:0.52 {c.SURFACE_MID},
        stop:1 {c.SURFACE_LOW}
    );
    color: {c.TEXT_SECONDARY};
    padding: 8px 10px;
    border: none;
    border-right: 1px solid {c.BORDER_SUBTLE};
    border-bottom: 1px solid {c.BORDER_DARK};
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
QHeaderView::section:hover {{ color: {c.TEXT_PRIMARY}; }}

QWidget[detailPanel=\"true\"] {{
    background-color: {c.BG_INPUT};
    border: 1px solid {c.BORDER_DARK};
    border-radius: {s.BORDER_RADIUS_LG}px;
}}
QTextBrowser {{
    background: transparent;
    border: none;
    padding: 4px 6px;
    selection-background-color: {c.PRIMARY};
    selection-color: {c.TEXT_ON_PRIMARY};
}}

/* TYPOGRAPHY */
QLabel {{ color: {c.TEXT_PRIMARY}; background: transparent; }}
QLabel[secondary=\"true\"] {{ color: {c.TEXT_SECONDARY}; font-size: 11px; }}
QLabel[header=\"true\"] {{
    color: {c.TEXT_PRIMARY};
    font-size: {t.CARD_HEADER_SIZE}px;
    font-weight: {t.CARD_HEADER_WEIGHT};
    font-variant: small-caps;
    letter-spacing: {t.CARD_HEADER_LETTER_SPACING}px;
}}
QLabel[title=\"true\"] {{
    color: {c.TEXT_PRIMARY};
    font-size: {t.TITLE_SIZE}px;
    font-weight: {t.TITLE_WEIGHT};
    letter-spacing: -0.01em;
}}
QLabel[link=\"true\"] {{ color: {c.LINK}; }}

/* SPLITTERS — same handle geometry as the baseline. */
QSplitter::handle {{ background-color: transparent; }}
QSplitter::handle:horizontal {{
    width: 4px;
    margin: 8px 1px;
    border-left: 1px solid {c.SHADOW_DARK};
    border-right: 1px solid {c.SHADOW_LIGHT_SOFT};
}}
QSplitter::handle:vertical {{
    height: 4px;
    margin: 1px 8px;
    border-top: 1px solid {c.SHADOW_DARK};
    border-bottom: 1px solid {c.SHADOW_LIGHT_SOFT};
}}
QSplitter::handle:hover {{
    background-color: {c.PRIMARY};
    border: 1px solid {c.PRIMARY};
    border-radius: 2px;
}}

/* MENUS AND TOOLTIPS */
QMenuBar {{
    background-color: {c.BG_CARD};
    color: {c.TEXT_PRIMARY};
    border-bottom: 1px solid {c.BORDER_SUBTLE};
    padding: 2px 4px;
}}
QMenuBar::item {{ background: transparent; padding: 6px 12px; border-radius: {s.BORDER_RADIUS_SM}px; }}
QMenuBar::item:selected {{ background-color: {c.BG_HOVER}; color: {c.PRIMARY_SOFT}; }}
QMenu {{
    background-color: {c.BG_ELEVATED};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER};
    border-radius: {s.BORDER_RADIUS}px;
    padding: 6px;
}}
QMenu::item {{ padding: 8px 24px; border-radius: {s.BORDER_RADIUS_SM}px; margin: 1px 2px; }}
QMenu::item:selected {{ background-color: {c.BG_SELECTION}; color: {c.PRIMARY_SOFT}; }}
QMenu::item:disabled {{ color: {c.TEXT_DISABLED}; }}
QMenu::separator {{ height: 1px; background-color: {c.BORDER_SUBTLE}; margin: 4px 8px; }}
QToolTip {{
    background-color: {c.BG_TOOLTIP};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER};
    border-radius: {s.BORDER_RADIUS_SM}px;
    padding: 6px 10px;
}}

/* STATUS BAR */
QStatusBar {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_SECONDARY};
    border-top: 1px solid {c.BORDER_SUBTLE};
    padding: 4px 8px;
}}
QStatusBar::item {{ border: none; }}

/* FALLBACK EDITABLE CONTROLS USED BY DIALOGS */
QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {c.BG_INPUT};
    color: {c.TEXT_PRIMARY};
    border-top: 1px solid {c.SHADOW_DARK_SOFT};
    border-left: 1px solid {c.SHADOW_DARK_SOFT};
    border-right: 1px solid {c.BORDER};
    border-bottom: 1px solid {c.BORDER};
    border-radius: {s.BORDER_RADIUS}px;
    padding: 10px 14px;
    selection-background-color: {c.PRIMARY};
    selection-color: {c.TEXT_ON_PRIMARY};
}}
QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {c.PRIMARY};
}}

/* CHECKBOX / RADIO / PROGRESS */
QCheckBox, QRadioButton {{ color: {c.TEXT_PRIMARY}; spacing: 10px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    background-color: {c.BG_INPUT};
    border-top: 1px solid {c.SHADOW_DARK};
    border-left: 1px solid {c.SHADOW_DARK};
    border-right: 1px solid {c.SHADOW_LIGHT_SOFT};
    border-bottom: 1px solid {c.SHADOW_LIGHT_SOFT};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {c.PRIMARY};
    border: 1px solid {c.PRIMARY_DARK};
}}
QCheckBox:focus, QRadioButton:focus {{ color: {c.PRIMARY_SOFT}; }}
QProgressBar {{
    background-color: {c.BG_INPUT};
    border: 1px solid {c.BORDER_DARK};
    border-radius: {s.BORDER_RADIUS_SM}px;
    text-align: center;
    color: {c.TEXT_PRIMARY};
    height: 20px;
}}
QProgressBar::chunk {{
    background-color: {c.PRIMARY};
    border-radius: {s.BORDER_RADIUS_SM}px;
    margin: 1px;
}}

/* SCROLLBARS */
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 {c.SHADOW_LIGHT_SOFT},
        stop:1 {c.SURFACE_LOW}
    );
    border: 1px solid {c.BORDER};
    min-height: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{ background: {c.BG_HOVER}; border-color: {c.PRIMARY_DARK}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: none; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px 4px; }}
QScrollBar::handle:horizontal {{
    background: {c.SURFACE_MID};
    border: 1px solid {c.BORDER};
    min-width: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{ border-color: {c.PRIMARY_DARK}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; background: none; border: none; }}

/* Existing V/H separators; appearance only. */
QFrame[frameShape=\"4\"], QFrame[frameShape=\"5\"] {{
    background-color: {c.BORDER_SUBTLE};
    border: none;
}}
""".strip()


__all__ = ["build_global_qss"]
