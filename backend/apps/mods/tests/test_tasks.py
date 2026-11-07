from contextlib import contextmanager
from unittest import mock

import pytest

from apps.library.models import Download
from apps.mods import tasks
from apps.mods.models import Project
from apps.sources.clients.modrinth import ModrinthError
from apps.sources.models import SyncRun

from .factories import ProjectFactory, VersionFactory
from .payloads import project_payload, version_payload
from .test_sync import FakeModrinth

pytestmark = pytest.mark.django_db


@contextmanager
def modrinth(fake: FakeModrinth):
    """Makes tasks use the fake client as `with ModrinthClient() as client`."""
    with mock.patch("apps.mods.tasks.ModrinthClient") as factory:
        factory.return_value.__enter__.return_value = fake
        yield


def test_sync_popular_task_writes_a_sync_run_per_type(settings):
    settings.SYNC_LIMITS = {"mod": 5, "resourcepack": 5, "shader": 5}
    fake = FakeModrinth([project_payload()], {"AANobbMI": [version_payload()]})

    with modrinth(fake):
        result = tasks.sync_popular.delay().get()
        again = tasks.sync_popular.delay().get()

    assert result["mod"] == {"created": 1, "updated": 0, "unchanged": 0, "skipped": 0, "failed": 0}
    assert result["shader"]["created"] == 0
    assert again["mod"]["updated"] == 1
    runs = SyncRun.objects.filter(job="modrinth.catalog:mod")
    assert runs.count() == 2
    assert {run.status for run in runs} == {SyncRun.Status.OK}
    assert runs.first().params == {"limit": 5}


def test_sync_popular_task_limit_overrides_settings(settings):
    settings.SYNC_LIMITS = {"mod": 300, "resourcepack": 300, "shader": 300}
    fake = FakeModrinth([project_payload()], {"AANobbMI": [version_payload()]})

    with modrinth(fake):
        tasks.sync_popular.delay(limit=20).get()

    assert SyncRun.objects.count() == 3  # mods, resource packs, shaders
    assert all(run.params == {"limit": 20} for run in SyncRun.objects.all())


def test_a_failing_project_is_counted_and_the_rest_synced(settings):
    settings.SYNC_LIMITS = {"mod": 5, "resourcepack": 5, "shader": 5}
    fake = FakeModrinth(
        [project_payload(), project_payload("IRIS0001", "iris")],
        {"IRIS0001": [version_payload("i1", project_id="IRIS0001")]},
    )
    real = fake.get_versions

    def broken(project_id, **kwargs):
        if project_id == "AANobbMI":
            raise ModrinthError("boom")
        return real(project_id, **kwargs)

    fake.get_versions = broken
    with modrinth(fake):
        result = tasks.sync_popular.delay().get()

    assert result["mod"]["created"] == 1
    assert result["mod"]["failed"] == 1
    run = SyncRun.objects.get(job="modrinth.catalog:mod")
    assert run.status == SyncRun.Status.PARTIAL
    assert run.errors[0]["type"] == "ModrinthError"
    assert run.errors[0]["context"] == {"project": "sodium"}


def test_import_project_task_creates_a_pending_project(user):
    fake = FakeModrinth([project_payload("IRIS0001", "iris")], {})

    with modrinth(fake):
        slug = tasks.import_project.delay(slug="iris", suggested_by_id=user.pk).get()

    assert slug == "iris"
    assert Project.objects.get(slug="iris").status == Project.Status.PENDING


@pytest.mark.parametrize(
    "payload",
    [None, project_payload("PLUGIN01", "essentials", "plugin")],
    ids=["unknown slug", "unsupported type"],
)
def test_import_project_task_drops_bad_suggestions(payload):
    fake = FakeModrinth([payload] if payload else [], {})

    with modrinth(fake):
        result = tasks.import_project.delay(slug="essentials").get()

    assert result is None
    assert not Project.objects.exists()


def test_versions_are_refreshed_only_for_recently_downloaded_projects(user):
    downloaded = ProjectFactory(modrinth_id="AANobbMI")
    VersionFactory(project=downloaded, modrinth_version_id="OLDONE01")
    ProjectFactory(modrinth_id="IGNORED1")
    Download.objects.create(user=user, project=downloaded)
    fake = FakeModrinth([], {"AANobbMI": [version_payload("NEWONE01")]})

    with modrinth(fake):
        synced = tasks.sync_versions_for_tracked.delay().get()

    assert synced["updated"] == 1
    assert SyncRun.objects.get(job="modrinth.versions").status == SyncRun.Status.OK
    assert [call[0] for call in fake.version_calls] == ["AANobbMI"]
    assert list(downloaded.versions.values_list("modrinth_version_id", flat=True)) == ["NEWONE01"]
