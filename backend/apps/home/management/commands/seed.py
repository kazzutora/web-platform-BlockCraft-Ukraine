from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.home import demo
from apps.mods.models import Project


class Command(BaseCommand):
    help = "Demo content: 20 players, skins, servers, collections, reviews and comments."

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
        if not Project.objects.published().exists():
            self.stdout.write(
                self.style.WARNING("No mods yet: run `make sync-mods` for full demo.")
            )
        summary = demo.create(seed=seed)
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo: {summary.users} players, {summary.skins} skins, {summary.servers} servers, "
                f"{summary.collections} collections, {summary.reviews} reviews, "
                f"{summary.comments} comments (password for all: {demo.PASSWORD})"
            )
        )
