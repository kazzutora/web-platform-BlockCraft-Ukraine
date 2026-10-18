from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.game import GAME_VERSIONS
from apps.mods import services
from apps.mods.clients import ModrinthClient


class Command(BaseCommand):
    help = "Sync popular mods, resource packs and shaders from Modrinth (make sync-mods)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            help="Projects per type instead of the configured limits (quick local runs).",
        )

    def handle(self, *args, limit: int | None = None, **options) -> None:
        limits = (
            dict.fromkeys(settings.MODRINTH_SYNC_LIMITS, limit)
            if limit
            else settings.MODRINTH_SYNC_LIMITS
        )
        with ModrinthClient() as client:
            result = services.sync_popular(
                client=client,
                limits=limits,
                game_versions=list(GAME_VERSIONS),
                progress=lambda message: self.stdout.write(message),
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Categories: {result.categories}, projects: {result.projects}, "
                f"versions: {result.versions}"
            )
        )
