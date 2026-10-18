"""Demo content for `make seed`: players, skins, servers, collections, reviews, comments.

Everything goes through the services, so counters, ratings and notifications stay
consistent. A fixed random seed gives the same site every time.
"""

import random
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO

from allauth.account.models import EmailAddress
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone
from PIL import Image

from apps.accounts import privacy
from apps.accounts import services as accounts
from apps.accounts.models import User
from apps.core import publishing
from apps.library import services as library
from apps.mods.models import Project
from apps.servers.models import Server, ServerSnapshot
from apps.servers.services import create_server
from apps.skins import services as skins
from apps.skins.models import Skin
from apps.social import services as social

DEMO_DOMAIN = "demo.blockcraft.test"
PASSWORD = "Creeper-Aww-Man-2026"

NICKNAMES = [
    "Kozak_Craft", "Mavka_Builds", "LvivRedstone", "Dnipro_Miner", "Chereshnia", "Bandura_PvP",
    "Kyiv_Pixel", "Smerichka", "Hutsul_Steve", "Odesa_Waves", "Kharkiv_Tech", "Zirka_Alex",
    "Polissia_Wolf", "Vyshyvanka", "Tavria_Sun", "Karpaty_Peak", "Chumak_Trader", "Sokil_Sky",
    "Kalyna_Red", "Dub_Oak",
]  # fmt: skip
BIOS = [
    "Будую замки й мости на виживанні.",
    "Редстоун — це мистецтво.",
    "Граю з друзями на SMP по вечорах.",
    "Збираю шейдери під слабкий ноутбук.",
    "Малюю скіни для всієї гільдії.",
    "",
]
VERSIONS = ["26.3", "1.21.11", "1.21.1", "1.20.1"]
LOADERS = ["fabric", "neoforge", "forge", "vanilla"]
SKIN_COLORS = [
    ("Козак у червоному", (190, 35, 35)),
    ("Лісова мавка", (45, 140, 60)),
    ("Морський вовк", (35, 75, 190)),
    ("Соняшникова", (230, 190, 40)),
    ("Нічна відьма", (95, 45, 160)),
    ("Пісочний мандрівник", (130, 85, 40)),
    ("Сніговик", (235, 235, 240)),
    ("Бірюзова хвиля", (40, 170, 180)),
    ("Рожева хмарка", (225, 90, 160)),
    ("Тінь", (30, 30, 34)),
]
SKIN_STYLES = [
    ["ukrainian", "medieval"],
    ["fantasy"],
    ["casual"],
    ["cute"],
    ["horror"],
    ["casual", "sport"],
]
SERVERS = [
    ("Козацька Січ", ["survival", "rp"], "java", "uk", "1.20–1.21"),
    ("Карпатське виживання", ["survival", "smp"], "java", "uk", "1.21"),
    ("Редстоун Лабораторія", ["creative"], "java", "uk", "26.3"),
    ("Анархія Дике Поле", ["anarchy", "pvp"], "java", "multi", "1.12–1.21"),
    ("Мініігри Хортиця", ["minigames", "pvp"], "both", "uk", "1.21"),
    ("Скайблок Небо", ["skyblock"], "bedrock", "uk", "1.21"),
    ("Модпак Техно", ["modded", "survival"], "java", "uk", "1.20.1"),
    ("Хардкор Острів", ["hardcore", "survival"], "java", "multi", "1.21"),
]
REVIEWS = [
    (5, "Чудово працює, раджу."),
    (4, "Добре, але є дрібні баги."),
    (5, ""),
    (3, "Нормально, нічого особливого."),
    (4, "Спільнота приємна, адміни відповідають."),
]
COMMENTS = [
    "А з Sodium працює?",
    "Дякую, саме те, що треба!",
    "Під 26.3 вже є?",
    "Підкажіть, як поставити на Bedrock?",
    "Найкращий у своєму роді.",
]
REPLIES = ["Так, перевіряв.", "Ще ні, чекаємо оновлення.", "Дивись вкладку «Як поставити»."]


