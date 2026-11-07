from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.home import demo


class Command(BaseCommand):
    help = "Demo players on top of synced Modrinth data: saves, reviews, collections, packs."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset", action="store_true", help="Delete the previous demo content first."
        )
        parser.add_argument("--seed", type=int, default=42, help="Random seed.")

    def handle(self, *args, reset: bool, seed: int, **options) -> None:
        if not settings.DEBUG and not reset:
            raise CommandError("Demo content is for development; pass --reset to confirm.")
        if reset:
            self.stdout.write(f"Removed {demo.remove()} demo players")
        elif demo.User.objects.filter(email__endswith=f"@{demo.DEMO_DOMAIN}").exists():
            raise CommandError("Demo content is already there; run with --reset to recreate it.")
        try:
            summary = demo.create(seed=seed)
        except demo.NoSyncedMods as error:
            raise CommandError("No mods yet: run `make sync-mods` first.") from error
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo: {summary.users} players, {summary.collections} collections, "
                f"{summary.reviews} reviews, {summary.packs} packs "
                f"(password for all: {demo.PASSWORD})"
            )
        )
