"""Deterministic dark-neumorphic painting primitives.

All geometry belongs to the existing widgets.  These functions only paint
inside their current rectangles.  One virtual light source is used throughout:
upper-left light, lower-right shadow.
"""

from __future__ import annotations

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen

from config.theme import ThemeColors


def rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def alpha_color(hex_color: str, alpha: int) -> QColor:
    color = QColor(hex_color)
    color.setAlpha(max(0, min(255, int(alpha))))
    return color


def _edge_depth(width: float, height: float, requested: float) -> float:
    return max(4.0, min(requested, width * 0.22, height * 0.34))


def _edge_gradient(
    painter: QPainter,
    rect: QRectF,
    *,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str,
    alpha: int,
    middle: float = 0.34,
) -> None:
    if rect.width() <= 0.0 or rect.height() <= 0.0 or alpha <= 0:
        return

    gradient = QLinearGradient(
        rect.left() + rect.width() * start[0],
        rect.top() + rect.height() * start[1],
        rect.left() + rect.width() * end[0],
        rect.top() + rect.height() * end[1],
    )
    gradient.setColorAt(0.0, alpha_color(color, alpha))
    gradient.setColorAt(0.32, alpha_color(color, int(alpha * 0.62)))
    gradient.setColorAt(0.68, alpha_color(color, int(alpha * middle)))
    gradient.setColorAt(1.0, alpha_color(color, 0))
    painter.fillRect(rect, gradient)


def _split_edge_lines(
    painter: QPainter,
    surface: QRectF,
    *,
    radius: float,
    top_left: str,
    top_left_alpha: int,
    bottom_right: str,
    bottom_right_alpha: int,
) -> None:
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)

    light_pen = QPen(alpha_color(top_left, top_left_alpha))
    light_pen.setWidthF(1.15)
    painter.setPen(light_pen)
    painter.drawLine(
        QLineF(
            surface.left() + radius * 0.38,
            surface.top() + 0.75,
            surface.right() - radius * 0.48,
            surface.top() + 0.75,
        )
    )
    painter.drawLine(
        QLineF(
            surface.left() + 0.75,
            surface.top() + radius * 0.38,
            surface.left() + 0.75,
            surface.bottom() - radius * 0.48,
        )
    )

    dark_pen = QPen(alpha_color(bottom_right, bottom_right_alpha))
    dark_pen.setWidthF(1.15)
    painter.setPen(dark_pen)
    painter.drawLine(
        QLineF(
            surface.left() + radius * 0.48,
            surface.bottom() - 0.75,
            surface.right() - radius * 0.38,
            surface.bottom() - 0.75,
        )
    )
    painter.drawLine(
        QLineF(
            surface.right() - 0.75,
            surface.top() + radius * 0.48,
            surface.right() - 0.75,
            surface.bottom() - radius * 0.38,
        )
    )
    painter.restore()


def draw_raised_edge_overlay(
    painter: QPainter,
    bounds: QRectF,
    *,
    radius: float,
    depth: float = 12.0,
    light_alpha: int = 190,
    dark_alpha: int = 238,
) -> None:
    """Draw only a raised rim, leaving the center untouched.

    This is intended for an always-on-top, mouse-transparent child overlay so
    complex native children can still paint normally underneath it.
    """

    surface = bounds.adjusted(0.5, 0.5, -0.5, -0.5)
    if surface.width() <= 2.0 or surface.height() <= 2.0:
        return

    d = _edge_depth(surface.width(), surface.height(), depth)
    path = rounded_path(surface, radius)

    painter.save()
    painter.setClipPath(path, Qt.ClipOperation.IntersectClip)
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.top(), surface.width(), d),
        start=(0.5, 0.0),
        end=(0.5, 1.0),
        color=ThemeColors.SHADOW_LIGHT,
        alpha=light_alpha,
        middle=0.24,
    )
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.top(), d, surface.height()),
        start=(0.0, 0.5),
        end=(1.0, 0.5),
        color=ThemeColors.SHADOW_LIGHT,
        alpha=light_alpha,
        middle=0.24,
    )
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.bottom() - d, surface.width(), d),
        start=(0.5, 1.0),
        end=(0.5, 0.0),
        color=ThemeColors.SHADOW_DARK,
        alpha=dark_alpha,
        middle=0.44,
    )
    _edge_gradient(
        painter,
        QRectF(surface.right() - d, surface.top(), d, surface.height()),
        start=(1.0, 0.5),
        end=(0.0, 0.5),
        color=ThemeColors.SHADOW_DARK,
        alpha=dark_alpha,
        middle=0.44,
    )
    painter.restore()

    _split_edge_lines(
        painter,
        surface,
        radius=radius,
        top_left=ThemeColors.SHADOW_LIGHT,
        top_left_alpha=min(235, light_alpha + 28),
        bottom_right=ThemeColors.SHADOW_DARK,
        bottom_right_alpha=min(255, dark_alpha + 12),
    )


