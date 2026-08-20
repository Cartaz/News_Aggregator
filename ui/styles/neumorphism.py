"""Global QSS companion for the real multi-shadow Dark Neumorphism skin.

QSS is deliberately *not* responsible for the defining depth effect.
Buttons/fields/panels receive genuine blurred inset/outset QGraphicsEffects.

This stylesheet provides typography, item states, menu chrome, scrollbar
styling and transparent native layers needed by the custom-painted controls.
"""

from __future__ import annotations

from config.theme import ThemeColors, ThemeFonts, ThemeSpacing, ThemeTypography


def build_global_qss() -> str:
    c = ThemeColors
    f = ThemeFonts
    s = ThemeSpacing
    t = ThemeTypography

    return f"""
/* ============================================================
 * BASE
 * ============================================================ */
QWidget {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_PRIMARY};
    font-family: "{f.SANS}", "{f.FALLBACK_SANS}";
    font-size: {t.BODY_SIZE}px;
}}

QMainWindow,
QDialog {{
    background-color: {c.BG_MAIN};
}}

/* ============================================================
 * CUSTOM-PAINTED CONTROLS
 * Keep baseline padding/metrics. Background is painted in Python.
 * ============================================================ */
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

QPushButton:pressed,
QPushButton:checked {{
    background: transparent;
    border: none;
    padding: 10px 20px;
}}

QPushButton:disabled {{
    color: {c.TEXT_DISABLED};
}}

QPushButton[danger="true"] {{
    color: {c.DANGER};
}}

QLineEdit {{
    background: transparent;
    color: {c.TEXT_PRIMARY};
    border: none;
    border-radius: {s.BORDER_RADIUS}px;
    padding: 10px 14px;
    selection-background-color: {c.PRIMARY};
    selection-color: {c.TEXT_ON_PRIMARY};
}}

QLineEdit > QToolButton {{
    background: transparent;
    border: none;
    padding: 2px;
}}

/* ============================================================
 * DATA PANELS
 * Their inner depth comes from MultiBoxShadowEffect.
 * ============================================================ */
QTreeWidget,
QTableWidget {{
    background-color: {c.BG_INPUT};
    alternate-background-color: #191919;
    border: none;
    border-radius: {s.BORDER_RADIUS}px;
    outline: 0;
    selection-background-color: {c.BG_SELECTION};
    selection-color: {c.TEXT_PRIMARY};
}}

QTreeWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid #1E1E1E;
    background: transparent;
}}

QTreeWidget::item:hover {{
    background-color: #1C1C1C;
    color: {c.PRIMARY_SOFT};
}}

QTreeWidget::item:selected {{
    background-color: {c.BG_SELECTION};
    color: {c.TEXT_PRIMARY};
}}

QTableWidget::item {{
    padding: 6px 8px;
    background: transparent;
}}

QTableWidget::item:hover {{
    background-color: #1C1C1C;
}}

QTableWidget::item:selected {{
    background-color: {c.BG_SELECTION};
    color: {c.TEXT_PRIMARY};
}}

QHeaderView {{
    background-color: {c.BG_MAIN};
}}

QHeaderView::section {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #1F1F1F,
        stop:0.50 #1A1A1A,
        stop:1 #161616
    );
    color: {c.TEXT_SECONDARY};
    padding: 8px 10px;
    border: none;
    border-right: 1px solid #202020;
    border-bottom: 1px solid #202020;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}

QWidget[detailPanel="true"] {{
    background-color: {c.BG_INPUT};
    border: none;
    border-radius: {s.BORDER_RADIUS_LG}px;
}}

QTextBrowser {{
    background: transparent;
    border: none;
    padding: 4px 6px;
    selection-background-color: {c.PRIMARY};
    selection-color: {c.TEXT_ON_PRIMARY};
}}

/* ============================================================
 * LABELS
 * ============================================================ */
QLabel {{
    color: {c.TEXT_PRIMARY};
    background: transparent;
}}

QLabel[secondary="true"] {{
    color: {c.TEXT_SECONDARY};
    font-size: 11px;
}}

QLabel[header="true"] {{
    color: {c.TEXT_PRIMARY};
    font-size: {t.CARD_HEADER_SIZE}px;
    font-weight: {t.CARD_HEADER_WEIGHT};
    font-variant: small-caps;
    letter-spacing: {t.CARD_HEADER_LETTER_SPACING}px;
}}

QLabel[title="true"] {{
    color: {c.TEXT_PRIMARY};
    font-size: {t.TITLE_SIZE}px;
    font-weight: {t.TITLE_WEIGHT};
    letter-spacing: -0.01em;
}}

QLabel[link="true"] {{
    color: {c.LINK};
}}

/* ============================================================
 * SPLITTERS
 * Existing handle geometry is unchanged.
 * ============================================================ */
QSplitter::handle {{
    background-color: transparent;
}}

QSplitter::handle:horizontal {{
    width: 4px;
    margin: 8px 1px;
    border-left: 1px solid #080808;
    border-right: 1px solid #2B2B2B;
}}

QSplitter::handle:vertical {{
    height: 4px;
    margin: 1px 8px;
    border-top: 1px solid #080808;
    border-bottom: 1px solid #2B2B2B;
}}

QSplitter::handle:hover {{
    background-color: {c.PRIMARY};
    border: 1px solid {c.PRIMARY};
    border-radius: 2px;
}}

/* ============================================================
 * MENUS / TOOLTIP
 * ============================================================ */
QMenuBar {{
    background-color: {c.BG_CARD};
    color: {c.TEXT_PRIMARY};
    border-bottom: 1px solid {c.BORDER_SUBTLE};
    padding: 2px 4px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 6px 12px;
    border-radius: {s.BORDER_RADIUS_SM}px;
}}

QMenuBar::item:selected {{
    background-color: {c.BG_HOVER};
    color: {c.PRIMARY_SOFT};
}}

QMenu {{
    background-color: {c.BG_ELEVATED};
    color: {c.TEXT_PRIMARY};
    border: 1px solid #282828;
    border-radius: {s.BORDER_RADIUS}px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: {s.BORDER_RADIUS_SM}px;
    margin: 1px 2px;
}}

QMenu::item:selected {{
    background-color: {c.BG_SELECTION};
    color: {c.PRIMARY_SOFT};
}}

QMenu::item:disabled {{
    color: {c.TEXT_DISABLED};
}}

QMenu::separator {{
    height: 1px;
    background-color: #262626;
    margin: 4px 8px;
}}

QToolTip {{
    background-color: {c.BG_TOOLTIP};
    color: {c.TEXT_PRIMARY};
    border: 1px solid #2A2A2A;
    border-radius: {s.BORDER_RADIUS_SM}px;
    padding: 6px 10px;
}}

/* ============================================================
 * STATUS BAR
 * ============================================================ */
QStatusBar {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_SECONDARY};
    border-top: 1px solid #252525;
    padding: 4px 8px;
}}

QStatusBar::item {{
    border: none;
}}

/* ============================================================
 * FALLBACK EDITABLE CONTROLS USED IN DIALOGS
 * ============================================================ */
QTextEdit,
QPlainTextEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {{
    background-color: {c.BG_INPUT};
    color: {c.TEXT_PRIMARY};
    border: 1px solid #242424;
    border-radius: {s.BORDER_RADIUS}px;
    padding: 10px 14px;
    selection-background-color: {c.PRIMARY};
    selection-color: {c.TEXT_ON_PRIMARY};
}}

QTextEdit:focus,
QPlainTextEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus {{
    border: 1px solid {c.PRIMARY};
}}

/* ============================================================
 * CHECK / RADIO / PROGRESS
 * ============================================================ */
QCheckBox,
QRadioButton {{
    color: {c.TEXT_PRIMARY};
    spacing: 10px;
    background: transparent;
}}

QCheckBox::indicator,
QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    background-color: {c.BG_INPUT};
    border-top: 1px solid #080808;
    border-left: 1px solid #080808;
    border-right: 1px solid #2B2B2B;
    border-bottom: 1px solid #2B2B2B;
}}

QCheckBox::indicator {{
    border-radius: 4px;
}}

QRadioButton::indicator {{
    border-radius: 9px;
}}

QCheckBox::indicator:checked,
QRadioButton::indicator:checked {{
    background-color: {c.PRIMARY};
    border: 1px solid {c.PRIMARY_DARK};
}}

QProgressBar {{
    background-color: {c.BG_INPUT};
    border: 1px solid #242424;
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

/* ============================================================
 * SCROLLBARS
 * ============================================================ */
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 4px 2px;
}}

QScrollBar::handle:vertical {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #303030,
        stop:1 #1C1C1C
    );
    border: 1px solid #242424;
    min-height: 30px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #363636;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
    border: none;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 2px 4px;
}}

QScrollBar::handle:horizontal {{
    background: #292929;
    border: 1px solid #242424;
    min-width: 30px;
    border-radius: 4px;
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
    border: none;
}}

QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    background-color: #262626;
    border: none;
}}
""".strip()


__all__ = ["build_global_qss"]
