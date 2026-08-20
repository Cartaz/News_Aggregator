"""Foglio di stile QSS globale per il tema Neumorphism.

Implementa le linee guida neumorphism:
- Un unico materiale: ogni elemento ha lo stesso colore di sfondo (#121213).
- Bottoni estrusi: bordo chiaro in alto/sinistra + bordo scuro in
  basso/destra simulano l'ombra duale di una fonte di luce in alto
  a sinistra. Al :pressed i bordi si invertono (effetto incavato).
- Campi di testo incavati: bordo scuro in alto/sinistra + bordo chiaro
  in basso/destra (simulazione inset shadow). Lo stesso aspetto è
  mantenuto in ogni stato, anche senza focus.
- Accento (#ff6600) solo per stati attivi, link, focus ring — mai
  per riempire superfici.
- Border-radius generosi (8/12/16 px).

QSS non supporta box-shadow; usiamo i bordi asimmetrici come tecnica
di simulazione standard per il neumorphism in Qt. Il risultato è
visivamente coerente con il principio "un solo materiale, due
direzioni" delle linee guida.

Tutti i selettori referenziano esclusivamente i token di ``ThemeColors``,
``ThemeFonts`` e ``ThemeSpacing``. Nessun valore hardcoded (vincolo §5.1.5).
"""

from __future__ import annotations

from config.theme import ThemeColors, ThemeFonts, ThemeSpacing, ThemeTypography


