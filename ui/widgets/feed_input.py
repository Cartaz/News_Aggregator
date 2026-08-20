"""Widget composito per l'inserimento di un nuovo URL feed.

Combina ``QLineEdit`` + ``ActionButton`` in un layout orizzontale.
Valida l'URL prima di emettere ``feed_submitted``.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QWidget,
)

from config.constants import Shortcuts
from ui.widgets.action_button import ActionButton
from ui.widgets.neumorphic_controls import NeumorphicLineEdit

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    """Verifica sintatticamente che l'URL sia ben formato.

    Accetta solo schemi http/https.

    Args:
        url: URL da validare.

    Returns:
        True se l'URL è valido.
    """
    if not url or not url.strip():
        return False
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except (ValueError, TypeError):
        return False


def normalize_url(url: str) -> str:
    """Normalizza un URL aggiungendo lo schema ``https://`` se mancante.

    Accetta input come ``guru3d.com`` o ``www.guru3d.com`` e restituisce
    ``https://guru3d.com``. URL già completi (con schema) sono restituiti
    invariati (a parte il strip).

    Args:
        url: URL grezzo immesso dall'utente.

    Returns:
        URL normalizzato con schema https://.

    Raises:
        ValueError: Se l'URL non contiene un hostname valido.
    """
    cleaned: str = (url or "").strip()
    if not cleaned:
        raise ValueError("URL vuoto")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    if not is_valid_url(cleaned):
        raise ValueError(f"URL non valido: {url}")
    return cleaned


class FeedInput(QWidget):
    """Input URL + pulsante aggiungi, con scorciatoia ``Ctrl+N``.

    Args:
        parent: Widget genitore.

    Signals:
        feed_submitted: Emesso con l'URL normalizzato quando l'utente
            preme Invio o clicca Aggiungi.
    """

    feed_submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Costruisce il layout orizzontale."""
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
        """Collega i segnali del widget."""
        self._url_edit.returnPressed.connect(self._submit)
        self._add_button.clicked.connect(self._submit)

    def _submit(self) -> None:
        """Normalizza e propaga l'URL immesso.

        Accetta anche URL senza schema (es. ``guru3d.com``): viene
        aggiunto automaticamente ``https://``.
        """
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
        """Attiva il focus sul campo URL."""
        self._url_edit.setFocus()

    def get_text(self) -> str:
        """Restituisce il testo corrente (non validato)."""
        return self._url_edit.text()


__all__ = ["FeedInput", "is_valid_url", "normalize_url"]
