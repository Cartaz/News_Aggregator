"""Reusable material surfaces for the Dark Neumorphism presentation layer.

The widgets preserve Qt behavior and geometry. For QAbstractScrollArea
subclasses, the final inset rim is painted directly on ``viewport()`` after
native content, matching Qt's documented viewport painting model.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from PySide6.QtCore import QEvent, QRectF, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPalette
from PySide6.QtWidgets import QTableWidget, QTextBrowser, QTreeWidget, QWidget

from config.theme import ThemeColors, ThemeSpacing
from ui.styles.neumorphic_painter import (
    draw_inset_edge_overlay,
    draw_panel_material,
    draw_raised_edge_overlay,
)


class SurfaceTone(str, Enum):
    BASE = "base"
    ELEVATED = "elevated"


class RaisedPanelOverlay(QWidget):
    """Always-on-top, mouse-transparent raised rim for a container widget."""

    def __init__(
        self,
        target: QWidget,
        *,
        radius: float,
        depth: float = 13.0,
    ) -> None:
        super().__init__(target)
        self._target = target
        self._radius = radius
        self._depth = depth
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("background: transparent; border: none;")
        target.installEventFilter(self)
        self.setGeometry(target.rect())
        self.show()
        self.raise_()

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self._target and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.LayoutRequest,
            QEvent.Type.ChildAdded,
            QEvent.Type.ZOrderChange,
        ):
            self.setGeometry(self._target.rect())
            self.raise_()
            self.update()
        return False

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_raised_edge_overlay(
            painter,
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            radius=self._radius,
            depth=self._depth,
            light_alpha=205,
            dark_alpha=245,
        )
        painter.end()


class NeumorphicPanel(QWidget):
    """QWidget with a material body and raised rim; geometry is unchanged."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        radius: float | None = None,
        tone: SurfaceTone | str = SurfaceTone.BASE,
    ) -> None:
        super().__init__(parent)
        self._surface_radius = float(radius or ThemeSpacing.BORDER_RADIUS_LG)
        self._surface_tone = SurfaceTone(tone)
        self.setProperty("neumorphicPanel", True)
        self.setProperty("surfaceTone", self._surface_tone.value)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._surface_overlay = RaisedPanelOverlay(
            self,
            radius=self._surface_radius,
            depth=13.0 if self._surface_tone == SurfaceTone.BASE else 11.0,
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_panel_material(
            painter,
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            radius=self._surface_radius,
            elevated=self._surface_tone == SurfaceTone.ELEVATED,
        )
        painter.end()

    def showEvent(self, event: QEvent) -> None:
        super().showEvent(event)
        self._surface_overlay.setGeometry(self.rect())
        self._surface_overlay.raise_()


class _ViewportSurface(Protocol):
    _inset_radius: float
    _inset_depth: float

    def viewport(self) -> QWidget: ...
    def palette(self) -> QPalette: ...
    def setPalette(self, palette: QPalette) -> None: ...
    def setProperty(self, name: str, value: object) -> bool: ...
    def hasFocus(self) -> bool: ...


def _prepare_inset_view(widget: _ViewportSurface, *, radius: float, depth: float) -> None:
    widget._inset_radius = radius
    widget._inset_depth = depth
    widget.setProperty("neumorphicView", True)
    viewport = widget.viewport()
    viewport.setProperty("neumorphicViewport", True)

    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.Base, QColor(ThemeColors.BG_INPUT))
    palette.setColor(QPalette.ColorRole.Window, QColor(ThemeColors.BG_INPUT))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(ThemeColors.SURFACE_MID))
    palette.setColor(QPalette.ColorRole.Text, QColor(ThemeColors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ThemeColors.BG_SELECTION))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(ThemeColors.TEXT_PRIMARY))
    widget.setPalette(palette)
    viewport.setPalette(palette)


def _paint_inset_rim(widget: _ViewportSurface) -> None:
    viewport = widget.viewport()
    painter = QPainter(viewport)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    draw_inset_edge_overlay(
        painter,
        QRectF(viewport.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
        radius=widget._inset_radius,
        depth=widget._inset_depth,
        dark_alpha=252,
        light_alpha=168,
        focused=widget.hasFocus(),
    )
    painter.end()


class NeumorphicTreeWidget(QTreeWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        _prepare_inset_view(
            self,
            radius=float(ThemeSpacing.BORDER_RADIUS),
            depth=14.0,
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        _paint_inset_rim(self)


class NeumorphicTableWidget(QTableWidget):
    def __init__(
        self,
        rows: int = 0,
        columns: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(rows, columns, parent)
        _prepare_inset_view(
            self,
            radius=float(ThemeSpacing.BORDER_RADIUS),
            depth=14.0,
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        _paint_inset_rim(self)


class NeumorphicTextBrowser(QTextBrowser):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        _prepare_inset_view(
            self,
            radius=float(ThemeSpacing.BORDER_RADIUS),
            depth=13.0,
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        _paint_inset_rim(self)


__all__ = [
    "NeumorphicPanel",
    "NeumorphicTableWidget",
    "NeumorphicTextBrowser",
    "NeumorphicTreeWidget",
    "RaisedPanelOverlay",
    "SurfaceTone",
]
