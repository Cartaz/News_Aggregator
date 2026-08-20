"""Visual keyboard shortcut badge with deterministic neumorphic painting."""

from __future__ import annotations

from ui.widgets.neumorphic_controls import NeumorphicBadge


class ShortcutBadge(NeumorphicBadge):
    """Preserves the original ShortcutBadge public API."""

    def __init__(
        self,
        shortcut: str,
        parent: object | None = None,
    ) -> None:
        super().__init__(shortcut, parent=parent)  # type: ignore[arg-type]
        self._shortcut: str = shortcut
        self.setObjectName("shortcutBadge")

    def set_shortcut(self, shortcut: str) -> None:
        self._shortcut = shortcut
        self.setText(shortcut)
        self.update()

    def get_shortcut(self) -> str:
        return self._shortcut


__all__ = ["ShortcutBadge"]
