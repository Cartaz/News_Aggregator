"""Normalize raster favicons into compact monochrome alpha masks.

The favicon cache keeps SVG assets untouched, while opaque or multicolour raster
icons are converted into a white RGBA mask. QML can then apply the application
accent without retaining coloured square backgrounds.
"""

from __future__ import annotations

from collections import Counter
from io import BytesIO
from statistics import median

from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError

_MAX_INPUT_DIMENSION = 512
_OUTPUT_SIZE = 64
_ALPHA_VISIBLE = 28
_BACKGROUND_DISTANCE_LOW = 18
_BACKGROUND_DISTANCE_HIGH = 78
_MIN_MASK_COVERAGE = 0.012
_MAX_MASK_COVERAGE = 0.94


def _quantized_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Reduce insignificant colour noise while preserving favicon structure."""
    return tuple((channel // 16) * 16 for channel in rgb)  # type: ignore[return-value]


def _border_samples(image: Image.Image) -> list[tuple[int, int, int, int]]:
    width, height = image.size
    if width <= 0 or height <= 0:
        return []
    pixels = image.load()
    step_x = max(1, width // 12)
    step_y = max(1, height // 12)
    points: set[tuple[int, int]] = set()
    for x in range(0, width, step_x):
        points.add((x, 0))
        points.add((x, height - 1))
    for y in range(0, height, step_y):
        points.add((0, y))
        points.add((width - 1, y))
    points.update(
        {
            (0, 0),
            (width - 1, 0),
            (0, height - 1),
            (width - 1, height - 1),
        }
    )
    return [pixels[x, y] for x, y in points]


def _dominant_visible_color(image: Image.Image) -> tuple[tuple[int, int, int], float] | None:
    visible: list[tuple[int, int, int]] = []
    for red, green, blue, alpha in image.getdata():
        if alpha >= 192:
            visible.append(_quantized_color((red, green, blue)))
    if not visible:
        return None
    color, count = Counter(visible).most_common(1)[0]
    return color, count / len(visible)


def _background_color(image: Image.Image) -> tuple[tuple[int, int, int] | None, bool]:
    """Estimate whether the favicon has an opaque background and its colour."""
    border = _border_samples(image)
    if not border:
        return None, False
    opaque = [pixel for pixel in border if pixel[3] >= 192]
    border_opaque_ratio = len(opaque) / len(border)
    if border_opaque_ratio >= 0.65:
        return (
            (
                int(median(pixel[0] for pixel in opaque)),
                int(median(pixel[1] for pixel in opaque)),
                int(median(pixel[2] for pixel in opaque)),
            ),
            True,
        )

    dominant = _dominant_visible_color(image)
    if dominant is None:
        return None, False
    color, share = dominant
    # A dominant fill on an otherwise transparent favicon is commonly a badge
    # background. Only treat it as removable when enough secondary detail exists.
    return (color if 0.52 <= share <= 0.90 else None), False


def _distance_mask(image: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    rgb = image.convert("RGB")
    reference = Image.new("RGB", image.size, background)
    difference = ImageChops.difference(rgb, reference)
    red, green, blue = difference.split()
    distance = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    distance = ImageOps.autocontrast(distance, cutoff=1)

    span = _BACKGROUND_DISTANCE_HIGH - _BACKGROUND_DISTANCE_LOW
    mask = distance.point(
        lambda value: 0
        if value <= _BACKGROUND_DISTANCE_LOW
        else 255
        if value >= _BACKGROUND_DISTANCE_HIGH
        else int((value - _BACKGROUND_DISTANCE_LOW) * 255 / span)
    )
    return ImageChops.multiply(mask, image.getchannel("A"))


def _binary_coverage(mask: Image.Image) -> float:
    histogram = mask.histogram()
    visible = sum(histogram[_ALPHA_VISIBLE:])
    return visible / max(1, mask.width * mask.height)


def _square_mask(mask: Image.Image) -> Image.Image | None:
    visible = mask.point(lambda value: 255 if value >= _ALPHA_VISIBLE else 0)
    bbox = visible.getbbox()
    if bbox is None:
        return None

    coverage = _binary_coverage(mask)
    if coverage < _MIN_MASK_COVERAGE or coverage > _MAX_MASK_COVERAGE:
        return None

    cropped = mask.crop(bbox)
    side = max(cropped.size)
    padding = max(1, round(side * 0.10))
    canvas_side = side + padding * 2
    canvas = Image.new("L", (canvas_side, canvas_side), 0)
    x = (canvas_side - cropped.width) // 2
    y = (canvas_side - cropped.height) // 2
    canvas.paste(cropped, (x, y))
    return canvas.resize((_OUTPUT_SIZE, _OUTPUT_SIZE), Image.Resampling.LANCZOS)


def normalize_raster_icon(data: bytes) -> bytes | None:
    """Return a white PNG alpha mask, or ``None`` for an unusable raster icon.

    Opaque backgrounds are removed by colour distance. Transparent single-colour
    symbols retain their alpha silhouette. Multicolour badges with a dominant fill
    use that fill as removable background so the internal glyph remains visible.
    """
    try:
        with Image.open(BytesIO(data)) as source:
            source.seek(0)
            rgba = source.convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError):
        return None

    if rgba.width <= 0 or rgba.height <= 0:
        return None
    if rgba.width > _MAX_INPUT_DIMENSION or rgba.height > _MAX_INPUT_DIMENSION:
        rgba.thumbnail(
            (_MAX_INPUT_DIMENSION, _MAX_INPUT_DIMENSION),
            Image.Resampling.LANCZOS,
        )

    background, opaque_border = _background_color(rgba)
    alpha = rgba.getchannel("A")
    if background is None:
        mask = alpha
    else:
        candidate = _distance_mask(rgba, background)
        candidate_coverage = _binary_coverage(candidate)
        # For opaque images the border colour is a strong background signal. For
        # transparent badges, only replace the alpha silhouette when the contrast
        # mask contains meaningful but not near-solid internal detail.
        if opaque_border or 0.025 <= candidate_coverage <= 0.72:
            mask = candidate
        else:
            mask = alpha

    normalized_mask = _square_mask(mask)
    if normalized_mask is None:
        return None

    output = Image.new("RGBA", normalized_mask.size, (255, 255, 255, 0))
    output.putalpha(normalized_mask)
    buffer = BytesIO()
    output.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


__all__ = ["normalize_raster_icon"]
