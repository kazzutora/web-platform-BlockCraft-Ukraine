from django.conf import settings
from django.core.management.base import BaseCommand

from apps.packs import services
from apps.sources.clients.loaders import LoaderClient
from apps.sources.clients.modrinth import ModrinthClient
from apps.sources.services import supported_game_versions


class Command(BaseCommand):
    help = "Import popular Modrinth modpacks as official packs and refresh loader versions."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limit", type=int, help="Modpacks to import (default from settings).")

    def handle(self, *args, limit: int | None = None, **options) -> None:
        with LoaderClient() as loaders:
            found = services.store_loader_releases(loaders.latest_many(supported_game_versions()))
        self.stdout.write(f"Loader versions: {found}")
        with ModrinthClient() as client:
            slugs = services.import_popular_modpacks(
                client=client, limit=limit or settings.SYNC_LIMITS["modpack"]
            )
        self.stdout.write(self.style.SUCCESS(f"Official packs: {', '.join(slugs) or 'none'}"))