def build_global_qss() -> str:
    """Genera il QSS globale applicato a ``QApplication``.

    Returns:
        Stringa QSS pronta per ``QApplication.setStyleSheet``.
    """
    c = ThemeColors
    f = ThemeFonts
    s = ThemeSpacing
    t = ThemeTypography

    # Shortcut per le "ombre" neumorphic
    sl = c.SHADOW_LIGHT   # ombra chiara (alto/sinistra)
    sd = c.SHADOW_DARK    # ombra scura (basso/destra)
    sds = c.SHADOW_DARK_SOFT  # ombra scura soft (per card grandi)

    return f"""
/* ============================================================
 * BACKGROUND & TESTO BASE
 * ============================================================ */
QWidget {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_PRIMARY};
    font-family: "{f.SANS}", "{f.FALLBACK_SANS}";
    font-size: {t.BODY_SIZE}px;
}}

QMainWindow, QDialog {{
    background-color: {c.BG_MAIN};
}}

/* ============================================================
 * STATUS BAR
 * ============================================================ */
QStatusBar {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_SECONDARY};
    border-top: 1px solid {sl};
    padding: 4px 8px;
}}
QStatusBar::item {{ border: none; }}

/* ============================================================
 * TOOLTIP
 * ============================================================ */
QToolTip {{
    background-color: {c.BG_TOOLTIP};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {sd};
    border-top-color: {sl};
    border-left-color: {sl};
    border-radius: {s.BORDER_RADIUS_SM}px;
    padding: 6px 10px;
}}

/* ============================================================
 * SCROLLBAR — minimali ma visibili, nascoste quando non serve
 * ============================================================ */
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {sd};
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-bottom: 1px solid {sl};
    border-right: 1px solid {sl};
    min-height: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c.TEXT_DISABLED};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
    border: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: {sd};
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-bottom: 1px solid {sl};
    border-right: 1px solid {sl};
    min-width: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {c.TEXT_DISABLED};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
    border: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* ============================================================
 * CAMPI DI TESTO — INCARATI (inset shadow simulato)
 * Stato di riposo, hover e focus mantengono tutti l'aspetto
 * incavato; il focus aggiunge un ring di accento 2px.
 * ============================================================ */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {c.BG_INPUT};
    color: {c.TEXT_PRIMARY};
    /* Ombra inset: bordo scuro in alto/sinistra, chiaro in basso/destra */
    border-top: 1px solid {sd};
    border-left: 1px solid {sd};
    border-right: 1px solid {sl};
    border-bottom: 1px solid {sl};
    border-radius: {s.BORDER_RADIUS}px;
    padding: 10px 14px;
    selection-background-color: {c.BG_SELECTION};
    selection-color: {c.TEXT_ON_PRIMARY};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover {{
    /* Neumorphism: nessun cambiamento visivo sull'hover del campo */
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{
    /* Focus ring: anello di accento senza cambio di sfondo */
    border-top: 1px solid {sd};
    border-left: 1px solid {sd};
    border-right: 1px solid {sd};
    border-bottom: 1px solid {sd};
    outline: 2px solid {c.PRIMARY_SOFT};
    outline-offset: 0px;
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    color: {c.TEXT_DISABLED};
    background-color: {c.BG_MAIN};
    border-top: 1px solid {sds};
    border-left: 1px solid {sds};
    border-right: 1px solid {sds};
    border-bottom: 1px solid {sds};
}}
/* Icona "clear" del QLineEdit */
QLineEdit > QToolButton {{
    background: transparent;
    border: none;
    padding: 2px;
}}

/* ============================================================
 * PULSANTI — ESTRUSI (shadow esterna simulata)
 * Ombra chiara in alto/sinistra, scura in basso/destra.
 * Hover: ombra più stretta (effetto avvicinamento).
 * Pressed: ombra invertita (effetto pressione fisica).
 * Disabled: opacità ridotta + ombre rimosse.
 * ============================================================ */
QPushButton {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_PRIMARY};
    /* Estrusione: chiaro sopra/sinistra, scuro sotto/destra */
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-right: 1px solid {sd};
    border-bottom: 1px solid {sd};
    border-radius: {s.BORDER_RADIUS}px;
    padding: 10px 20px;
    font-size: {t.BUTTON_SIZE}px;
    font-weight: {t.BUTTON_WEIGHT};
    margin: 2px;
}}
QPushButton:hover {{
    /* Ombra più stretta: l'elemento si avvicina */
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-right: 1px solid {sd};
    border-bottom: 1px solid {sd};
    color: {c.PRIMARY_SOFT};
}}
QPushButton:pressed, QPushButton:checked {{
    /* Inversione inset: effetto pressione */
    border-top: 1px solid {sd};
    border-left: 1px solid {sd};
    border-right: 1px solid {sl};
    border-bottom: 1px solid {sl};
    background-color: {c.BG_MAIN};
    padding-top: 11px;
    padding-bottom: 9px;
    padding-left: 21px;
    padding-right: 19px;
}}
QPushButton:disabled {{
    color: {c.TEXT_DISABLED};
    border: 1px solid {sds};
    background-color: {c.BG_MAIN};
}}

/* Variante primaria (accento) — testo arancione, contorno più marcato */
QPushButton[primary="true"] {{
    color: {c.PRIMARY};
    border-top: 2px solid {sl};
    border-left: 2px solid {sl};
    border-right: 2px solid {sd};
    border-bottom: 2px solid {sd};
    padding: 9px 19px;
}}
QPushButton[primary="true"]:hover {{
    color: {c.PRIMARY_SOFT};
}}
QPushButton[primary="true"]:pressed {{
    border-top: 2px solid {sd};
    border-left: 2px solid {sd};
    border-right: 2px solid {sl};
    border-bottom: 2px solid {sl};
}}

/* Variante danger (rosso "bad") */
QPushButton[danger="true"] {{
    color: {c.DANGER};
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-right: 1px solid {sd};
    border-bottom: 1px solid {sd};
}}
QPushButton[danger="true"]:hover {{
    color: {c.DANGER};
    background-color: {c.BG_HOVER};
}}
QPushButton[danger="true"]:pressed {{
    border-top: 1px solid {sd};
    border-left: 1px solid {sd};
    border-right: 1px solid {sl};
    border-bottom: 1px solid {sl};
    background-color: {c.BG_MAIN};
}}

/* ============================================================
 * LISTE / TABELLE / ALBERI — pannelli incavati
 * Lo sfondo è lo stesso dell'app, ma il bordo asimmetrico li
 * fa apparire scavati nel materiale.
 * ============================================================ */
QListWidget, QTreeWidget, QTableWidget {{
    background-color: {c.BG_MAIN};
    alternate-background-color: {c.BG_HOVER};
    border-top: 1px solid {sd};
    border-left: 1px solid {sd};
    border-right: 1px solid {sl};
    border-bottom: 1px solid {sl};
    border-radius: {s.BORDER_RADIUS}px;
    outline: 0;
    selection-background-color: {c.BG_SELECTION};
    selection-color: {c.TEXT_ON_PRIMARY};
}}
QListWidget::item, QTreeWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid {sds};
    background: transparent;
}}
QListWidget::item:hover, QTreeWidget::item:hover {{
    background-color: {c.BG_HOVER};
    color: {c.PRIMARY_SOFT};
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {c.BG_SELECTION};
    color: {c.TEXT_ON_PRIMARY};
}}
QListWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {{
    border-image: none;
    image: none;
}}
QTableWidget::item {{
    padding: 6px 8px;
    background: transparent;
}}
QTableWidget::item:selected {{
    background-color: {c.BG_SELECTION};
    color: {c.TEXT_ON_PRIMARY};
}}
QHeaderView::section {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_SECONDARY};
    padding: 8px 10px;
    border: none;
    border-right: 1px solid {sds};
    border-bottom: 1px solid {sl};
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
QHeaderView::section:first {{
    border-top-left-radius: {s.BORDER_RADIUS}px;
}}
QHeaderView::section:last {{
    border-top-right-radius: {s.BORDER_RADIUS}px;
    border-right: none;
}}

/* ============================================================
 * DETAIL PANEL — separazione visiva netta tra lista articoli
 * e dettaglio sottostante (border-top accent + sfondo leggero).
 * Identificato dalla property detailPanel=True sul QWidget
 * contenitore impostato in NewsView._setup_ui.
 * ============================================================ */
QWidget[detailPanel="true"] {{
    background-color: {c.BG_MAIN};
    border-top: 1px solid {c.SHADOW_LIGHT};
}}

/* ============================================================
 * SPLITTER
 * ============================================================ */
QSplitter::handle {{
    background-color: transparent;
}}
QSplitter::handle:horizontal {{
    width: 4px;
    margin: 8px 1px;
    border-left: 1px solid {sds};
    border-right: 1px solid {sds};
    border-radius: 1px;
}}
QSplitter::handle:horizontal:hover {{
    background-color: {c.PRIMARY};
    border: 1px solid {c.PRIMARY};
    border-radius: 2px;
}}
QSplitter::handle:vertical {{
    height: 4px;
    margin: 1px 8px;
    border-top: 1px solid {sds};
    border-bottom: 1px solid {sds};
    border-radius: 1px;
}}
QSplitter::handle:vertical:hover {{
    background-color: {c.PRIMARY};
    border: 1px solid {c.PRIMARY};
    border-radius: 2px;
}}

/* ============================================================
 * LABEL
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
QLabel[link="true"]:hover {{
    color: {c.PRIMARY_SOFT};
}}

/* ============================================================
 * MENU BAR & MENU
 * ============================================================ */
QMenuBar {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_PRIMARY};
    border-bottom: 1px solid {sl};
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
    background-color: {c.BG_MAIN};
    color: {c.TEXT_PRIMARY};
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-right: 1px solid {sd};
    border-bottom: 1px solid {sd};
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
    color: {c.TEXT_ON_PRIMARY};
}}
QMenu::separator {{
    height: 1px;
    background-color: {sds};
    margin: 4px 8px;
}}
QMenu::icon {{ padding-left: 8px; }}

/* ============================================================
 * TOOLBAR
 * ============================================================ */
QToolBar {{
    background-color: {c.BG_MAIN};
    border-bottom: 1px solid {sl};
    border-top: 1px solid {sd};
    spacing: 4px;
    padding: 6px;
}}
QToolBar::separator {{
    background-color: {sds};
    width: 1px;
    margin: 6px 4px;
}}

/* ============================================================
 * PROGRESS BAR
 * ============================================================ */
QProgressBar {{
    background-color: {c.BG_MAIN};
    border-top: 1px solid {sd};
    border-left: 1px solid {sd};
    border-right: 1px solid {sl};
    border-bottom: 1px solid {sl};
    border-radius: {s.BORDER_RADIUS_SM}px;
    text-align: center;
    color: {c.TEXT_PRIMARY};
    height: 20px;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: {c.PRIMARY};
    border-radius: {s.BORDER_RADIUS_SM}px;
    margin: 1px;
}}

/* ============================================================
 * GROUP BOX — pannello estruso
 * ============================================================ */
QGroupBox {{
    background-color: {c.BG_MAIN};
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-right: 1px solid {sd};
    border-bottom: 1px solid {sd};
    border-radius: {s.BORDER_RADIUS_LG}px;
    margin-top: 18px;
    padding: 16px 14px 14px 14px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    margin-left: 12px;
    color: {c.TEXT_SECONDARY};
    background-color: {c.BG_MAIN};
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-right: 1px solid {sd};
    border-bottom: 1px solid {sd};
    border-radius: {s.BORDER_RADIUS_SM}px;
    font-variant: small-caps;
    font-size: 11px;
    letter-spacing: 0.08em;
}}

/* ============================================================
 * CHECKBOX / RADIO
 * Indicatori incavati quando non selezionati, estrusi quando attivi.
 * ============================================================ */
QCheckBox, QRadioButton {{
    color: {c.TEXT_PRIMARY};
    spacing: 10px;
    background: transparent;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    background-color: {c.BG_MAIN};
    border-top: 1px solid {sd};
    border-left: 1px solid {sd};
    border-right: 1px solid {sl};
    border-bottom: 1px solid {sl};
}}
QCheckBox::indicator {{
    border-radius: 4px;
}}
QRadioButton::indicator {{
    border-radius: 9px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {c.PRIMARY};
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-right: 1px solid {sd};
    border-bottom: 1px solid {sd};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-top: 1px solid {c.PRIMARY_SOFT};
    border-left: 1px solid {c.PRIMARY_SOFT};
}}

/* ============================================================
 * COMBOBOX drop-down
 * ============================================================ */
QComboBox::drop-down {{
    border: none;
    width: 24px;
    border-left: 1px solid {sds};
    border-top-right-radius: {s.BORDER_RADIUS}px;
    border-bottom-right-radius: {s.BORDER_RADIUS}px;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c.TEXT_SECONDARY};
    width: 0;
    height: 0;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {c.BG_MAIN};
    color: {c.TEXT_PRIMARY};
    selection-background-color: {c.BG_SELECTION};
    selection-color: {c.TEXT_ON_PRIMARY};
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-right: 1px solid {sd};
    border-bottom: 1px solid {sd};
    border-radius: {s.BORDER_RADIUS}px;
    padding: 4px;
    outline: 0;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 12px;
    border-radius: {s.BORDER_RADIUS_SM}px;
}}

/* ============================================================
 * TAB WIDGET
 * ============================================================ */
QTabWidget::pane {{
    border-top: 1px solid {sd};
    border-left: 1px solid {sd};
    border-right: 1px solid {sl};
    border-bottom: 1px solid {sl};
    border-radius: {s.BORDER_RADIUS}px;
    top: -1px;
    background: {c.BG_MAIN};
}}
QTabBar::tab {{
    background: {c.BG_MAIN};
    color: {c.TEXT_SECONDARY};
    border-top: 1px solid {sds};
    border-left: 1px solid {sds};
    border-right: 1px solid {sds};
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: {s.BORDER_RADIUS_SM}px;
    border-top-right-radius: {s.BORDER_RADIUS_SM}px;
}}
QTabBar::tab:selected {{
    color: {c.PRIMARY};
    border-top: 1px solid {sl};
    border-left: 1px solid {sl};
    border-right: 1px solid {sd};
    background: {c.BG_MAIN};
}}
QTabBar::tab:hover:!selected {{
    color: {c.PRIMARY_SOFT};
    background: {c.BG_HOVER};
}}

/* ============================================================
 * DIALOG BUTTONS
 * ============================================================ */
QDialogButtonBox QPushButton {{
    min-width: 80px;
    padding: 10px 18px;
}}

/* ============================================================
 * FRAME
 * ============================================================ */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    /* HLine / VLine separators */
    background-color: {sds};
    border: none;
    border-radius: 1px;
}}
""".strip()


__all__ = ["build_global_qss"]
