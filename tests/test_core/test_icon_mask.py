"""Deterministic coverage for raster favicon mask normalization."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

from core.icon_mask import normalize_raster_icon


def _png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _normalized_image(image: Image.Image) -> Image.Image:
    data = normalize_raster_icon(_png_bytes(image))
    assert data is not None
    with Image.open(BytesIO(data)) as normalized:
        return normalized.convert("RGBA")


def test_opaque_background_is_removed_and_symbol_becomes_alpha_mask() -> None:
    source = Image.new("RGBA", (32, 32), (245, 245, 245, 255))
    draw = ImageDraw.Draw(source)
    draw.ellipse((8, 8, 23, 23), fill=(20, 20, 20, 255))

    normalized = _normalized_image(source)
    alpha = normalized.getchannel("A")

    assert normalized.size == (64, 64)
    assert alpha.getpixel((0, 0)) < 16
    assert alpha.getpixel((32, 32)) > 220
    assert normalized.getpixel((32, 32))[:3] == (255, 255, 255)


def test_transparent_single_colour_symbol_keeps_its_silhouette() -> None:
    source = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(source)
    draw.polygon([(16, 3), (28, 27), (4, 27)], fill=(40, 120, 220, 255))

    normalized = _normalized_image(source)
    alpha = normalized.getchannel("A")

    assert alpha.getpixel((32, 20)) > 180
    assert alpha.getpixel((0, 0)) < 16


def test_transparent_badge_prefers_internal_glyph_over_coloured_fill() -> None:
    source = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(source)
    draw.ellipse((2, 2, 29, 29), fill=(230, 80, 20, 255))
    draw.rectangle((13, 7, 18, 24), fill=(255, 255, 255, 255))
    draw.rectangle((8, 13, 23, 18), fill=(255, 255, 255, 255))

    normalized = _normalized_image(source)
    alpha = normalized.getchannel("A")
    visible = sum(alpha.histogram()[28:])

    # The orange circular badge itself is removed; the contrasting plus remains.
    assert visible / (64 * 64) < 0.70
    assert alpha.getpixel((32, 32)) > 180
    assert alpha.getpixel((8, 8)) < 80


def test_solid_square_without_distinguishable_symbol_is_rejected() -> None:
    source = Image.new("RGBA", (32, 32), (30, 100, 180, 255))
    assert normalize_raster_icon(_png_bytes(source)) is None
