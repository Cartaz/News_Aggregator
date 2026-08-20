"""Deterministic dark-neumorphic raster primitives.

The target screenshots showed that QGraphicsEffect output was not surviving
the real QWidget composition path on the target system.  This renderer avoids
that dependency entirely.

All depth is drawn directly *inside the widget's existing pixel rectangle*:
the visible material surface is inset by a few pixels and the reserved pixels
are used for a multi-pass soft shadow.  Geometry reported to layouts does not
change.

No palette value is defined here. RGB values come only from ``ThemeColors``.
"""

from __future__ import annotations

from math import exp

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
)

from config.theme import ThemeColors


def rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def alpha_color(hex_color: str, alpha: int) -> QColor:
    color = QColor(hex_color)
    color.setAlpha(max(0, min(255, int(alpha))))
    return color


def _soft_lobe(
    painter: QPainter,
    surface: QRectF,
    *,
    radius: float,
    offset_x: float,
    offset_y: float,
    color: str,
    strength: int,
    steps: int = 13,
    max_spread: float = 7.0,
) -> None:
    """Approximate a Gaussian lobe with nested translucent rounded shapes.

    This deliberately does not depend on QGraphicsBlurEffect.  Each pass is
    visible in the final QWidget paint buffer and therefore cannot disappear
    because of effect-source clipping.
    """

    # Far, weak passes first; near, stronger passes last.
    for index in range(steps, 0, -1):
        t = index / steps
        spread = max_spread * t

        # Gaussian-like energy distribution.  Individual alpha stays low;
        # overlap creates the soft continuous falloff.
        weight = exp(-2.15 * (t ** 2))
        layer_alpha = max(1, int((strength / steps) * (0.62 + weight)))

        rect = surface.translated(offset_x, offset_y).adjusted(
            -spread,
            -spread,
            spread,
            spread,
        )
        painter.fillPath(
            rounded_path(rect, radius + spread),
            alpha_color(color, layer_alpha),
        )


def draw_raised_surface(
    painter: QPainter,
    bounds: QRectF,
    *,
    radius: float,
    surface_inset: float,
    light_offset: float,
    dark_offset: float,
    light_strength: int,
    dark_strength: int,
    hovered: bool = False,
    focused: bool = False,
    disabled: bool = False,
) -> QRectF:
    """Draw a clearly raised surface while staying inside ``bounds``."""

    surface = bounds.adjusted(
        surface_inset,
        surface_inset,
        -surface_inset,
        -surface_inset,
    )

    light_gain = 18 if hovered else 0
    dark_gain = 12 if hovered else 0

    _soft_lobe(
        painter,
        surface,
        radius=radius,
        offset_x=-light_offset,
        offset_y=-light_offset,
        color=ThemeColors.SHADOW_LIGHT,
        strength=min(255, light_strength + light_gain),
    )
    _soft_lobe(
        painter,
        surface,
        radius=radius,
        offset_x=dark_offset,
        offset_y=dark_offset,
        color=ThemeColors.SHADOW_DARK,
        strength=min(255, dark_strength + dark_gain),
    )

    gradient = QLinearGradient(surface.topLeft(), surface.bottomRight())

    if disabled:
        gradient.setColorAt(0.0, QColor(ThemeColors.BG_CARD))
        gradient.setColorAt(1.0, QColor(ThemeColors.BG_MAIN))
    elif hovered:
        # Same locked palette; only select existing semantic shades.
        gradient.setColorAt(0.0, QColor(ThemeColors.SURFACE_HIGH))
        gradient.setColorAt(0.52, QColor(ThemeColors.BG_ELEVATED))
        gradient.setColorAt(1.0, QColor(ThemeColors.SURFACE_LOW))
    else:
        gradient.setColorAt(0.0, QColor(ThemeColors.SURFACE_HIGH))
        gradient.setColorAt(0.50, QColor(ThemeColors.SURFACE_MID))
        gradient.setColorAt(1.0, QColor(ThemeColors.SURFACE_LOW))

    painter.fillPath(rounded_path(surface, radius), gradient)

    # Broad, faint upper-left material reflection; not a border.
    highlight = surface.adjusted(2.0, 2.0, -2.0, 0.0)
    highlight.setHeight(min(7.0, max(3.0, surface.height() * 0.24)))
    painter.fillPath(
        rounded_path(highlight, max(2.0, radius - 2.0)),
        alpha_color(ThemeColors.SHADOW_LIGHT, 18 if hovered else 13),
    )

    if focused and not disabled:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = painter.pen()
        pen.setColor(QColor(ThemeColors.BORDER_FOCUS))
        pen.setWidthF(1.5)
        painter.setPen(pen)
        painter.drawPath(
            rounded_path(
                surface.adjusted(1.0, 1.0, -1.0, -1.0),
                max(2.0, radius - 1.0),
            )
        )

    return surface


