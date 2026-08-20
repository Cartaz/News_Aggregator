"""Custom-painted interactive controls for the Dark Neumorphism theme."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPaintEvent, QPainter, QPalette
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QStyle, QStyleOptionButton, QWidget

from config.theme import ThemeColors, ThemeDepth, ThemeFonts, ThemeSpacing, ThemeTypography
from ui.styles.neumorphic_painter import (
    draw_inset_edge_overlay,
    draw_inset_surface,
    draw_raised_surface,
)


class NeumorphicButton(QPushButton):
    """QPushButton semantics with a deterministic raised/recessed skin."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.setProperty("neumorphic", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def enterEvent(self, event: QEvent) -> None:
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        self.update()

    def focusInEvent(self, event: QEvent) -> None:
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event: QEvent) -> None:
        super().focusOutEvent(event)
        self.update()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange:
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = float(ThemeSpacing.BORDER_RADIUS)
        inset = max(5.5, float(ThemeDepth.BUTTON_SURFACE_INSET))
        offset = max(5.5, float(ThemeDepth.BUTTON_OFFSET))

        if self.isDown() or self.isChecked():
            surface = draw_inset_surface(
                painter,
                bounds.adjusted(inset, inset, -inset, -inset),
                radius=radius,
                dark_strength=min(255, ThemeDepth.BUTTON_DARK_ALPHA + 32),
                light_strength=155,
                depth=11.0,
                focused=self.hasFocus(),
                disabled=not self.isEnabled(),
                fill_base=True,
            )
        else:
            surface = draw_raised_surface(
                painter,
                bounds,
                radius=radius,
                surface_inset=inset,
                light_offset=offset,
                dark_offset=offset,
                light_strength=(
                    min(255, ThemeDepth.BUTTON_HOVER_LIGHT_ALPHA + 32)
                    if self.underMouse()
                    else min(255, ThemeDepth.BUTTON_LIGHT_ALPHA + 24)
                ),
                dark_strength=(
                    min(255, ThemeDepth.BUTTON_HOVER_DARK_ALPHA + 22)
                    if self.underMouse()
                    else min(255, ThemeDepth.BUTTON_DARK_ALPHA + 16)
                ),
                hovered=self.underMouse(),
                focused=self.hasFocus(),
                disabled=not self.isEnabled(),
            )

        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.rect = surface.toAlignedRect()

        if not self.isEnabled():
            text_color = ThemeColors.TEXT_DISABLED
        elif bool(self.property("danger")):
            text_color = ThemeColors.DANGER
        elif self.underMouse() or self.hasFocus():
            text_color = ThemeColors.PRIMARY_SOFT
        else:
            text_color = ThemeColors.TEXT_PRIMARY
        option.palette.setColor(QPalette.ColorRole.ButtonText, QColor(text_color))

        self.style().drawControl(
            QStyle.ControlElement.CE_PushButtonLabel,
            option,
            painter,
            self,
        )
        painter.end()


class NeumorphicLineEdit(QLineEdit):
    """QLineEdit rendered as a true recessed cavity.

    Painting is deliberately three-pass: material background, native text/caret,
    then the inset rim above native painting.  This prevents Qt's standard
    line-edit rendering from visually flattening the cavity.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.setProperty("neumorphic", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setFrame(False)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(ThemeColors.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(ThemeColors.TEXT_DISABLED))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(ThemeColors.PRIMARY))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(ThemeColors.TEXT_ON_PRIMARY))
        self.setPalette(palette)

    def focusInEvent(self, event: QEvent) -> None:
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event: QEvent) -> None:
        super().focusOutEvent(event)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        bounds = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = float(ThemeSpacing.BORDER_RADIUS)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_inset_surface(
            painter,
            bounds,
            radius=radius,
            dark_strength=min(255, ThemeDepth.INPUT_DARK_ALPHA + 32),
            light_strength=min(220, ThemeDepth.INPUT_LIGHT_ALPHA + 40),
            depth=13.0,
            focused=False,
            disabled=not self.isEnabled(),
            fill_base=True,
        )
        painter.end()

        super().paintEvent(event)

        rim = QPainter(self)
        rim.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_inset_edge_overlay(
            rim,
            bounds,
            radius=radius,
            depth=13.0,
            dark_alpha=252 if self.isEnabled() else 145,
            light_alpha=170 if self.isEnabled() else 92,
            focused=self.hasFocus() and self.isEnabled(),
        )
        rim.end()


class NeumorphicBadge(QLabel):
    """Raised shortcut keycap using the same material language as buttons."""

    def __init__(self, shortcut: str, parent: QWidget | None = None) -> None:
        super().__init__(shortcut, parent)
        self.setProperty("neumorphic", True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(20)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        font = self.font()
        font.setFamily(ThemeFonts.MONO)
        font.setPixelSize(ThemeTypography.BADGE_SIZE)
        font.setWeight(QFont.Weight(ThemeTypography.BADGE_WEIGHT))
        self.setFont(font)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        surface = draw_raised_surface(
            painter,
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            radius=float(ThemeSpacing.BORDER_RADIUS_SM),
            surface_inset=max(2.5, float(ThemeDepth.BADGE_SURFACE_INSET)),
            light_offset=max(3.5, float(ThemeDepth.BADGE_OFFSET)),
            dark_offset=max(3.5, float(ThemeDepth.BADGE_OFFSET)),
            light_strength=min(255, ThemeDepth.BADGE_LIGHT_ALPHA + 34),
            dark_strength=min(255, ThemeDepth.BADGE_DARK_ALPHA + 24),
        )
        painter.setPen(QColor(ThemeColors.PRIMARY_SOFT))
        painter.drawText(surface, Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()


# Compatibility shim retained for older call sites.  New large views use the
# dedicated classes in neumorphic_surfaces.py and paint directly on viewport().
def install_inset_overlay(
    widget: QWidget,
    *,
    radius: float = 12.0,
    use_viewport: bool = False,
) -> QWidget:
    target = widget.viewport() if use_viewport and hasattr(widget, "viewport") else widget

    class _InsetCompatOverlay(QWidget):
        def __init__(self, parent: QWidget) -> None:
            super().__init__(parent)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setGeometry(parent.rect())
            parent.installEventFilter(self)
            self.show()
            self.raise_()

        def eventFilter(self, watched: object, event: QEvent) -> bool:
            if watched is target and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
                self.setGeometry(target.rect())
                self.raise_()
            return False

        def paintEvent(self, event: QPaintEvent) -> None:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            draw_inset_edge_overlay(
                p,
                QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
                radius=radius,
                depth=13.0,
            )
            p.end()

    overlay = _InsetCompatOverlay(target)
    setattr(widget, "_neumorphic_compat_overlay", overlay)
    return overlay


__all__ = [
    "NeumorphicBadge",
    "NeumorphicButton",
    "NeumorphicLineEdit",
    "install_inset_overlay",
]
