from datetime import UTC, datetime

import factory

from apps.accounts.tests.factories import UserFactory
from apps.mods.models import Project
from apps.mods.tests.factories import ProjectFactory, VersionFactory
from apps.packs.models import Pack, PackItem


class PackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pack

    author = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Збірка {n}")
    slug = factory.Sequence(lambda n: f"pack-{n}")
    summary = "Затишне виживання"
    game_version = "26.3"
    loader = "fabric"
    loader_version = "0.17.2"
    status = Pack.Status.PUBLISHED
    published_at = factory.LazyFunction(lambda: datetime(2026, 1, 1, tzinfo=UTC))


def mod(
    *,
    requires: list[Project] = (),
    breaks: list[Project] = (),
    optional: list[Project] = (),
    unknown: list[str] = (),
    game_versions: list[str] | None = None,
    loaders: list[str] | None = None,
    **fields,
) -> Project:
    """A catalog project with one file whose dependencies point at the given projects."""
    project = ProjectFactory(**fields)
    dependencies = (
        [{"project_id": p.external_id, "dependency_type": "required"} for p in requires]
        + [{"project_id": p.external_id, "dependency_type": "incompatible"} for p in breaks]
        + [{"project_id": p.external_id, "dependency_type": "optional"} for p in optional]
        + [{"project_id": modrinth_id, "dependency_type": "required"} for modrinth_id in unknown]
    )
    VersionFactory(
        project=project,
        game_versions=game_versions or ["26.3"],
        loaders=loaders or ["fabric"],
        dependencies=dependencies,
        sha1="1" * 40,
        sha512="5" * 128,
    )
    return project


def add(pack: Pack, project: Project, **fields) -> PackItem:
    """An item as it is stored, without resolving the set (services.add_item does that)."""
    item = PackItem.objects.create(
        pack=pack,
        project=project,
        version=project.versions.order_by("-date_published").first(),
        position=pack.items.count() + 1,
        **fields,
    )
    Pack.objects.filter(pk=pack.pk).update(items_count=pack.items.count())
    pack.items_count = pack.items.count()
    return item
