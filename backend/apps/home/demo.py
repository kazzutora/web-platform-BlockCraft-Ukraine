"""Demo players for `make seed` on top of synced Modrinth data: saves, reviews, collections, packs.

No made-up content: every mod, pack item and review target is a real synced project.
Everything goes through the services, so counters, ratings and notifications stay
consistent. A fixed random seed gives the same site every time.
"""

import random
from dataclasses import dataclass

from allauth.account.models import EmailAddress
from django.db import transaction
from django.utils import timezone

from apps.accounts import privacy
from apps.accounts import services as accounts
from apps.accounts.models import User
from apps.library import services as library
from apps.mods.models import Project
from apps.packs import services as packs
from apps.packs.models import Pack
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
REVIEWS = [
    (5, "Чудово працює, раджу."),
    (4, "Добре, але є дрібні баги."),
    (5, ""),
    (3, "Нормально, нічого особливого."),
    (4, "Спільнота приємна, адміни відповідають."),
]


@dataclass
class Summary:
    users: int = 0
    collections: int = 0
    reviews: int = 0
    packs: int = 0


def _email(nickname: str) -> str:
    return f"{nickname.lower()}@{DEMO_DOMAIN}"


def remove() -> int:
    """Deletes the demo players and everything they made; other counters are recounted."""
    players = list(User.objects.filter(email__endswith=f"@{DEMO_DOMAIN}"))
    for player in players:
        privacy.delete(player)
    return len(players)


def _players(rng: random.Random) -> list[User]:
    players = []
    for nickname in NICKNAMES:
        user = User.objects.create_user(
            email=_email(nickname),
            password=PASSWORD,
            nickname=nickname,
            bio=rng.choice(BIOS),
        )
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        accounts.complete_onboarding(
            user=user,
            data={
                "game_version": rng.choice(VERSIONS),
                "loader": rng.choice(LOADERS),
            },
        )
        players.append(user)
    return players


def _library_and_social(rng: random.Random, players: list[User]) -> Summary:
    summary = Summary()
    mods = list(Project.objects.published().order_by("-modrinth_downloads")[:40])
    for index, player in enumerate(players):
        # Favorites
        for project in rng.sample(mods, min(5, len(mods))):
            library.add_favorite(user=player, kind="mod", identifier=project.slug)
        # Reviews of mods
        for project in rng.sample(mods, min(3, len(mods))):
            stars, text = rng.choice(REVIEWS)
            social.upsert_review(
                user=player, kind="mod", identifier=project.slug, stars=stars, text=text
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
            summary.collections += 1
    return summary


PACKS = [
    ("Для слабкого ПК", "Більше кадрів на старому ноутбуці.", ["performance", "lightweight"]),
    ("Ванілла з друзями", "Та сама гра, тільки зручніша.", ["vanilla-plus", "multiplayer"]),
    ("Техно-виживання", "Механізми, конвеєри й автоматизація.", ["tech", "survival"]),
    ("Пригоди й підземелля", "Нові структури, боси й лут.", ["adventure"]),
]
PACK_TARGETS = [
    ("1.21.1", "fabric"),
    ("26.3", "fabric"),
    ("1.21.1", "neoforge"),
    ("1.20.1", "forge"),
]
INSTALL = (
    "1. Завантаж `.mrpack`.\n"
    "2. Відкрий Modrinth App або Prism Launcher → «Додати» → «Імпорт».\n"
    "3. Грай!"
)


def _packs(rng: random.Random, players: list[User]) -> list[Pack]:
    """Packs of real catalog files; none when Modrinth was never synced (no files to pick)."""
    made = []
    for (title, summary, styles), author in zip(
        PACKS, rng.sample(players, len(PACKS)), strict=False
    ):
        for game_version, loader in PACK_TARGETS:
            fitting = list(
                Project.objects.published()
                .filter(
                    project_type="mod",
                    versions__game_versions__contains=[game_version],
                    versions__loaders__contains=[loader],
                )
                .distinct()
                .order_by("-modrinth_downloads")[:30]
            )
            if len(fitting) >= 4:
                break
        else:
            return made
        pack = packs.create_pack(
            author=author,
            data={
                "title": title,
                "summary": summary,
                "style_tags": styles,
                "game_version": game_version,
                "loader": loader,
                "install_md": INSTALL,
                "ram_min_gb": rng.choice([4, 6, 8]),
            },
        )
        for project in rng.sample(fitting, min(len(fitting), rng.randint(4, 8))):
            if not pack.items.filter(project=project).exists():
                packs.add_item(pack=pack, user=author, project_slug=project.slug)
        pack.status = Pack.Status.PUBLISHED
        pack.published_at = timezone.now()
        pack.save(update_fields=["status", "published_at", "updated_at"])
        for reviewer in rng.sample([p for p in players if p != author], 2):
            stars, text = rng.choice(REVIEWS)
            social.upsert_review(
                user=reviewer, kind="pack", identifier=pack.slug, stars=stars, text=text
            )
        made.append(pack)
    return made


class NoSyncedMods(Exception):
    """The demo is built on real projects: sync Modrinth first."""


@transaction.atomic
def create(*, seed: int = 42) -> Summary:
    if not Project.objects.published().exists():
        raise NoSyncedMods
    rng = random.Random(seed)
    players = _players(rng)
    summary = _library_and_social(rng, players)
    summary.packs = len(_packs(rng, players))
    social.recalc_scores()
    social.recalc_trends()
    summary.users = len(players)
    return summary
