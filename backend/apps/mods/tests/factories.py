from datetime import UTC, datetime, timedelta

import factory

from apps.mods.models import Category, Project, ProjectType, ProjectVersion


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("project_type", "slug")

    slug = factory.Sequence(lambda n: f"category-{n}")
    name_uk = factory.Sequence(lambda n: f"Категорія {n}")
    project_type = ProjectType.MOD
    header = "categories"


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project
        skip_postgeneration_save = True

    modrinth_id = factory.Sequence(lambda n: f"MR{n:06d}")
    slug = factory.Sequence(lambda n: f"project-{n}")
    project_type = ProjectType.MOD
    title = factory.Sequence(lambda n: f"Project {n}")
    summary = "A useful mod"
    status = Project.Status.PUBLISHED
    loaders = factory.LazyFunction(lambda: ["fabric"])
    game_versions = factory.LazyFunction(lambda: ["1.21.1", "26.3"])
    modrinth_downloads = 1000
    published_at = factory.LazyFunction(lambda: datetime(2024, 1, 1, tzinfo=UTC))

    @factory.post_generation
    def categories(self, create: bool, extracted, **kwargs) -> None:
        if create and extracted:
            self.categories.set(extracted)


class VersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectVersion

    project = factory.SubFactory(ProjectFactory)
    modrinth_version_id = factory.Sequence(lambda n: f"V{n:07d}")
    version_number = factory.Sequence(lambda n: f"1.0.{n}")
    version_type = ProjectVersion.VersionType.RELEASE
    game_versions = factory.LazyFunction(lambda: ["26.3"])
    loaders = factory.LazyFunction(lambda: ["fabric"])
    file_url = factory.LazyAttribute(
        lambda version: f"https://cdn.modrinth.com/data/x/{version.modrinth_version_id}.jar"
    )
    file_name = factory.LazyAttribute(lambda version: f"{version.modrinth_version_id}.jar")
    file_size = 1024
    released_at = factory.Sequence(lambda n: datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=n))
