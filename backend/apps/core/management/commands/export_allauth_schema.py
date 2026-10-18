import json

from allauth.headless.spec.internal.schema import get_schema
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Print the OpenAPI schema of allauth headless (source of frontend auth types)."

    def handle(self, *args, **options) -> None:
        # Internal allauth API: the same function serves /_allauth/openapi.json
        self.stdout.write(json.dumps(get_schema(), indent=2, sort_keys=True, ensure_ascii=False))
