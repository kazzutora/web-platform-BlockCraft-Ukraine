from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.game import GAME_VERSIONS
from apps.mods.clients import ModrinthClient
from apps.packs import services
from apps.packs.clients import LoaderClient


class Command(BaseCommand):
    help = "Import popular Modrinth modpacks as official packs and refresh loader versions."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limit", type=int, help="Modpacks to import (default from settings).")

    def handle(self, *args, limit: int | None = None, **options) -> None:
        with LoaderClient() as loaders:
            found = services.store_loader_releases(loaders.latest_many(GAME_VERSIONS))
        self.stdout.write(f"Loader versions: {found}")
        with ModrinthClient() as client:
            slugs = services.import_popular_modpacks(
                client=client, limit=limit or settings.MODRINTH_OFFICIAL_PACKS
            )
        self.stdout.write(self.style.SUCCESS(f"Official packs: {', '.join(slugs) or 'none'}"))
