from io import BytesIO

import pytest
from PIL import Image

from apps.skins import textures

from .factories import png_bytes, skin_image


def load(data: bytes, size: int | None = None):
    return textures.load(BytesIO(data), size=size)


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"definitely not an image", "skin_invalid"),
        (png_bytes(skin_image().convert("RGB"), "JPEG"), "skin_invalid"),
        (png_bytes(Image.new("RGBA", (32, 32))), "skin_wrong_size"),
        (png_bytes(Image.new("RGBA", (128, 128))), "skin_wrong_size"),
    ],
)
def test_rejects_files_that_are_not_skins(data, code):
    with pytest.raises(textures.SkinTextureError) as error:
        load(data)
    assert error.value.code == code


def test_rejects_files_over_100_kb():
    with pytest.raises(textures.SkinTextureError) as error:
        load(png_bytes(skin_image()), size=100 * 1024 + 1)
    assert error.value.code == "skin_too_large"


def test_legacy_skin_becomes_64x64_with_mirrored_left_limbs():
    legacy = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    # Right leg front: left half red, right half blue
    legacy.paste((255, 0, 0, 255), (4, 20, 6, 32))
    legacy.paste((0, 0, 255, 255), (6, 20, 8, 32))

    image, was_legacy = load(png_bytes(legacy))

    assert was_legacy
    assert image.size == (64, 64)
    # Left leg front (20, 52) is the mirror image
    assert image.getpixel((20, 52)) == (0, 0, 255, 255)
    assert image.getpixel((23, 52)) == (255, 0, 0, 255)


def test_detects_slim_arms():
    assert textures.detect_model(skin_image(slim=True)) == "slim"
    assert textures.detect_model(skin_image()) == "classic"


def test_legacy_skins_are_classic():
    legacy = skin_image(slim=True).crop((0, 0, 64, 32))

    assert textures.analyse(BytesIO(png_bytes(legacy))).model == "classic"


def test_fully_opaque_overlay_is_cleared():
    image = Image.new("RGBA", (64, 64), (20, 120, 40, 255))

    cleared = textures.clear_opaque_overlay(image, legacy=False)

    assert cleared.getpixel((40, 8))[3] == 0  # hat
    assert cleared.getpixel((8, 8)) == (20, 120, 40, 255)  # face stays


@pytest.mark.parametrize(
    ("rgb", "bucket"),
    [
        ((200, 30, 30), "red"),
        ((240, 140, 20), "orange"),
        ((240, 220, 40), "yellow"),
        ((40, 180, 60), "green"),
        ((40, 200, 210), "cyan"),
        ((40, 70, 220), "blue"),
        ((130, 50, 200), "purple"),
        ((230, 80, 170), "pink"),
        ((120, 70, 30), "brown"),
        ((15, 15, 15), "black"),
        ((245, 245, 245), "white"),
        ((128, 128, 128), "gray"),
    ],
)
def test_colour_buckets(rgb, bucket):
    assert textures.bucket_of(*rgb) == bucket


def test_dominant_colour_ignores_transparent_pixels():
    image = skin_image(color=(40, 70, 220))
    # Paint the face orange: still a minority of the visible front
    image.paste((240, 140, 20, 255), (8, 8, 16, 16))

    color, bucket = textures.dominant_color(image, "classic")

    assert bucket == "blue"
    assert color == "#2846dc"


def test_front_preview_is_scaled_without_smoothing():
    image = skin_image(color=(40, 180, 60))
    image.paste((255, 255, 255, 255), (8, 8, 9, 9))  # top-left pixel of the face

    preview = textures.render_front(image, "classic")

    assert preview.size == (128, 256)
    assert preview.getpixel((4 * 8, 0)) == (255, 255, 255, 255)
    assert preview.getpixel((4 * 8 + 8, 0)) == (40, 180, 60, 255)
    assert preview.getpixel((0, 0))[3] == 0  # beside the head


def test_slim_preview_leaves_the_outer_arm_column_empty():
    preview = textures.render_front(skin_image(slim=True), "slim", scale=1)

    assert preview.getpixel((0, 10))[3] == 0
    assert preview.getpixel((1, 10))[3] == 255
