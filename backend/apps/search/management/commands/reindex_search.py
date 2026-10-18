from django.core.management.base import BaseCommand

from apps.search import services


class Command(BaseCommand):
    help = "Rebuild the Meilisearch index from the database (the same as the daily task)."

    def handle(self, *args, **options) -> None:
        count = services.reindex_all()
        self.stdout.write(self.style.SUCCESS(f"Indexed {count} documents"))
