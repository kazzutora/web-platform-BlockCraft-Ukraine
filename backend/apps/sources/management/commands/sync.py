from django.core.management.base import BaseCommand, CommandError

from apps.sources import registry


class Command(BaseCommand):
    help = "Run synchronization jobs of all sources or of one (make sync / make sync s=modrinth)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--source", help="Registry key, e.g. modrinth.")
        parser.add_argument("--job", help="One job of the source, e.g. catalog.")
        parser.add_argument(
            "--limit", type=int, help="Items per type instead of the configured limits."
        )

    def handle(
        self, *args, source: str | None, job: str | None, limit: int | None, **options
    ) -> None:
        if job and not source:
            raise CommandError("--job needs --source.")
        try:
            sources = [registry.get(source)] if source else list(registry.SOURCES)
            selected = [
                (info, item)
                for info in sources
                for item in ((info.job(job),) if job else info.jobs)
            ]
        except KeyError as error:
            known = ", ".join(info.key for info in registry.SOURCES)
            raise CommandError(f"Unknown source or job {error}; sources: {known}.") from error

        if not selected:
            self.stdout.write(f"{source}: no sync jobs yet.")
            return
        for info, item in selected:
            self.stdout.write(f"{info.key}.{item.key}: {item.title}")
            kwargs = {"limit": limit} if limit and item.accepts_limit else {}
            result = item.load()(**kwargs)
            self.stdout.write(self.style.SUCCESS(f"{info.key}.{item.key}: {result}"))
