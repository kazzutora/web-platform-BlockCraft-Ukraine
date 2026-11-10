from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core.exceptions import DomainError
from apps.mods import services
from apps.mods.models import Project, ProjectType
from apps.sources.clients.modrinth import ModrinthNotFoundError
from apps.sources.runs import SyncCounter

from .fakes import recorded

pytestmark = pytest.mark.django_db

GAME = ["1.21.1"]


def catalog(fake, project_type="mod", limit=10) -> SyncCounter:
    run = SyncCounter()
    services.sync_catalog(
        client=fake,
        project_type=project_type,
        limit=limit,
        game_versions=GAME,
        run=run,
        progress=lambda message: None,
    )
    return run


def test_catalog_creates_then_finds_nothing_changed():
    fake = recorded()

    first = catalog(fake)
    second = catalog(fake)

    assert (first.created, first.unchanged) == (3, 0)  # sodium, the datapack, terralith
    assert (second.created, second.unchanged) == (0, 3)
    assert set(Project.objects.values_list("project_type", flat=True)) == {"mod", "datapack"}
    assert fake.version_calls == []  # versions are the versions job's business


def test_catalog_respects_the_limit_and_skips_other_types():
    fake = recorded()
    fake.hits["mod"] = ["1KVo5zza", "AANobbMI", "8oi3bsk5"]  # a modpack among the hits

    run = catalog(fake, limit=2)

    assert (run.created, run.skipped) == (1, 1)
    assert list(Project.objects.values_list("slug", flat=True)) == ["sodium"]


def versions_job(fake, **kwargs) -> SyncCounter:
    run = SyncCounter()
    services.sync_versions(client=fake, game_versions=GAME, run=run, **kwargs)
    return run


def test_versions_are_read_only_for_changed_projects():
    fake = recorded()
    catalog(fake)

    first = versions_job(fake)
    second = versions_job(fake)
    Project.objects.filter(slug="sodium").update(
        modrinth_updated_at=timezone.now() + timedelta(minutes=1)
    )
    third = versions_job(fake)

    assert (first.created, first.unchanged) == (3, 0)
    assert (second.created, second.updated, second.unchanged) == (0, 0, 3)
    assert (third.updated, third.unchanged) == (1, 2)
    assert Project.objects.get(slug="sodium").versions.count() == 3
    assert fake.version_calls[0] == ("AANobbMI", GAME)


def test_full_versions_job_reads_everything():
    fake = recorded()
    catalog(fake)
    versions_job(fake)

    assert versions_job(fake, full=True).updated == 3


def test_stale_projects_outside_the_top_are_refreshed_and_missing_ones_skipped():
    fake = recorded()
    catalog(fake)
    stale = timezone.now() - timedelta(days=2)
    Project.objects.update(synced_at=stale)
    del fake.projects["TiFXQSAQ"]  # removed from Modrinth

    run = versions_job(fake)

    assert run.skipped == 1
    assert Project.objects.get(slug="mysticmons").synced_at == stale
    assert Project.objects.get(slug="sodium").synced_at > stale


def test_import_by_link_brings_project_and_versions(user):
    fake = recorded()

    project = services.import_from_modrinth(
        client=fake, slug="mysticmons", user=user, game_versions=GAME
    )

    assert project.project_type == ProjectType.DATAPACK
    assert project.imported_by == user
    assert project.versions.count() == 2


def test_import_by_link_refuses_modpacks_and_unknown_slugs(user):
    fake = recorded()

    with pytest.raises(DomainError) as error:
        services.import_from_modrinth(
            client=fake, slug="fabulously-optimized", user=user, game_versions=GAME
        )
    assert error.value.code == "is_modpack"
    with pytest.raises(ModrinthNotFoundError):
        services.import_from_modrinth(client=fake, slug="nope", user=user, game_versions=GAME)
    assert not Project.objects.exists()


def test_import_by_id_of_a_hidden_project_is_refused(user):
    fake = recorded()
    services.import_from_modrinth(client=fake, slug="sodium", user=user, game_versions=GAME)
    Project.objects.update(is_hidden=True)

    with pytest.raises(DomainError) as error:
        services.import_from_modrinth(client=fake, slug="AANobbMI", user=user, game_versions=GAME)

    assert error.value.code == "hidden_project"


def test_versions_used_by_packs_survive_when_their_game_version_is_dropped():
    from apps.packs.tests.factories import PackFactory

    fake = recorded()
    catalog(fake)
    sodium = Project.objects.get(slug="sodium")
    services.sync_project_versions(client=fake, project=sodium, game_versions=GAME)
    kept, gone = sodium.versions.all()[:2]
    PackFactory().items.create(project=sodium, version=kept)
    fake.versions["AANobbMI"] = []

    # 1.21.1 is no longer asked for: the pack keeps its file, the unused one goes
    services.sync_project_versions(client=fake, project=sodium, game_versions=["26.1"])
    assert list(sodium.versions.values_list("pk", flat=True)) == [kept.pk]
    # Asked again and still absent: deleted on Modrinth, so it goes too
    services.sync_project_versions(client=fake, project=sodium, game_versions=GAME)
    assert not sodium.versions.exists()
    assert gone.pk != kept.pk


def test_import_missing_takes_only_unknown_supported_projects():
    fake = recorded()
    catalog(fake)
    Project.objects.filter(slug="terralith").delete()

    imported = services.import_missing(
        client=fake, modrinth_ids={"AANobbMI", "8oi3bsk5", "1KVo5zza"}, game_versions=GAME
    )

    assert imported == 1
    assert Project.objects.get(slug="terralith").versions.count() == 3