def draw_inset_edge_overlay(
    painter: QPainter,
    bounds: QRectF,
    *,
    radius: float,
    depth: float = 14.0,
    dark_alpha: int = 250,
    light_alpha: int = 155,
    focused: bool = False,
) -> None:
    """Draw only the walls of a recessed cavity above native content."""

    surface = bounds.adjusted(0.5, 0.5, -0.5, -0.5)
    if surface.width() <= 2.0 or surface.height() <= 2.0:
        return

    d = _edge_depth(surface.width(), surface.height(), depth)
    path = rounded_path(surface, radius)

    painter.save()
    painter.setClipPath(path, Qt.ClipOperation.IntersectClip)
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.top(), surface.width(), d),
        start=(0.5, 0.0),
        end=(0.5, 1.0),
        color=ThemeColors.SHADOW_DARK,
        alpha=dark_alpha,
        middle=0.46,
    )
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.top(), d, surface.height()),
        start=(0.0, 0.5),
        end=(1.0, 0.5),
        color=ThemeColors.SHADOW_DARK,
        alpha=dark_alpha,
        middle=0.46,
    )
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.bottom() - d, surface.width(), d),
        start=(0.5, 1.0),
        end=(0.5, 0.0),
        color=ThemeColors.SHADOW_LIGHT,
        alpha=light_alpha,
        middle=0.24,
    )
    _edge_gradient(
        painter,
        QRectF(surface.right() - d, surface.top(), d, surface.height()),
        start=(1.0, 0.5),
        end=(0.0, 0.5),
        color=ThemeColors.SHADOW_LIGHT,
        alpha=light_alpha,
        middle=0.24,
    )
    painter.restore()

    _split_edge_lines(
        painter,
        surface,
        radius=radius,
        top_left=ThemeColors.SHADOW_DARK,
        top_left_alpha=235,
        bottom_right=ThemeColors.SHADOW_LIGHT,
        bottom_right_alpha=175,
    )

    if focused:
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        focus_pen = QPen(alpha_color(ThemeColors.BORDER_FOCUS, 225))
        focus_pen.setWidthF(1.4)
        painter.setPen(focus_pen)
        painter.drawPath(
            rounded_path(
                surface.adjusted(2.0, 2.0, -2.0, -2.0),
                max(2.0, radius - 2.0),
            )
        )
        painter.restore()


def draw_panel_material(
    painter: QPainter,
    bounds: QRectF,
    *,
    radius: float,
    elevated: bool = False,
) -> None:
    """Paint the base material for a large panel before children are drawn."""

    surface = bounds.adjusted(0.5, 0.5, -0.5, -0.5)
    gradient = QLinearGradient(surface.topLeft(), surface.bottomRight())
    if elevated:
        gradient.setColorAt(0.0, QColor(ThemeColors.SURFACE_HIGH))
        gradient.setColorAt(0.46, QColor(ThemeColors.BG_ELEVATED))
        gradient.setColorAt(1.0, QColor(ThemeColors.BG_CARD))
    else:
        gradient.setColorAt(0.0, QColor(ThemeColors.SURFACE_MID))
        gradient.setColorAt(0.48, QColor(ThemeColors.BG_CARD))
        gradient.setColorAt(1.0, QColor(ThemeColors.BG_MAIN))
    painter.fillPath(rounded_path(surface, radius), gradient)


def _outer_ring(surface: QRectF, *, radius: float, width: float) -> QPainterPath:
    outer = rounded_path(surface.adjusted(-width, -width, width, width), radius + width)
    return outer.subtracted(rounded_path(surface, radius))


def _direction_band(surface: QRectF, *, width: float, light_side: bool) -> QPainterPath:
    band = QPainterPath()
    if light_side:
        band.addRect(
            QRectF(
                surface.left() - width,
                surface.top() - width,
                surface.width() + width * 2.0,
                width + 1.0,
            )
        )
        band.addRect(
            QRectF(
                surface.left() - width,
                surface.top() - width,
                width + 1.0,
                surface.height() + width * 2.0,
            )
        )
    else:
        band.addRect(
            QRectF(
                surface.left() - width,
                surface.bottom() - 1.0,
                surface.width() + width * 2.0,
                width + 1.0,
            )
        )
        band.addRect(
            QRectF(
                surface.right() - 1.0,
                surface.top() - width,
                width + 1.0,
                surface.height() + width * 2.0,
            )
        )
    return band


