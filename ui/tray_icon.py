"""Icona nel system tray con menu contestuale e badge articoli non letti.

Implementa un ``QSystemTrayIcon`` con icona SVG dell'app, menu
contestuale che replica le azioni principali dell'app, e badge dinamico
che mostra il numero totale di articoli non letti (sovrapposto
all'icona in alto a destra, in arancione Neumorphism — senza sfondo).

L'uscita avviene tramite il pulsante X (con ``close_to_tray=True`` la
finestra viene solo nascosta, NON si esce), Ctrl+Q, o la voce "Esci"
nel menu tray — questi ultimi due invocano ``QApplication.quit()``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from config.constants import Paths
from config.theme import ThemeColors

logger = logging.getLogger(__name__)


# Dimensioni canvas badge. 32px è la dimensione standard hicolor per
# system tray su KDE Plasma 6 / GTK (sufficientemente grande da
# mostrare testo leggibile). L'icona base viene scalata per riempire
# l'intero canvas, così il numero in alto a destra è ben visibile.
_BADGE_ICON_SIZE: int = 32
# Colore del numero: arancione Neumorphism (PRIMARY = #ff6600),
# in linea con il resto della UI. Il valore è preso da ThemeColors
# per coerenza (vincolo §5.1.5: niente hex hardcoded).
_BADGE_TEXT_COLOR: QColor = QColor(ThemeColors.PRIMARY)
# Limite oltre il quale mostriamo "99+" invece del numero
_BADGE_OVERFLOW: int = 99


class TrayIcon(QWidget):
    """Wrapper widget per QSystemTrayIcon + menu contestuale + badge.

    Args:
        parent: Widget genitore.

    Signals:
        show_window_requested: Emesso quando l'utente clicca l'icona
            o seleziona "Mostra" nel menu.
        refresh_all_requested: Emesso quando l'utente seleziona
            "Aggiorna tutti" nel menu.
        quit_requested: Emesso quando l'utente seleziona "Esci"
            nel menu. L'app deve chiudere definitivamente (non
            solo nascondere la finestra).
    """

    show_window_requested = Signal()
    refresh_all_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tray: QSystemTrayIcon = QSystemTrayIcon(self)
        self._base_icon: QIcon = self._load_icon()
        self._unread_count: int = 0
        self._tray.setIcon(self._base_icon)
        self._tray.setToolTip("News Aggregator")
        self._menu: QMenu = self._build_menu()
        self._tray.setContextMenu(self._menu)
        self._connect_signals()

    def _load_icon(self) -> QIcon:
        """Carica l'icona SVG dell'app, con fallback di sistema."""
        icon_path: Path = Paths.APP_ICON
        if icon_path.exists():
            return QIcon(str(icon_path))
        logger.warning(
            "Icona SVG non trovata in %s, uso icona di fallback",
            icon_path,
        )
        return QIcon.fromTheme("application-rss+xml", QIcon.fromTheme("text-html"))

    def _build_menu(self) -> QMenu:
        """Costruisce il menu contestuale del tray."""
        menu: QMenu = QMenu()
        show_action: QAction = QAction("Mostra finestra", menu)
        refresh_action: QAction = QAction("Aggiorna tutti i feed", menu)
        menu.addSeparator()
        quit_action: QAction = QAction("Esci", menu)

        show_action.triggered.connect(self.show_window_requested.emit)
        refresh_action.triggered.connect(self.refresh_all_requested.emit)
        # "Esci" dal tray deve terminare l'app definitivamente, non
        # solo nascondere la finestra. Emettiamo il segnale così
        # l'applicazione può decidere (es. conferma uscita, cleanup).
        quit_action.triggered.connect(self.quit_requested.emit)
        # Compatibilità: chi chiama QApplication.quit direttamente
        # funziona ancora, ma preferiamo passare per il segnale.
        quit_action.triggered.connect(QApplication.quit)

        menu.addAction(show_action)
        menu.addAction(refresh_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        return menu

    def _connect_signals(self) -> None:
        """Collega i segnali del tray."""
        self._tray.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Mostra la finestra principale al click singolo sull'icona."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window_requested.emit()

    def show(self) -> None:
        """Rende visibile l'icona nel tray."""
        self._tray.show()

    def hide(self) -> None:
        """Nasconde l'icona dal tray."""
        self._tray.hide()

    def show_message(
        self,
        title: str,
        message: str,
        msecs: int = 5000,
    ) -> None:
        """Mostra una notifica balloon dal tray.

        Args:
            title: Titolo del messaggio.
            message: Corpo del messaggio.
            msecs: Durata in millisecondi.
        """
        if not self._tray.supportsMessages():
            logger.info(
                "Tray non supporta messaggi: %s — %s",
                title,
                message,
            )
            return
        self._tray.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            msecs,
        )

    def set_unread_count(self, count: int) -> None:
        """Aggiorna il badge del numero di articoli non letti.

        Disegna il numero (o "99+" se > 99) in alto a destra dell'icona,
        colorato di arancione Neumorphism, senza alcuno sfondo. Aggiorna
        anche il tooltip dell'icona.

        Args:
            count: Numero di articoli non letti (>= 0).
        """
        if count < 0:
            count = 0
        if count == self._unread_count:
            return  # Nessun cambiamento, evitiamo ridisegnamento inutile
        self._unread_count = count

        # Tooltip aggiornato con il conteggio
        if count > 0:
            self._tray.setToolTip(
                f"News Aggregator — {count} articoli non letti"
            )
        else:
            self._tray.setToolTip("News Aggregator")

        # Rigenera l'icona con il badge se count > 0, altrimenti icona pulita
        if count > 0:
            self._tray.setIcon(self._render_icon_with_badge(count))
        else:
            self._tray.setIcon(self._base_icon)

    def get_unread_count(self) -> int:
        """Restituisce il conteggio corrente (per test)."""
        return self._unread_count

    def _render_icon_with_badge(self, count: int) -> QIcon:
        """Disegna l'icona base massimizzata con il numero in alto a destra.

        Layout:
        - Canvas 32x32 pixel (dimensione standard hicolor tray su KDE/GTK)
        - Icona base scalata per riempire l'intero canvas (massima visibilità)
        - Numero (o "99+") in alto a destra, colorato di arancione
          Neumorphism (#ff6600 = ThemeColors.PRIMARY), SENZA alcuno
          sfondo/cerchio/bordo
        - Font grassetto, dimensione dinamica in base al numero di cifre:
          1 cifra → 18px, 2 cifre → 14px, "99+" → 11px

        Args:
            count: Numero da mostrare (se > 99, mostra "99+").

        Returns:
            QIcon con numero sovrapposto.
        """
        pixmap: QPixmap = QPixmap(_BADGE_ICON_SIZE, _BADGE_ICON_SIZE)
        pixmap.fill(QColor(0, 0, 0, 0))  # sfondo trasparente

        painter: QPainter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform, True
        )

        # 1. Disegna l'icona base scalata al massimo per riempire il canvas.
        #    QPainter.paint() con rettangolo (0,0,W,H) ridimensiona l'icona
        #    SVG preservando le proporzioni. L'icona di news-aggregator.svg
        #    è quadrata quindi riempie perfettamente 32x32.
        self._base_icon.paint(
            painter,
            0, 0, _BADGE_ICON_SIZE, _BADGE_ICON_SIZE,
        )

        # 2. Testo del numero (o "99+")
        if count > _BADGE_OVERFLOW:
            text: str = f"{_BADGE_OVERFLOW}+"
        else:
            text = str(count)

        # 3. Font: grassetto, dimensione dinamica in base alla lunghezza
        #    del testo così sta dentro il canvas senza overflow.
        #    - 1 cifra (1-9):     18px — massima leggibilità
        #    - 2 cifre (10-99):   14px — ancora leggibile
        #    - "99+":              11px — stringa più lunga, font più piccolo
        text_len: int = len(text)
        if text_len <= 1:
            font_size: int = 18
        elif text_len == 2:
            font_size = 14
        else:
            font_size = 11

        font: QFont = QFont()
        # Usiamo il font sans dell'app (Noto Sans) per coerenza col tema
        from config.theme import ThemeFonts
        font.setFamily(ThemeFonts.SANS)
        font.setPixelSize(font_size)
        font.setBold(True)
        painter.setFont(font)

        # 4. Calcola il bounding rect del testo per posizionarlo in alto
        #    a destra. Usiamo un rettangolo largo quanto il canvas così
        #    AlignRight | AlignTop lo posiziona nel angolo superiore destro.
        text_rect: QRectF = QRectF(
            0, 0, _BADGE_ICON_SIZE, _BADGE_ICON_SIZE
        )

        # 5. Disegna il testo in arancione, senza sfondo (nessun fillPath).
        #    Per migliorare la leggibilità su sfondi di colore variabile
        #    (l'icona sotto può essere chiara o scura), aggiungiamo una
        #    sottile ombra nera semitrasparente disegnando il testo
        #    sfalsato di 1px in nero prima del testo arancione.
        painter.setPen(QColor(0, 0, 0, 200))  # ombra nera semitrasparente
        painter.drawText(
            text_rect.adjusted(1, 1, 1, 1),
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop),
            text,
        )
        painter.setPen(_BADGE_TEXT_COLOR)  # testo arancione
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop),
            text,
        )

        painter.end()

        # 6. Crea l'icona e aggiungi pixmap scalate per size comuni
        #    così Qt sceglie quella giusta quando ridimensiona il tray.
        icon: QIcon = QIcon(pixmap)
        for size in (16, 22, 24, 32, 48, 64):
            if size == _BADGE_ICON_SIZE:
                icon.addPixmap(pixmap)
            else:
                icon.addPixmap(
                    pixmap.scaled(
                        size, size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ),
                )
        return icon


__all__ = ["TrayIcon"]
