"""Native Qt controls with a Dark Neumorphism presentation layer.

Signals, focus semantics, keyboard behaviour and size hints remain those of the
underlying Qt widgets. Only paint operations are customized.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QStyle, QStyleOptionButton, QWidget

from config.theme import ThemeColors, ThemeDepth, ThemeFonts, ThemeSpacing, ThemeTypography
from ui.styles.neumorphic_painter import draw_inset_surface, draw_raised_surface, rounded_path


class NeumorphicButton(QPushButton):
    """A native QPushButton with raised, hover and pressed depth states."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
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
        if event.type() in (QEvent.Type.EnabledChange, QEvent.Type.StyleChange):
            self.update()

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = float(ThemeSpacing.BORDER_RADIUS)

        if self.isDown() or self.isChecked():
            surface = bounds.adjusted(
                ThemeDepth.BUTTON_SURFACE_INSET,
                ThemeDepth.BUTTON_SURFACE_INSET,
                -ThemeDepth.BUTTON_SURFACE_INSET,
                -ThemeDepth.BUTTON_SURFACE_INSET,
            )
            painter.fillPath(rounded_path(surface, radius), QColor(ThemeColors.BG_INPUT))
            surface = draw_inset_surface(
                painter,
                surface.adjusted(-1.0, -1.0, 1.0, 1.0),
                radius=radius,
                dark_strength=190,
                light_strength=78,
                depth=9.0,
                focused=self.hasFocus(),
                disabled=not self.isEnabled(),
                fill_base=False,
            )
        else:
            hovered = self.underMouse() and self.isEnabled()
            surface = draw_raised_surface(
                painter,
                bounds,
                radius=radius,
                surface_inset=ThemeDepth.BUTTON_SURFACE_INSET,
                light_offset=(
                    ThemeDepth.BUTTON_HOVER_OFFSET if hovered else ThemeDepth.BUTTON_OFFSET
                ),
                dark_offset=(
                    ThemeDepth.BUTTON_HOVER_OFFSET if hovered else ThemeDepth.BUTTON_OFFSET
                ),
                light_strength=(
                    ThemeDepth.BUTTON_HOVER_LIGHT_ALPHA
                    if hovered
                    else ThemeDepth.BUTTON_LIGHT_ALPHA
                ),
                dark_strength=(
                    ThemeDepth.BUTTON_HOVER_DARK_ALPHA
                    if hovered
                    else ThemeDepth.BUTTON_DARK_ALPHA
                ),
                blur=(ThemeDepth.BUTTON_HOVER_BLUR if hovered else ThemeDepth.BUTTON_BLUR),
                hovered=hovered,
                focused=self.hasFocus(),
                disabled=not self.isEnabled(),
                dpr=self.devicePixelRatioF(),
            )

        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.rect = surface.toAlignedRect()

        if not self.isEnabled():
            text_color = ThemeColors.TEXT_DISABLED
        elif bool(self.property("danger")):
            text_color = ThemeColors.DANGER
        elif self.underMouse():
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
    """Native QLineEdit painted as a recessed dark-material cavity."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.setFrame(False)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(ThemeColors.TEXT_PRIMARY))
        palette.setColor(
            QPalette.ColorRole.PlaceholderText, QColor(ThemeColors.TEXT_DISABLED)
        )
        palette.setColor(QPalette.ColorRole.Highlight, QColor(ThemeColors.PRIMARY))
        palette.setColor(
            QPalette.ColorRole.HighlightedText, QColor(ThemeColors.TEXT_ON_PRIMARY)
        )
        self.setPalette(palette)

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

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_inset_surface(
            painter,
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            radius=float(ThemeSpacing.BORDER_RADIUS),
            dark_strength=ThemeDepth.INPUT_DARK_ALPHA,
            light_strength=ThemeDepth.INPUT_LIGHT_ALPHA,
            depth=ThemeDepth.INPUT_DEPTH,
            focused=self.hasFocus(),
            disabled=not self.isEnabled(),
            fill_base=True,
        )
        painter.end()
        # QSS removes the native frame/background, so Qt now paints only text,
        # selection, cursor and the clear button over the custom cavity.
        super().paintEvent(event)


class NeumorphicBadge(QLabel):
    """Small raised keyboard-shortcut badge."""

    def __init__(self, shortcut: str, parent: QWidget | None = None) -> None:
        super().__init__(shortcut, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(20)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        font = self.font()
        font.setFamily(ThemeFonts.MONO)
        font.setPixelSize(ThemeTypography.BADGE_SIZE)
        font.setWeight(QFont.Weight(ThemeTypography.BADGE_WEIGHT))
        self.setFont(font)

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        surface = draw_raised_surface(
            painter,
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            radius=float(ThemeSpacing.BORDER_RADIUS_SM),
            surface_inset=ThemeDepth.BADGE_SURFACE_INSET,
            light_offset=ThemeDepth.BADGE_OFFSET,
            dark_offset=ThemeDepth.BADGE_OFFSET,
            light_strength=ThemeDepth.BADGE_LIGHT_ALPHA,
            dark_strength=ThemeDepth.BADGE_DARK_ALPHA,
            blur=ThemeDepth.BADGE_BLUR,
            dpr=self.devicePixelRatioF(),
        )
        painter.setPen(QColor(ThemeColors.TEXT_SECONDARY))
        painter.drawText(surface, Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()


class InsetShadowOverlay(QWidget):
    """Non-interactive inset depth overlay for existing data panels."""

    def __init__(self, target: QWidget, *, radius: float = 12.0) -> None:
        super().__init__(target)
        self._target = target
        self._radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        target.installEventFilter(self)
        self.setGeometry(target.rect())
        self.show()
        self.raise_()

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self._target and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.LayoutRequest,
        ):
            self.setGeometry(self._target.rect())
            self.raise_()
            self.update()
        return super().eventFilter(watched, event)

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_inset_surface(
            painter,
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            radius=self._radius,
            dark_strength=ThemeDepth.PANEL_DARK_ALPHA,
            light_strength=ThemeDepth.PANEL_LIGHT_ALPHA,
            depth=ThemeDepth.PANEL_DEPTH,
            fill_base=False,
        )
        painter.end()


def install_inset_overlay(
    widget: QWidget,
    *,
    radius: float = 12.0,
    use_viewport: bool = False,
) -> InsetShadowOverlay:
    """Add inset depth without changing the target widget's geometry."""

    target = widget
    if use_viewport and hasattr(widget, "viewport"):
        target = widget.viewport()  # type: ignore[assignment]

    overlay = InsetShadowOverlay(target, radius=radius)
    overlays = getattr(widget, "_neumorphic_overlays", None)
    if overlays is None:
        overlays = []
        setattr(widget, "_neumorphic_overlays", overlays)
    overlays.append(overlay)
    return overlay


__all__ = [
    "InsetShadowOverlay",
    "NeumorphicBadge",
    "NeumorphicButton",
    "NeumorphicLineEdit",
    "install_inset_overlay",
]