def _soft_directional_lobe(
    painter: QPainter,
    surface: QRectF,
    *,
    radius: float,
    offset: float,
    color: str,
    strength: int,
    light_side: bool,
    steps: int = 20,
    spread: float = 10.0,
) -> None:
    zone = spread + abs(offset) + 1.0
    clip = _outer_ring(surface, radius=radius, width=zone)
    clip = clip.intersected(_direction_band(surface, width=zone, light_side=light_side))

    painter.save()
    painter.setClipPath(clip, Qt.ClipOperation.IntersectClip)
    per_step = max(1.0, float(strength) / float(steps))
    translation = -offset if light_side else offset
    for index in range(steps, 0, -1):
        t = index / steps
        layer_spread = spread * t
        alpha = max(1, int(per_step * (0.68 + (1.0 - t) * 0.86)))
        rect = surface.translated(translation, translation).adjusted(
            -layer_spread,
            -layer_spread,
            layer_spread,
            layer_spread,
        )
        painter.fillPath(
            rounded_path(rect, radius + layer_spread),
            alpha_color(color, alpha),
        )
    painter.restore()


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
    """Paint a complete raised surface for buttons/badges/cards."""

    surface = bounds.adjusted(surface_inset, surface_inset, -surface_inset, -surface_inset)
    if surface.width() <= 0.0 or surface.height() <= 0.0:
        return bounds

    light = min(255, light_strength + (24 if hovered else 10))
    dark = min(255, dark_strength + (18 if hovered else 8))
    if disabled:
        light = int(light * 0.42)
        dark = int(dark * 0.42)

    _soft_directional_lobe(
        painter,
        surface,
        radius=radius,
        offset=light_offset,
        color=ThemeColors.SHADOW_LIGHT,
        strength=light,
        light_side=True,
    )
    _soft_directional_lobe(
        painter,
        surface,
        radius=radius,
        offset=dark_offset,
        color=ThemeColors.SHADOW_DARK,
        strength=dark,
        light_side=False,
    )

    gradient = QLinearGradient(surface.topLeft(), surface.bottomRight())
    if disabled:
        gradient.setColorAt(0.0, QColor(ThemeColors.BG_CARD))
        gradient.setColorAt(1.0, QColor(ThemeColors.BG_MAIN))
    elif hovered:
        gradient.setColorAt(0.0, QColor(ThemeColors.SURFACE_HIGH))
        gradient.setColorAt(0.42, QColor(ThemeColors.BG_ELEVATED))
        gradient.setColorAt(1.0, QColor(ThemeColors.SURFACE_LOW))
    else:
        gradient.setColorAt(0.0, QColor(ThemeColors.SURFACE_HIGH))
        gradient.setColorAt(0.50, QColor(ThemeColors.SURFACE_MID))
        gradient.setColorAt(1.0, QColor(ThemeColors.SURFACE_LOW))
    painter.fillPath(rounded_path(surface, radius), gradient)

    draw_raised_edge_overlay(
        painter,
        surface,
        radius=radius,
        depth=min(8.0, max(5.0, surface.height() * 0.20)),
        light_alpha=120 if disabled else (185 if hovered else 165),
        dark_alpha=145 if disabled else (225 if hovered else 205),
    )

    if focused and not disabled:
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(alpha_color(ThemeColors.BORDER_FOCUS, 225))
        pen.setWidthF(1.4)
        painter.setPen(pen)
        painter.drawPath(
            rounded_path(
                surface.adjusted(1.8, 1.8, -1.8, -1.8),
                max(2.0, radius - 1.8),
            )
        )
        painter.restore()

    return surface


def draw_inset_surface(
    painter: QPainter,
    bounds: QRectF,
    *,
    radius: float,
    dark_strength: int,
    light_strength: int,
    depth: float = 13.0,
    focused: bool = False,
    disabled: bool = False,
    fill_base: bool = True,
) -> QRectF:
    """Paint a complete recessed material cavity."""

    surface = bounds.adjusted(1.0, 1.0, -1.0, -1.0)
    if surface.width() <= 0.0 or surface.height() <= 0.0:
        return bounds

    if fill_base:
        gradient = QLinearGradient(surface.topLeft(), surface.bottomRight())
        gradient.setColorAt(0.0, QColor(ThemeColors.SURFACE_LOW))
        gradient.setColorAt(0.50, QColor(ThemeColors.BG_INPUT))
        gradient.setColorAt(1.0, QColor(ThemeColors.BG_INPUT))
        painter.fillPath(rounded_path(surface, radius), gradient)

    draw_inset_edge_overlay(
        painter,
        surface,
        radius=radius,
        depth=depth,
        dark_alpha=min(255, dark_strength),
        light_alpha=min(220, light_strength),
        focused=focused and not disabled,
    )
    return surface


__all__ = [
    "alpha_color",
    "draw_inset_edge_overlay",
    "draw_inset_surface",
    "draw_panel_material",
    "draw_raised_edge_overlay",
    "draw_raised_surface",
    "rounded_path",
]
