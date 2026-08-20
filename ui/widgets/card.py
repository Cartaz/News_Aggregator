"""Card widget with the existing API and a real dark-neumorphic material skin."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPaintEvent, QPainter
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from config.theme import ThemeSpacing
from ui.styles.neumorphic_painter import draw_panel_material, draw_raised_edge_overlay


class Card(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setStyleSheet("QFrame#card { background: transparent; border: none; }")

        self._title = title
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            ThemeSpacing.LG,
            ThemeSpacing.LG,
            ThemeSpacing.LG,
            ThemeSpacing.LG,
        )
        self._layout.setSpacing(ThemeSpacing.SM)

        self._header_label = QLabel(title, self)
        self._header_label.setProperty("header", True)
        self._layout.addWidget(self._header_label)

        self._body = QWidget(self)
        self._body.setAutoFillBackground(False)
        self._body.setStyleSheet("background: transparent;")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(ThemeSpacing.SM)
        self._layout.addWidget(self._body)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        draw_panel_material(
            painter,
            bounds,
            radius=float(ThemeSpacing.BORDER_RADIUS_LG),
            elevated=True,
        )
        draw_raised_edge_overlay(
            painter,
            bounds,
            radius=float(ThemeSpacing.BORDER_RADIUS_LG),
            depth=12.0,
            light_alpha=200,
            dark_alpha=242,
        )
        painter.end()

    def add_widget(self, widget: QWidget) -> None:
        self._body_layout.addWidget(widget)

    def add_layout(self, layout: object) -> None:
        self._body_layout.addLayout(layout)  # type: ignore[arg-type]

    def set_title(self, title: str) -> None:
        self._title = title
        self._header_label.setText(title)

    def get_title(self) -> str:
        return self._title

    def body(self) -> QWidget:
        return self._body


__all__ = ["Card"]
