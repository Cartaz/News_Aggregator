"""Card neumorphic con intestazione in maiuscoletto (small caps).

Le card raggruppano azioni correlate. Nel tema Neumorphism ogni card è
un elemento estruso dallo sfondo: bordo chiaro in alto/sinistra, bordo
scuro in basso/destra, border-radius 16px, padding generoso.
Stesso colore di sfondo del contenitore — è l'ombra a creare la forma.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from config.theme import ThemeColors, ThemeSpacing


class Card(QFrame):
    """Container visivo neumorphic con header small caps e body.

    Args:
        title: Testo intestazione (verrà mostrato in small caps).
        parent: Widget genitore.
    """

    def __init__(
        self,
        title: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._title: str = title
        self._apply_style()
        self._layout: QVBoxLayout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            ThemeSpacing.LG,
            ThemeSpacing.LG,
            ThemeSpacing.LG,
            ThemeSpacing.LG,
        )
        self._layout.setSpacing(ThemeSpacing.SM)
        self._header_label: QLabel = QLabel(title, self)
        self._header_label.setProperty("header", True)
        self._layout.addWidget(self._header_label)
        self._body: QWidget = QWidget(self)
        self._body_layout: QVBoxLayout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(ThemeSpacing.SM)
        self._layout.addWidget(self._body)

    def _apply_style(self) -> None:
        """Applica lo stile card Neumorphism (ombra estrusa)."""
        c = ThemeColors
        s = ThemeSpacing
        self.setStyleSheet(
            f"QFrame#card {{"
            f"  background-color: {c.BG_MAIN};"
            f"  border-top: 1px solid {c.SHADOW_LIGHT};"
            f"  border-left: 1px solid {c.SHADOW_LIGHT};"
            f"  border-right: 1px solid {c.SHADOW_DARK};"
            f"  border-bottom: 1px solid {c.SHADOW_DARK};"
            f"  border-radius: {s.BORDER_RADIUS_LG}px;"
            f"}}"
        )

    def add_widget(self, widget: QWidget) -> None:
        """Aggiunge un widget al body della card.

        Args:
            widget: Widget da aggiungere.
        """
        self._body_layout.addWidget(widget)

    def add_layout(self, layout: object) -> None:
        """Aggiunge un layout al body della card.

        Args:
            layout: QLayout da aggiungere.
        """
        self._body_layout.addLayout(layout)  # type: ignore[arg-type]

    def set_title(self, title: str) -> None:
        """Aggiorna il titolo della card."""
        self._title = title
        self._header_label.setText(title)

    def get_title(self) -> str:
        """Restituisce il titolo corrente."""
        return self._title

    def body(self) -> QWidget:
        """Restituisce il widget body per uso avanzato."""
        return self._body


__all__ = ["Card"]
