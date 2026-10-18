"""Skin texture checks and analysis: format, legacy conversion, arm model, colour, 2D preview.

Coordinates follow the Minecraft 64×64 skin layout (boxes are x, y, width, height).
"""

import colorsys
import hashlib
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from .styles import ColorBucket

MAX_BYTES = 100 * 1024
SIZE = 64
PREVIEW_SCALE = 8

Box = tuple[int, int, int, int]

# Last two columns of the right arm's back: unused (transparent) on 3-pixel «slim» arms
SLIM_ARM_PROBE: Box = (54, 20, 2, 12)

# Overlay layers of a 64×64 skin; legacy skins have only the hat
OVERLAY_BOXES: list[Box] = [(32, 0, 32, 16), (0, 32, 64, 16), (0, 48, 16, 16), (48, 48, 16, 16)]
LEGACY_OVERLAY_BOXES: list[Box] = [(32, 0, 32, 16)]

# Legacy 64×32 skins have one arm and one leg: the left ones are mirrored copies
_LEGACY_LIMB_COPIES: list[tuple[Box, tuple[int, int]]] = [
    ((4, 16, 4, 4), (20, 48)),  # leg top
    ((8, 16, 4, 4), (24, 48)),  # leg bottom
    ((0, 20, 4, 12), (24, 52)),  # leg outer side
    ((4, 20, 4, 12), (20, 52)),  # leg front
    ((8, 20, 4, 12), (16, 52)),  # leg inner side
    ((12, 20, 4, 12), (28, 52)),  # leg back
    ((44, 16, 4, 4), (36, 48)),  # arm top
    ((48, 16, 4, 4), (40, 48)),  # arm bottom
    ((40, 20, 4, 12), (40, 52)),  # arm outer side
    ((44, 20, 4, 12), (36, 52)),  # arm front
    ((48, 20, 4, 12), (32, 52)),  # arm inner side
    ((52, 20, 4, 12), (44, 52)),  # arm back
]


