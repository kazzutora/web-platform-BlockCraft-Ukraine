"""Skins from MineSkin and Mojang → `Skin` (tech.md 6.6, 8.3, 8.4).

One texture, one skin: the SHA-256 of the pixels decides, the first source wins.
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.core.models import Source
from apps.moderation.words import find_banned

from . import textures
from .models import Skin

#: Names the gallery is full of that are not names: «archmc-d5ecda4», uuids, and the parts
#: plugins upload one by one («Kes_ARM_LEFT_2», «Mangogoy_BODY_1», «…_BASE»)
TECHNICAL_NAME = re.compile(
    r"^[a-z0-9]+-[0-9a-f]{6,}$"
    r"|^[0-9a-f-]{8,}$"
    r"|_(ARM|LEG)_(LEFT|RIGHT)(_\d+)?$"
    r"|_(BODY|HEAD|BASE|HAT)(_\d+)?$"
    r"|\.png$"
    r"|^archmc-",
    re.IGNORECASE,
)
#: Where textures live; MineSkin lists give the id only
TEXTURE_URL = "https://textures.minecraft.net/texture/{}"
MINESKIN_UUID = re.compile(
    r"([0-9a-f]{8})-?([0-9a-f]{4})-?([0-9a-f]{4})-?([0-9a-f]{4})-?([0-9a-f]{12})", re.IGNORECASE
)


class Outcome(StrEnum):
    CREATED = "created"
    #: Already here from this source
    UNCHANGED = "unchanged"
    #: The same picture came from elsewhere first
    DUPLICATE = "duplicate"


class NotASkin(ValueError):
    """The texture is not something a player can wear (or not a skin at all)."""


@dataclass(frozen=True)
class Incoming:
    source: str
    external_id: str
    external_url: str
    texture_url: str
    title: str
    model: str = ""
    player_name: str = ""
    source_views: int = 0


def mineskin_url(uuid: str) -> str:
    return f"https://mineskin.org/skins/{uuid}"


def mineskin_uuid(value: str) -> str | None:
    """A MineSkin uuid from a link or the uuid itself (dashes optional), as the API spells it."""
    match = MINESKIN_UUID.search(value.strip())
    return "".join(match.groups()).lower() if match else None


def texture_id(texture_url: str) -> str:
    """textures.minecraft.net/texture/<id> → <id>: Mojang skins are keyed by it."""
    return texture_url.rstrip("/").rsplit("/", 1)[-1][:64]


def is_title(name: str | None) -> bool:
    """A name worth showing in the catalog (8.3: unnamed gallery skins are skipped), and
    one the lexicon filter lets through, as for everything players see here."""
    name = (name or "").strip()
    return len(name) >= 2 and not TECHNICAL_NAME.search(name) and find_banned(name) is None


def import_texture(png: bytes, incoming: Incoming, *, added_by: User | None = None):
    """Creates the skin from its PNG; (skin, outcome). Raises `NotASkin`."""
    known = Skin.objects.filter(source=incoming.source, external_id=incoming.external_id).first()
    if known is not None:
        return known, Outcome.UNCHANGED
    if find_banned(incoming.title):
        raise NotASkin("bad_name")
    try:
        analysis = textures.analyse(BytesIO(png), size=len(png), model=incoming.model)
    except textures.SkinTextureError as error:
        raise NotASkin(error.code) from error
    if not textures.is_wearable(analysis.image):
        raise NotASkin("not_wearable")
    same = Skin.objects.filter(texture_hash=analysis.texture_hash).first()
    if same is not None:
        return same, Outcome.DUPLICATE
    skin = Skin(
        source=incoming.source,
        external_id=incoming.external_id,
        external_url=incoming.external_url,
        texture_url=incoming.texture_url,
        title=incoming.title.strip()[:80],
        texture_hash=analysis.texture_hash,
        model=analysis.model,
        dominant_color=analysis.dominant_color,
        color_bucket=analysis.color_bucket,
        player_name=incoming.player_name[:16],
        source_views=max(incoming.source_views, 0),
        added_by=added_by,
    )
    skin.texture.save("skin.png", ContentFile(textures.to_png(analysis.image)), save=False)
    preview = textures.render_front(analysis.image, analysis.model)
    skin.preview.save("preview.png", ContentFile(textures.to_png(preview)), save=False)
    try:
        with transaction.atomic():
            skin.save()
    except IntegrityError:
        # The same picture or the same source id arrived in parallel
        skin.texture.delete(save=False)
        skin.preview.delete(save=False)
        same = Skin.objects.filter(texture_hash=analysis.texture_hash).first() or (
            Skin.objects.get(source=incoming.source, external_id=incoming.external_id)
        )
        return same, Outcome.DUPLICATE
    return skin, Outcome.CREATED


def mojang_incoming(*, nickname: str, model: str | None, texture_url: str) -> Incoming:
    return Incoming(
        source=Source.MOJANG,
        external_id=texture_id(texture_url),
        external_url=texture_url,
        texture_url=texture_url,
        title=nickname,
        model=model or "",
        player_name=nickname,
    )
