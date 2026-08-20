"""Badge visuale per scorciatoie da tastiera.

Mostra la combinazione di tasti (es. ``Ctrl+R``) accanto ai pulsanti.
Nel tema Neumorphism il badge è una pill neumorphic estrusa di piccole
dimensioni, con testo in accento soft.
Il badge è puramente visivo: la registrazione della scorciatoia avviene
in ``QShortcut`` nel widget che lo usa.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from config.theme import ThemeColors, ThemeFonts, ThemeSpacing, ThemeTypography


class ShortcutBadge(QLabel):
    """Etichetta piccola che mostra una scorciatoia tastiera.

    Args:
        shortcut: Combinazione tasti (es. ``Ctrl+N``).
        parent: Widget genitore.
    """

    def __init__(
        self,
        shortcut: str,
        parent: object | None = None,
    ) -> None:
        super().__init__(shortcut, parent=parent)  # type: ignore[arg-type]
        self._shortcut: str = shortcut
        self.setObjectName("shortcutBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(20)
        self._apply_style()

    def _apply_style(self) -> None:
        """Applica lo stile Neumorphism (pill estrusa mini)."""
        c = ThemeColors
        s = ThemeSpacing
        t = ThemeTypography
        self.setStyleSheet(
            f"QLabel#shortcutBadge {{"
            f"  background-color: {c.BG_MAIN};"
            f"  color: {c.TEXT_SECONDARY};"
            f"  border-top: 1px solid {c.SHADOW_LIGHT};"
            f"  border-left: 1px solid {c.SHADOW_LIGHT};"
            f"  border-right: 1px solid {c.SHADOW_DARK};"
            f"  border-bottom: 1px solid {c.SHADOW_DARK};"
            f"  border-radius: {s.BORDER_RADIUS_SM}px;"
            f"  padding: 2px 8px;"
            f"  font-size: {t.BADGE_SIZE}px;"
            f"  font-weight: {t.BADGE_WEIGHT};"
            f"  font-family: '{ThemeFonts.MONO}', '{ThemeFonts.FALLBACK_MONO}';"
            f"}}"
        )

    def set_shortcut(self, shortcut: str) -> None:
        """Aggiorna la scorciatoia mostrata.

        Args:
            shortcut: Nuova combinazione.
        """
        self._shortcut = shortcut
        self.setText(shortcut)

    def get_shortcut(self) -> str:
        """Restituisce la scorciatoia corrente."""
        return self._shortcut


__all__ = ["ShortcutBadge"]