@dataclass
class Summary:
    users: int = 0
    skins: int = 0
    servers: int = 0
    collections: int = 0
    reviews: int = 0
    comments: int = 0


def _email(nickname: str) -> str:
    return f"{nickname.lower()}@{DEMO_DOMAIN}"


def remove() -> int:
    """Deletes the demo players and everything they made; other counters are recounted."""
    players = list(User.objects.filter(email__endswith=f"@{DEMO_DOMAIN}"))
    for player in players:
        privacy.delete(player)
    return len(players)


def _skin_png(rng: random.Random, color: tuple[int, int, int], slim: bool) -> bytes:
    """A simple 64×64 skin: shirt in the main colour, darker trousers, a face."""
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    skin_tone = rng.choice([(240, 200, 170), (205, 160, 120), (150, 105, 75)])
    trousers = tuple(max(0, c - 70) for c in color)
    for box, fill in (
        ((0, 0, 32, 16), skin_tone),  # head
        ((16, 16, 40, 32), color),  # body
        ((40, 16, 56, 32), color),  # right arm
        ((32, 48, 48, 64), color),  # left arm
        ((0, 16, 16, 32), trousers),  # right leg
        ((16, 48, 32, 64), trousers),  # left leg
    ):
        image.paste((*fill, 255), box)
    hair = rng.choice([(40, 30, 20), (120, 80, 40), (230, 200, 120), (20, 20, 20)])
    image.paste((*hair, 255), (8, 0, 24, 8))  # top of the head
    image.paste((*hair, 255), (8, 8, 16, 10))  # fringe
    image.paste((30, 30, 30, 255), (10, 12, 11, 13))  # eyes
    image.paste((30, 30, 30, 255), (13, 12, 14, 13))
    if slim:
        for x, y, w, h in ((54, 20, 2, 12), (50, 16, 2, 4), (46, 52, 2, 12), (42, 48, 2, 4)):
            image.paste((0, 0, 0, 0), (x, y, x + w, y + h))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _players(rng: random.Random) -> list[User]:
    players = []
    for index, nickname in enumerate(NICKNAMES):
        user = User.objects.create_user(
            email=_email(nickname),
            password=PASSWORD,
            nickname=nickname,
            bio=rng.choice(BIOS),
            role=User.Role.TRUSTED if index < 8 else User.Role.USER,
        )
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        accounts.complete_onboarding(
            user=user,
            data={
                "game_version": rng.choice(VERSIONS),
                "loader": rng.choice(LOADERS),
                "interests": rng.sample(["survival", "building", "tech", "pvp", "rp"], 2),
            },
        )
        players.append(user)
    return players


def _skins(rng: random.Random, players: list[User]) -> list[Skin]:
    made = []
    for index, (title, color) in enumerate(SKIN_COLORS * 2):
        author = players[index % len(players)]
        upload = SimpleUploadedFile(
            "skin.png", _skin_png(rng, color, slim=index % 3 == 0), content_type="image/png"
        )
        skin = skins.upload_skin(
            author=author,
            upload=upload,
            title=title if index < len(SKIN_COLORS) else f"{title} II",
            style_tags=rng.choice(SKIN_STYLES),
        )
        if skin.status != Skin.Status.PUBLISHED:
            publishing.set_status(skin, Skin.Status.PUBLISHED)
        # Back-date publication so «new» and «skin of the week» have something to choose from
        Skin.objects.filter(pk=skin.pk).update(
            published_at=timezone.now() - timedelta(days=rng.randint(0, 20))
        )
        skins.render_preview(skin_id=skin.pk)
        made.append(skin)
    return made


