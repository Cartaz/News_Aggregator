"""Widget composito per l'inserimento di un nuovo URL feed."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from config.constants import Shortcuts
from ui.widgets.action_button import ActionButton
from ui.widgets.neumorphic_controls import NeumorphicLineEdit

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    """Accetta URL HTTP(S) con hostname sintatticamente utilizzabile."""

    if not url or not url.strip():
        return False
    cleaned = url.strip()
    if any(ch.isspace() for ch in cleaned):
        return False
    try:
        parsed = urlparse(cleaned)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc or parsed.hostname is None:
            return False
        if any(ch.isspace() for ch in parsed.netloc):
            return False
        _ = parsed.port
        return True
    except (ValueError, TypeError):
        return False


def normalize_url(url: str) -> str:
    cleaned: str = (url or "").strip()
    if not cleaned:
        raise ValueError("URL vuoto")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    if not is_valid_url(cleaned):
        raise ValueError(f"URL non valido: {url}")
    return cleaned


class FeedInput(QWidget):
    feed_submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout: QHBoxLayout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._url_edit: QLineEdit = NeumorphicLineEdit(self)
        self._url_edit.setPlaceholderText(
            "es. guru3d.com o https://example.com/feed — Invio o Ctrl+N"
        )
        self._url_edit.setClearButtonEnabled(True)
        layout.addWidget(self._url_edit, stretch=1)

        self._add_button: ActionButton = ActionButton(
            label="Aggiungi feed",
            shortcut=Shortcuts.ADD_FEED,
            parent=self,
        )
        layout.addWidget(self._add_button)

    def _connect_signals(self) -> None:
        self._url_edit.returnPressed.connect(self._submit)
        self._add_button.clicked.connect(self._submit)

    def _submit(self) -> None:
        raw: str = self._url_edit.text().strip()
        try:
            url: str = normalize_url(raw)
        except ValueError as exc:
            logger.warning("URL non valido ignorato: %r (%s)", raw, exc)
            self._url_edit.setFocus()
            return
        self.feed_submitted.emit(url)
        self._url_edit.clear()

    def set_focus(self) -> None:
        self._url_edit.setFocus()

    def get_text(self) -> str:
        return self._url_edit.text()


__all__ = ["FeedInput", "is_valid_url", "normalize_url"]
