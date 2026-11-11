from io import BytesIO

import factory
from PIL import Image

from apps.core.models import Source
from apps.skins.models import Skin

# Base-layer areas of the 64×64 layout: head, body, right arm, right leg, left leg, left arm
BASE_AREAS = [
    (0, 0, 32, 16),
    (16, 16, 24, 16),
    (40, 16, 16, 16),
    (0, 16, 16, 16),
    (16, 48, 16, 16),
    (32, 48, 16, 16),
]
# Columns a 3-pixel «slim» arm does not use
SLIM_GAPS = [(54, 20, 2, 12), (50, 16, 2, 4), (46, 52, 2, 12), (42, 48, 2, 4)]


def skin_image(*, color=(190, 40, 40), slim: bool = False) -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    for x, y, width, height in BASE_AREAS:
        image.paste((*color, 255), (x, y, x + width, y + height))
    if slim:
        for x, y, width, height in SLIM_GAPS:
            image.paste((0, 0, 0, 0), (x, y, x + width, y + height))
    return image


def png_bytes(image: Image.Image, image_format: str = "PNG") -> bytes:
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def skin_png(**kwargs) -> bytes:
    return png_bytes(skin_image(**kwargs))


class SkinFactory(factory.django.DjangoModelFactory):
    """A skin from MineSkin's gallery, as the catalog is made of."""

    class Meta:
        model = Skin

    source = Source.MINESKIN
    external_id = factory.Sequence(lambda n: f"{n:032x}")
    external_url = factory.LazyAttribute(lambda s: f"https://mineskin.org/skins/{s.external_id}")
    texture_url = factory.Sequence(lambda n: f"https://textures.minecraft.net/texture/{n:064x}")
    title = factory.Sequence(lambda n: f"Скін {n}")
    texture = factory.django.FileField(filename="skin.png", data=factory.LazyFunction(skin_png))
    model = Skin.Model.CLASSIC
    dominant_color = "#be2828"
    color_bucket = "red"
    texture_hash = factory.Sequence(lambda n: f"{n:064x}")