def _servers(rng: random.Random, players: list[User]) -> list[Server]:
    made = []
    now = timezone.now()
    for index, (name, modes, edition, language, versions) in enumerate(SERVERS):
        server = create_server(
            author=players[index],
            data={
                "name": name,
                "host": f"play{index + 1}.{DEMO_DOMAIN}",
                "edition": edition,
                "modes": modes,
                "language": language,
                "versions_label": versions,
                "description": f"{name}: дружня спільнота, щотижневі події й адекватні адміни.",
                "discord_url": "https://discord.gg/blockcraft",
            },
        )
        if server.status != Server.Status.PUBLISHED:
            publishing.set_status(server, Server.Status.PUBLISHED)
        # A day of history for the charts: a gentle evening peak
        peak = rng.randint(20, 160)
        ServerSnapshot.objects.bulk_create(
            ServerSnapshot(
                server=server,
                ts=now - timedelta(minutes=5 * step),
                is_online=step % 97 != 0,
                players_online=max(0, int(peak * (0.5 + 0.5 * ((step % 288) / 288)))),
                players_max=200,
                latency_ms=rng.randint(20, 90),
                version_name=versions,
            )
            for step in range(1, 289)
        )
        made.append(server)
    return made


def _library_and_social(
    rng: random.Random, players: list[User], made_skins: list[Skin], servers: list[Server]
) -> Summary:
    summary = Summary()
    mods = list(Project.objects.published().order_by("-modrinth_downloads")[:40])
    for index, player in enumerate(players):
        # Favorites and likes
        for skin in rng.sample(made_skins, 4):
            if skin.author_id != player.pk:
                library.add_favorite(user=player, kind="skin", identifier=str(skin.pk))
                social.like(user=player, kind="skin", identifier=str(skin.pk))
        for project in rng.sample(mods, min(5, len(mods))):
            library.add_favorite(user=player, kind="mod", identifier=project.slug)
        # Reviews of mods and servers
        for project in rng.sample(mods, min(3, len(mods))):
            stars, text = rng.choice(REVIEWS)
            social.upsert_review(
                user=player, kind="mod", identifier=project.slug, stars=stars, text=text
            )
            summary.reviews += 1
        for server in rng.sample(servers, 2):
            if server.author_id != player.pk:
                stars, text = rng.choice(REVIEWS)
                social.upsert_review(
                    user=player, kind="server", identifier=server.slug, stars=stars, text=text
                )
                summary.reviews += 1
        # A public collection for half of the players
        if index % 2 == 0 and mods:
            collection = library.create_collection(
                owner=player,
                title=rng.choice(
                    ["Мій сетап", "Для слабкого ПК", "Красиві шейдери", "Виживання з друзями"]
                )
                + f" #{index // 2 + 1}",
                description="Те, що ставлю завжди.",
                visibility="public",
            )
            for project in rng.sample(mods, min(5, len(mods))):
                library.add_item(
                    collection=collection, user=player, kind="mod", identifier=project.slug
                )
            library.add_item(
                collection=collection,
                user=player,
                kind="skin",
                identifier=str(rng.choice(made_skins).pk),
            )
            summary.collections += 1
    # Comments with a reply here and there
    targets = [("mod", p.slug) for p in mods[:10]] + [("server", s.slug) for s in servers]
    for kind, identifier in targets:
        author, replier = rng.sample(players, 2)
        comment = social.add_comment(
            user=author, kind=kind, identifier=identifier, body=rng.choice(COMMENTS)
        )
        summary.comments += 1
        if rng.random() < 0.6:
            social.add_comment(
                user=replier,
                kind=kind,
                identifier=identifier,
                body=rng.choice(REPLIES),
                parent_id=comment.pk,
            )
            summary.comments += 1
    return summary


@transaction.atomic
def create(*, seed: int = 42) -> Summary:
    rng = random.Random(seed)
    players = _players(rng)
    made_skins = _skins(rng, players)
    servers = _servers(rng, players)
    summary = _library_and_social(rng, players, made_skins, servers)
    social.recalc_scores()
    social.recalc_trends()
    summary.users, summary.skins, summary.servers = len(players), len(made_skins), len(servers)
    return summary