def _edge_gradient(
    painter: QPainter,
    rect: QRectF,
    *,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str,
    alpha: int,
) -> None:
    gradient = QLinearGradient(
        rect.left() + rect.width() * start[0],
        rect.top() + rect.height() * start[1],
        rect.left() + rect.width() * end[0],
        rect.top() + rect.height() * end[1],
    )
    gradient.setColorAt(0.0, alpha_color(color, alpha))
    gradient.setColorAt(0.38, alpha_color(color, int(alpha * 0.52)))
    gradient.setColorAt(1.0, alpha_color(color, 0))
    painter.fillRect(rect, gradient)


def draw_inset_surface(
    painter: QPainter,
    bounds: QRectF,
    *,
    radius: float,
    dark_strength: int,
    light_strength: int,
    depth: float = 11.0,
    focused: bool = False,
    disabled: bool = False,
    fill_base: bool = True,
) -> QRectF:
    """Draw a recessed cavity with directional soft inner falloff."""

    surface = bounds.adjusted(1.0, 1.0, -1.0, -1.0)
    path = rounded_path(surface, radius)

    if fill_base:
        painter.fillPath(
            path,
            QColor(
                ThemeColors.BG_MAIN
                if disabled
                else ThemeColors.BG_INPUT
            ),
        )

    painter.save()
    painter.setClipPath(path)

    # Top and left: virtual light comes from upper-left, so the cavity blocks
    # light there and produces the dominant dark inner falloff.
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.top(), surface.width(), depth),
        start=(0.5, 0.0),
        end=(0.5, 1.0),
        color=ThemeColors.SHADOW_DARK,
        alpha=dark_strength,
    )
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.top(), depth, surface.height()),
        start=(0.0, 0.5),
        end=(1.0, 0.5),
        color=ThemeColors.SHADOW_DARK,
        alpha=dark_strength,
    )

    # Bottom/right: restrained reflected light.
    bottom = QRectF(
        surface.left(),
        surface.bottom() - depth,
        surface.width(),
        depth,
    )
    bottom_gradient = QLinearGradient(
        bottom.left(),
        bottom.bottom(),
        bottom.left(),
        bottom.top(),
    )
    bottom_gradient.setColorAt(
        0.0,
        alpha_color(ThemeColors.SHADOW_LIGHT_SOFT, light_strength),
    )
    bottom_gradient.setColorAt(
        0.45,
        alpha_color(
            ThemeColors.SHADOW_LIGHT_SOFT,
            int(light_strength * 0.42),
        ),
    )
    bottom_gradient.setColorAt(
        1.0,
        alpha_color(ThemeColors.SHADOW_LIGHT_SOFT, 0),
    )
    painter.fillRect(bottom, bottom_gradient)

    right = QRectF(
        surface.right() - depth,
        surface.top(),
        depth,
        surface.height(),
    )
    right_gradient = QLinearGradient(
        right.right(),
        right.top(),
        right.left(),
        right.top(),
    )
    right_gradient.setColorAt(
        0.0,
        alpha_color(ThemeColors.SHADOW_LIGHT_SOFT, light_strength),
    )
    right_gradient.setColorAt(
        0.45,
        alpha_color(
            ThemeColors.SHADOW_LIGHT_SOFT,
            int(light_strength * 0.42),
        ),
    )
    right_gradient.setColorAt(
        1.0,
        alpha_color(ThemeColors.SHADOW_LIGHT_SOFT, 0),
    )
    painter.fillRect(right, right_gradient)

    painter.restore()

    if focused and not disabled:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = painter.pen()
        pen.setColor(QColor(ThemeColors.BORDER_FOCUS))
        pen.setWidthF(1.5)
        painter.setPen(pen)
        painter.drawPath(
            rounded_path(
                surface.adjusted(1.0, 1.0, -1.0, -1.0),
                max(2.0, radius - 1.0),
            )
        )

    return surface


__all__ = [
    "draw_inset_surface",
    "draw_raised_surface",
    "rounded_path",
]
