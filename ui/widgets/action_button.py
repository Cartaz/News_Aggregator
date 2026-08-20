"""Pulsante d'azione con badge scorciatoia e stile Neumorphism.

Combina un ``QPushButton`` con un ``ShortcutBadge``. Registra la
scorciatoia nel sistema globale tramite ``QShortcut`` (non solo visiva).
Lo stile (estruso, hover con ombra ridotta, pressed con ombra invertita)
è definito nel QSS globale di ``ui.styles.neumorphism``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from ui.widgets.shortcut_badge import ShortcutBadge


class ActionButton(QWidget):
    """Pulsante d'azione con scorciatoia tastiera registrata.

    Args:
        label: Testo del pulsante.
        shortcut: Combinazione tasti (es. ``Ctrl+N``); vuoto per nessuna.
        danger: Se True, usa lo stile distruttivo (Arancione).
        parent: Widget genitore.

    Signals:
        clicked: Emesso al click del pulsante o alla pressione della
            scorciatoia.
    """

    clicked = Signal()

    def __init__(
        self,
        label: str,
        shortcut: str = "",
        danger: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._shortcut_str: str = shortcut
        self._danger: bool = danger
        self._setup_ui(label)

    def _setup_ui(self, label: str) -> None:
        """Configura il layout del widget."""
        layout: QHBoxLayout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._button: QPushButton = QPushButton(label, self)
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._danger:
            self._button.setProperty("danger", True)
        self._button.clicked.connect(self.clicked.emit)
        layout.addWidget(self._button)

        if self._shortcut_str:
            self._badge: ShortcutBadge = ShortcutBadge(self._shortcut_str, self)
            layout.addWidget(self._badge)
            self._shortcut: QShortcut = QShortcut(
                QKeySequence(self._shortcut_str), self
            )
            self._shortcut.activated.connect(self.clicked.emit)

        layout.addStretch(1)

    def set_text(self, text: str) -> None:
        """Aggiorna il testo del pulsante."""
        self._button.setText(text)

    def set_enabled(self, enabled: bool) -> None:
        """Abilita/disabilita il pulsante."""
        self._button.setEnabled(enabled)

    def is_enabled(self) -> bool:
        """Restituisce True se il pulsante è abilitato."""
        return self._button.isEnabled()

    def click(self) -> None:
        """Programmaticamente attiva il pulsante."""
        self._button.click()


__all__ = ["ActionButton"]