class SkinTextureError(ValueError):
    """The file is not a usable skin; `message` is shown to the player."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Analysis:
    image: Image.Image
    model: str
    dominant_color: str
    color_bucket: str
    texture_hash: str


def _crop(image: Image.Image, box: Box) -> Image.Image:
    x, y, width, height = box
    return image.crop((x, y, x + width, y + height))


def _is_transparent(image: Image.Image, box: Box) -> bool:
    alpha = _crop(image, box).getchannel("A")
    return alpha.getextrema()[1] == 0


def load(upload: BinaryIO, *, size: int | None = None) -> tuple[Image.Image, bool]:
    """A checked RGBA 64×64 texture and whether it came in the legacy 64×32 layout."""
    if size is not None and size > MAX_BYTES:
        raise SkinTextureError("skin_too_large", "Скін має бути до 100 КБ.")
    try:
        image = Image.open(upload)
        image_format = image.format
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        raise SkinTextureError("skin_invalid", "Це не схоже на PNG-файл скіна.") from error
    if image_format != "PNG":
        raise SkinTextureError("skin_invalid", "Скін має бути у форматі PNG.")
    if image.size not in ((SIZE, SIZE), (SIZE, SIZE // 2)):
        raise SkinTextureError(
            "skin_wrong_size",
            f"Розмір скіна — 64×64 або 64×32 пікселі, а не {image.width}×{image.height}.",
        )
    image = image.convert("RGBA")
    legacy = image.height == SIZE // 2
    return (to_modern(image) if legacy else image), legacy


def to_modern(legacy: Image.Image) -> Image.Image:
    """64×32 → 64×64: the left arm and leg become mirrored copies of the right ones."""
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    image.paste(legacy, (0, 0))
    for box, target in _LEGACY_LIMB_COPIES:
        image.paste(ImageOps.mirror(_crop(legacy, box)), target)
    return image


def clear_opaque_overlay(image: Image.Image, *, legacy: bool) -> Image.Image:
    """Old editors filled the overlay with solid colour; fully opaque, it hides the skin."""
    drawn = _crop(image, (0, 0, SIZE, SIZE // 2)) if legacy else image
    if drawn.getchannel("A").getextrema()[0] < 255:
        return image
    image = image.copy()
    for x, y, width, height in LEGACY_OVERLAY_BOXES if legacy else OVERLAY_BOXES:
        image.paste((0, 0, 0, 0), (x, y, x + width, y + height))
    return image


def detect_model(image: Image.Image) -> str:
    """«slim» when the arm is 3 pixels wide (its fourth column is transparent)."""
    return "slim" if _is_transparent(image, SLIM_ARM_PROBE) else "classic"


def _front_parts(model: str) -> list[tuple[Box, Box, tuple[int, int]]]:
    """(base face, overlay face, position on a 16×32 canvas) for each body part."""
    arm = 3 if model == "slim" else 4
    return [
        ((8, 8, 8, 8), (40, 8, 8, 8), (4, 0)),  # head, hat
        ((20, 20, 8, 12), (20, 36, 8, 12), (4, 8)),  # body, jacket
        ((44, 20, arm, 12), (44, 36, arm, 12), (4 - arm, 8)),  # right arm
        ((36, 52, arm, 12), (52, 52, arm, 12), (12, 8)),  # left arm
        ((4, 20, 4, 12), (4, 36, 4, 12), (4, 20)),  # right leg
        ((20, 52, 4, 12), (4, 52, 4, 12), (8, 20)),  # left leg
    ]


def render_front(image: Image.Image, model: str, *, scale: int = PREVIEW_SCALE) -> Image.Image:
    """The player seen from the front with both layers, scaled with nearest-neighbour."""
    canvas = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    for base, overlay, position in _front_parts(model):
        canvas.alpha_composite(_crop(image, base), position)
        canvas.alpha_composite(_crop(image, overlay), position)
    return canvas.resize((16 * scale, 32 * scale), Image.Resampling.NEAREST)


def bucket_of(red: int, green: int, blue: int) -> str:
    hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    degrees = hue * 360
    if value < 0.18:
        return ColorBucket.BLACK
    if saturation < 0.18:
        if value > 0.85:
            return ColorBucket.WHITE
        return ColorBucket.GRAY if value > 0.3 else ColorBucket.BLACK
    if 15 <= degrees < 50 and value < 0.65:
        return ColorBucket.BROWN
    for limit, bucket in (
        (15, ColorBucket.RED),
        (40, ColorBucket.ORANGE),
        (70, ColorBucket.YELLOW),
        (165, ColorBucket.GREEN),
        (200, ColorBucket.CYAN),
        (255, ColorBucket.BLUE),
        (290, ColorBucket.PURPLE),
        (345, ColorBucket.PINK),
    ):
        if degrees < limit:
            return bucket
    return ColorBucket.RED


def dominant_color(image: Image.Image, model: str) -> tuple[str, str]:
    """Hex of the most common colour family on the visible front, ignoring transparent pixels."""
    front = render_front(image, model, scale=1)
    pixels = [(r, g, b) for r, g, b, a in front.get_flattened_data() if a >= 128]
    if not pixels:
        return "#808080", ColorBucket.GRAY
    buckets = [bucket_of(*pixel) for pixel in pixels]
    winner = Counter(buckets).most_common(1)[0][0]
    members = [pixel for pixel, bucket in zip(pixels, buckets, strict=True) if bucket == winner]
    channels = zip(*members, strict=True)
    red, green, blue = (round(sum(channel) / len(members)) for channel in channels)
    return f"#{red:02x}{green:02x}{blue:02x}", winner


def to_png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def analyse(upload: BinaryIO, *, size: int | None = None, model: str = "") -> Analysis:
    """Everything the upload form needs; `model` overrides the detected one."""
    image, legacy = load(upload, size=size)
    image = clear_opaque_overlay(image, legacy=legacy)
    model = model or ("classic" if legacy else detect_model(image))
    color, bucket = dominant_color(image, model)
    return Analysis(
        image=image,
        model=model,
        dominant_color=color,
        color_bucket=bucket,
        texture_hash=hashlib.sha256(image.tobytes()).hexdigest(),
    )
