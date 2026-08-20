"""Indicatore di stato animato: punto colorato di 8px.

Mostra visivamente lo stato di un processo in background. Per i processi
attivi, l'opacità pulsa tra 0.5 e 1.0 con periodo 1.5s (§3.5 del system
prompt).
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QTimer, Qt, Property, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from config.theme import ThemeColors, ThemeSpacing


class StatusIndicator(QWidget):
    """Punto colorato di stato, con animazione pulsante opzionale.

    Args:
        parent: Widget genitore.

    Signals:
        state_changed: Emesso quando lo stato cambia.
    """

    class State(Enum):
        """Stati possibili del processo monitorato."""

        STOPPED = "stopped"
        RUNNING = "running"
        ERROR = "error"
        PAUSED = "paused"

    state_changed = Signal(object)

    _STATE_COLORS: dict[State, str] = {
        State.STOPPED: ThemeColors.STATUS_STOPPED,
        State.RUNNING: ThemeColors.STATUS_RUNNING,
        State.ERROR: ThemeColors.STATUS_ERROR,
        State.PAUSED: ThemeColors.STATUS_PAUSED,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state: StatusIndicator.State = StatusIndicator.State.STOPPED
        self._opacity: float = 1.0
        self._pulse_phase: float = 0.0
        self._size: int = ThemeSpacing.STATUS_INDICATOR_SIZE
        self.setFixedSize(self._size + 4, self._size + 4)
        self._timer: QTimer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_tick)
        self._update_tooltip()

    def set_state(self, state: "StatusIndicator.State") -> None:
        """Aggiorna lo stato dell'indicatore.

        Args:
            state: Nuovo stato.
        """
        if state == self._state:
            return
        self._state = state
        self._update_tooltip()
        if state == StatusIndicator.State.RUNNING:
            self._timer.start()
        else:
            self._timer.stop()
            self._opacity = 1.0
        self.update()
        self.state_changed.emit(state)

    def get_state(self) -> State:
        """Restituisce lo stato corrente."""
        return self._state

    def _on_tick(self) -> None:
        """Aggiorna l'opacità con una sinusoide lenta."""
        self._pulse_phase = (self._pulse_phase + 0.1) % (2 * 3.14159)
        self._opacity = 0.75 + 0.25 * (
            0.5 + 0.5 * (
                -1 if self._pulse_phase > 3.14159 else 1
            )
        )
        self.update()

    def _update_tooltip(self) -> None:
        """Imposta il tooltip in base allo stato."""
        labels: dict[StatusIndicator.State, str] = {
            StatusIndicator.State.STOPPED: "Arrestato",
            StatusIndicator.State.RUNNING: "In esecuzione",
            StatusIndicator.State.ERROR: "Errore",
            StatusIndicator.State.PAUSED: "In pausa",
        }
        self.setToolTip(labels.get(self._state, ""))

    def paintEvent(self, event: object) -> None:
        """Disegna il cerchio colorato centrato."""
        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color: QColor = QColor(self._STATE_COLORS[self._state])
        color.setAlphaF(self._opacity)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        margin: int = 2
        painter.drawEllipse(
            margin,
            margin,
            self._size,
            self._size,
        )
        painter.end()


__all__ = ["StatusIndicator"]
