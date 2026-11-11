"""Skins: the MineSkin gallery, a player's skin by nickname, «Мій скін»."""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from django.db import transaction

from apps.accounts.models import User, UserSettings
from apps.core import jobs
from apps.core.counters import bump
from apps.core.exceptions import DomainError
from apps.core.models import Source
from apps.sources.clients.base import SourceNotFoundError
from apps.sources.clients.mineskin import MineSkinClient
from apps.sources.clients.mojang import MojangClient, texture_https
from apps.sources.runs import SyncCounter
from apps.sources.schemas.mineskin import Skin as MineSkinSkin

from . import importers, mojang
from .importers import Incoming, NotASkin, Outcome
from .models import Skin

logger = logging.getLogger(__name__)

#: Pages one run may read (64 rows each; ~5 % of the rows are worth importing)
MAX_PAGES = 120
PAGE_SIZE = 64
#: Shown for a skin a player adds from MineSkin without a usable name
UNNAMED = "Скін з MineSkin"


def record_download(*, skin: Skin, user: User | None = None) -> None:
    from apps.library.models import Download
    from apps.library.services import record_took

    bump(skin, "downloads_count")
    record_took(user=user, target=skin, action=Download.Action.DOWNLOAD_PNG)


# «Мій скін»


@transaction.atomic
def set_my_skin(*, user: User, skin: Skin) -> Skin:
    """The skin shown in the player's profile: any skin of the catalog."""
    settings, _ = UserSettings.objects.get_or_create(user=user)
    settings.skin = skin
    settings.save(update_fields=["skin"])
    return skin


def clear_my_skin(*, user: User) -> None:
    UserSettings.objects.filter(user=user).update(skin=None)


# MineSkin gallery (Celery)


def _incoming(data: MineSkinSkin) -> Incoming:
    return Incoming(
        source=Source.MINESKIN,
        external_id=data.uuid,
        external_url=importers.mineskin_url(data.uuid),
        texture_url=texture_https(data.texture.url.skin),
        # The gallery takes named skins only; a player may add an unnamed one
        title=data.name if importers.is_title(data.name) else UNNAMED,
        model=data.variant or "",
        source_views=data.views,
    )


def import_mineskin(
    *, client: MineSkinClient, textures: MojangClient, uuid: str, added_by: User | None = None
) -> tuple[Skin, Outcome]:
    """One gallery skin by its uuid. Raises `NotASkin`, `SourceNotFoundError`."""
    data = client.get_skin(uuid)
    if data.visibility != "public":
        raise NotASkin("not_public")
    png = textures.texture(data.texture.url.skin)
    return importers.import_texture(png, _incoming(data), added_by=added_by)


def sync_mineskin(
    *,
    client: MineSkinClient,
    textures: MojangClient,
    per_run: int,
    run: SyncCounter,
    progress: Callable[[str], None] = logger.info,
) -> None:
    """The newest named skins of the gallery, until `per_run` were added.

    The gallery is a stream (tens of thousands of new skins a day, docs/sources.md): each
    run reads it from the top, so there is no cursor to lose. Rows already here, unnamed,
    technical and partial textures, and pictures we already have are skipped; the last two
    without asking MineSkin, by the texture id the list already gives.
    """
    after, pages = None, 0
    while pages < MAX_PAGES and run.created < per_run:
        page = client.list_skins(after=after, size=PAGE_SIZE)
        pages += 1
        uuids = [summary.uuid for summary in page.skins]
        known = set(
            Skin.objects.filter(source=Source.MINESKIN, external_id__in=uuids).values_list(
                "external_id", flat=True
            )
        )
        urls = {importers.TEXTURE_URL.format(summary.texture) for summary in page.skins}
        pictures = set(
            Skin.objects.filter(texture_url__in=urls).values_list("texture_url", flat=True)
        )
        for summary in page.skins:
            if run.created >= per_run:
                break
            if summary.uuid in known:
                run.unchanged += 1
            elif (
                not importers.is_title(summary.name)
                or importers.TEXTURE_URL.format(summary.texture) in pictures
            ):
                run.skipped += 1
            else:
                _import_row(client=client, textures=textures, uuid=summary.uuid, run=run)
        after = page.next_after
        if after is None:
            break
    progress(f"mineskin: {pages} pages read")


def _import_row(*, client: MineSkinClient, textures: MojangClient, uuid: str, run: SyncCounter):
    with run.item(skin=uuid):
        try:
            _, outcome = import_mineskin(client=client, textures=textures, uuid=uuid)
        except (NotASkin, SourceNotFoundError):
            run.skipped += 1
            return
        if outcome == Outcome.CREATED:
            run.created += 1
        else:
            run.skipped += 1


# A player adds a skin (POST /skins)


@dataclass(frozen=True)
class AddRequest:
    job_id: str | None = None
    skin_id: int | None = None
    title: str = ""


def request_add(*, user: User, nickname: str = "", mineskin: str = "") -> AddRequest:
    """Starts a background import; a skin already here is answered at once."""
    from . import tasks

    if mineskin:
        uuid = importers.mineskin_uuid(mineskin)
        if uuid is None:
            message = "Встав посилання на скін MineSkin або його UUID."
            raise DomainError(code="invalid", message=message, fields={"mineskin": [message]})
        known = Skin.objects.filter(source=Source.MINESKIN, external_id=uuid).first()
        if known is not None and known.is_hidden:
            raise DomainError(code="hidden_skin", message="Цей скін приховав модератор.")
        if known is not None:
            return AddRequest(skin_id=known.pk, title=known.title)
        kind, value = "mineskin", uuid
    else:
        kind, value = "nickname", nickname
    job = jobs.create("skins.add")
    transaction.on_commit(
        lambda: tasks.import_skin.delay(job_id=job["id"], kind=kind, value=value, user_id=user.pk)
    )
    return AddRequest(job_id=job["id"])


def add_by_nickname(*, nickname: str, user: User | None) -> tuple[Skin, Outcome]:
    """The skin a Java player wears now (Mojang, cached). Raises DomainError."""
    try:
        player = mojang.lookup(nickname)
    except mojang.MojangError as error:
        raise DomainError(code="source_unavailable", message="Mojang не відповідає.") from error
    if player is None:
        raise DomainError(code="player_not_found", message="Гравця з таким ніком не знайдено.")
    if player.texture_png is None or not player.texture_url:
        raise DomainError(code="default_skin", message="У гравця стандартний скін.")
    incoming = importers.mojang_incoming(
        nickname=player.nickname, model=player.model, texture_url=player.texture_url
    )
    try:
        return importers.import_texture(player.texture_png, incoming, added_by=user)
    except NotASkin as error:
        # The code says why: a partial texture or a name the lexicon filter stops
        raise DomainError(code=str(error), message="Цей скін не можна додати.") from error
