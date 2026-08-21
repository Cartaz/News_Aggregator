"""Raster primitives for deterministic Dark Neumorphism on Qt Widgets.

The defining raised shadow is rendered off-screen and then composited by the
widget's own paint event. This gives us two independent, genuinely blurred
lobes (upper-left highlight + lower-right shadow) without relying on a single
``QGraphicsDropShadowEffect`` attached to the live widget.

All painting stays inside the widget's existing rectangle. No size hint,
layout margin, splitter size or control geometry is changed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QGraphicsBlurEffect, QGraphicsScene

from config.theme import ThemeColors


@dataclass(frozen=True)
class _MaskKey:
    width: int
    height: int
    left: int
    top: int
    right: int
    bottom: int
    radius: int
    blur: int


_MASK_CACHE: dict[_MaskKey, QImage] = {}
_CACHE_LIMIT = 72


def rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def alpha_color(hex_color: str, alpha: int) -> QColor:
    color = QColor(hex_color)
    color.setAlpha(max(0, min(255, int(alpha))))
    return color


def _evict_if_needed() -> None:
    # Widgets usually reuse only a handful of sizes. A tiny FIFO-ish cache is
    # enough and avoids keeping large high-DPI buffers forever after resizing.
    while len(_MASK_CACHE) >= _CACHE_LIMIT:
        _MASK_CACHE.pop(next(iter(_MASK_CACHE)))


def _blurred_round_rect_mask(
    width: float,
    height: float,
    surface: QRectF,
    radius: float,
    blur: float,
    dpr: float,
) -> QImage:
    """Return a cached blurred alpha mask in device pixels."""

    scale = max(1.0, float(dpr))
    pw = max(1, int(ceil(width * scale)))
    ph = max(1, int(ceil(height * scale)))

    left = int(round(surface.left() * scale))
    top = int(round(surface.top() * scale))
    right = int(round(surface.right() * scale))
    bottom = int(round(surface.bottom() * scale))
    pradius = max(1, int(round(radius * scale)))
    pblur = max(1, int(round(blur * scale)))

    key = _MaskKey(pw, ph, left, top, right, bottom, pradius, pblur)
    cached = _MASK_CACHE.get(key)
    if cached is not None:
        return cached

    source = QImage(pw, ph, QImage.Format.Format_ARGB32_Premultiplied)
    source.fill(Qt.GlobalColor.transparent)

    painter = QPainter(source)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    physical_rect = QRectF(
        float(left),
        float(top),
        float(max(1, right - left)),
        float(max(1, bottom - top)),
    )
    painter.fillPath(
        rounded_path(physical_rect, float(pradius)),
        QColor(255, 255, 255, 255),
    )
    painter.end()

    # QGraphicsBlurEffect is used only as an off-screen raster operator. The
    # final widget does not own a graphics effect, so compositor/effect-source
    # clipping cannot remove one of the two neumorphic lobes.
    scene = QGraphicsScene()
    scene.setSceneRect(0.0, 0.0, float(pw), float(ph))
    item = scene.addPixmap(QPixmap.fromImage(source))
    blur_effect = QGraphicsBlurEffect()
    blur_effect.setBlurRadius(float(pblur))
    blur_effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(blur_effect)

    blurred = QImage(pw, ph, QImage.Format.Format_ARGB32_Premultiplied)
    blurred.fill(Qt.GlobalColor.transparent)
    out = QPainter(blurred)
    scene.render(
        out,
        QRectF(0.0, 0.0, float(pw), float(ph)),
        QRectF(0.0, 0.0, float(pw), float(ph)),
    )
    out.end()

    blurred.setDevicePixelRatio(scale)
    _evict_if_needed()
    _MASK_CACHE[key] = blurred
    return blurred


def _tinted_mask(mask: QImage, color: QColor) -> QImage:
    tinted = QImage(mask.size(), QImage.Format.Format_ARGB32_Premultiplied)
    tinted.fill(color)
    painter = QPainter(tinted)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    # Temporarily draw in physical pixels; mask and tinted share the same size.
    dpr = mask.devicePixelRatio()
    plain = mask.copy()
    plain.setDevicePixelRatio(1.0)
    painter.drawImage(0, 0, plain)
    painter.end()
    tinted.setDevicePixelRatio(dpr)
    return tinted


def _draw_blurred_lobe(
    painter: QPainter,
    bounds: QRectF,
    surface: QRectF,
    *,
    radius: float,
    blur: float,
    offset_x: float,
    offset_y: float,
    color: str,
    alpha: int,
    dpr: float,
) -> None:
    mask = _blurred_round_rect_mask(
        bounds.width(), bounds.height(), surface, radius, blur, dpr
    )
    tint = alpha_color(color, alpha)
    shadow = _tinted_mask(mask, tint)
    painter.drawImage(
        QRectF(offset_x, offset_y, bounds.width(), bounds.height()),
        shadow,
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
    blur: float = 8.0,
    hovered: bool = False,
    focused: bool = False,
    disabled: bool = False,
    dpr: float = 1.0,
) -> QRectF:
    """Paint a raised dark-material surface using two true blurred lobes."""

    surface = bounds.adjusted(
        surface_inset,
        surface_inset,
        -surface_inset,
        -surface_inset,
    )

    _draw_blurred_lobe(
        painter,
        bounds,
        surface,
        radius=radius,
        blur=blur,
        offset_x=-light_offset,
        offset_y=-light_offset,
        color=ThemeColors.SHADOW_LIGHT,
        alpha=min(255, light_strength + (18 if hovered else 0)),
        dpr=dpr,
    )
    _draw_blurred_lobe(
        painter,
        bounds,
        surface,
        radius=radius,
        blur=blur,
        offset_x=dark_offset,
        offset_y=dark_offset,
        color=ThemeColors.SHADOW_DARK,
        alpha=min(255, dark_strength + (12 if hovered else 0)),
        dpr=dpr,
    )

    gradient = QLinearGradient(surface.topLeft(), surface.bottomRight())
    if disabled:
        gradient.setColorAt(0.0, QColor(ThemeColors.BG_CARD))
        gradient.setColorAt(1.0, QColor(ThemeColors.SURFACE_LOW))
    elif hovered:
        gradient.setColorAt(0.0, QColor(ThemeColors.SURFACE_HIGH))
        gradient.setColorAt(0.48, QColor(ThemeColors.BG_HOVER))
        gradient.setColorAt(1.0, QColor(ThemeColors.SURFACE_LOW))
    else:
        gradient.setColorAt(0.0, QColor(ThemeColors.SURFACE_HIGH))
        gradient.setColorAt(0.50, QColor(ThemeColors.SURFACE_MID))
        gradient.setColorAt(1.0, QColor(ThemeColors.SURFACE_LOW))
    painter.fillPath(rounded_path(surface, radius), gradient)

    # A subtle directional rim makes the light source legible without turning
    # the control into a hard 1px bevel.
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    rim = QLinearGradient(surface.topLeft(), surface.bottomRight())
    rim.setColorAt(0.0, alpha_color(ThemeColors.SHADOW_LIGHT, 115 if hovered else 88))
    rim.setColorAt(0.42, alpha_color(ThemeColors.BORDER, 35))
    rim.setColorAt(1.0, alpha_color(ThemeColors.SHADOW_DARK, 145))
    pen = painter.pen()
    pen.setBrush(rim)
    pen.setWidthF(1.0)
    painter.setPen(pen)
    painter.drawPath(rounded_path(surface.adjusted(0.5, 0.5, -0.5, -0.5), radius))
    painter.restore()

    if focused and not disabled:
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = painter.pen()
        pen.setColor(QColor(ThemeColors.BORDER_FOCUS))
        pen.setWidthF(1.6)
        painter.setPen(pen)
        painter.drawPath(
            rounded_path(
                surface.adjusted(1.5, 1.5, -1.5, -1.5),
                max(2.0, radius - 1.0),
            )
        )
        painter.restore()

    return surface


def _edge_gradient(
    painter: QPainter,
    rect: QRectF,
    *,
    horizontal: bool,
    reverse: bool,
    color: str,
    alpha: int,
) -> None:
    if horizontal:
        start_x = rect.right() if reverse else rect.left()
        end_x = rect.left() if reverse else rect.right()
        gradient = QLinearGradient(start_x, rect.top(), end_x, rect.top())
    else:
        start_y = rect.bottom() if reverse else rect.top()
        end_y = rect.top() if reverse else rect.bottom()
        gradient = QLinearGradient(rect.left(), start_y, rect.left(), end_y)
    gradient.setColorAt(0.0, alpha_color(color, alpha))
    gradient.setColorAt(0.32, alpha_color(color, int(alpha * 0.58)))
    gradient.setColorAt(1.0, alpha_color(color, 0))
    painter.fillRect(rect, gradient)


def draw_inset_surface(
    painter: QPainter,
    bounds: QRectF,
    *,
    radius: float,
    dark_strength: int,
    light_strength: int,
    depth: float = 10.0,
    focused: bool = False,
    disabled: bool = False,
    fill_base: bool = True,
) -> QRectF:
    """Paint a recessed cavity with broad directional inner shadows."""

    surface = bounds.adjusted(1.0, 1.0, -1.0, -1.0)
    path = rounded_path(surface, radius)

    if fill_base:
        painter.fillPath(
            path,
            QColor(ThemeColors.BG_MAIN if disabled else ThemeColors.BG_INPUT),
        )

    painter.save()
    painter.setClipPath(path)

    # A cavity under upper-left light has darker top/left inner walls and a
    # restrained reflected highlight on bottom/right.
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.top(), surface.width(), depth),
        horizontal=False,
        reverse=False,
        color=ThemeColors.SHADOW_DARK,
        alpha=dark_strength,
    )
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.top(), depth, surface.height()),
        horizontal=True,
        reverse=False,
        color=ThemeColors.SHADOW_DARK,
        alpha=dark_strength,
    )
    _edge_gradient(
        painter,
        QRectF(surface.left(), surface.bottom() - depth, surface.width(), depth),
        horizontal=False,
        reverse=True,
        color=ThemeColors.SHADOW_LIGHT_SOFT,
        alpha=light_strength,
    )
    _edge_gradient(
        painter,
        QRectF(surface.right() - depth, surface.top(), depth, surface.height()),
        horizontal=True,
        reverse=True,
        color=ThemeColors.SHADOW_LIGHT_SOFT,
        alpha=light_strength,
    )
    painter.restore()

    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    pen = painter.pen()
    pen.setColor(alpha_color(ThemeColors.BORDER_DARK, 185))
    pen.setWidthF(1.0)
    painter.setPen(pen)
    painter.drawPath(rounded_path(surface.adjusted(0.5, 0.5, -0.5, -0.5), radius))
    painter.restore()

    if focused and not disabled:
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = painter.pen()
        pen.setColor(QColor(ThemeColors.BORDER_FOCUS))
        pen.setWidthF(1.6)
        painter.setPen(pen)
        painter.drawPath(
            rounded_path(
                surface.adjusted(1.5, 1.5, -1.5, -1.5),
                max(2.0, radius - 1.0),
            )
        )
        painter.restore()

    return surface


__all__ = [
    "draw_inset_surface",
    "draw_raised_surface",
    "rounded_path",
]
