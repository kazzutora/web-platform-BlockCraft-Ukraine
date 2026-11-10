from contextlib import contextmanager
from unittest import mock

import pytest

from apps.core import jobs
from apps.mods import importers, tasks
from apps.mods.models import Project
from apps.sources.models import SyncRun

from .fakes import FakeModrinth, recorded

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("game_versions")]


@contextmanager
def modrinth(fake: FakeModrinth):
    """Makes tasks use the fake client as `with ModrinthClient() as client`."""
    with mock.patch("apps.mods.tasks.ModrinthClient") as factory:
        factory.return_value.__enter__.return_value = fake
        yield


def test_sync_catalog_writes_a_sync_run_per_type(settings):
    settings.SYNC_LIMITS = {"mod": 5, "resourcepack": 5, "shader": 5, "datapack": 5}

    with modrinth(recorded()):
        result = tasks.sync_catalog.delay().get()
        again = tasks.sync_catalog.delay().get()

    assert result["mod"] == {"created": 3, "updated": 0, "unchanged": 0, "skipped": 0, "failed": 0}
    assert again["mod"]["unchanged"] == 3
    assert result["shader"]["created"] == 0
    runs = SyncRun.objects.filter(job="modrinth.catalog:mod")
    assert runs.count() == 2
    assert {run.status for run in runs} == {SyncRun.Status.OK}
    assert runs.first().params == {"limit": 5}
    assert SyncRun.objects.filter(job="modrinth.catalog:datapack").exists()


def test_sync_catalog_limit_overrides_settings():
    with modrinth(recorded()):
        tasks.sync_catalog.delay(limit=20).get()

    assert SyncRun.objects.count() == 4  # mods, resource packs, shaders, datapacks
    assert all(run.params == {"limit": 20} for run in SyncRun.objects.all())


def test_a_failing_project_is_counted_and_the_rest_synced():
    real = importers.import_project

    def flaky(data, **kwargs):
        if data.slug == "sodium":
            raise ValueError("boom")
        return real(data, **kwargs)

    with modrinth(recorded()), mock.patch("apps.mods.importers.import_project", flaky):
        result = tasks.sync_catalog.delay(limit=5).get()

    assert result["mod"]["created"] == 2
    assert result["mod"]["failed"] == 1
    run = SyncRun.objects.get(job="modrinth.catalog:mod")
    assert run.status == SyncRun.Status.PARTIAL
    assert run.errors[0]["type"] == "ValueError"
    assert run.errors[0]["context"] == {"project": "sodium"}


def test_sync_versions_task_journals_its_run():
    fake = recorded()
    with modrinth(fake):
        tasks.sync_catalog.delay(limit=5).get()
        result = tasks.sync_versions.delay().get()

    assert result["created"] == 3
    run = SyncRun.objects.get(job="modrinth.versions")
    assert (run.status, run.params) == (SyncRun.Status.OK, {"full": False})


def test_import_project_job_ends_done_with_the_slug(user):
    job = jobs.create("mods.import")

    with modrinth(recorded()):
        tasks.import_project.delay(job_id=job["id"], slug="sodium", user_id=user.pk).get()

    state = jobs.get(job["id"])
    assert state["status"] == "done"
    assert state["result"] == {"slug": "sodium", "title": "Sodium", "project_type": "mod"}
    assert Project.objects.get().imported_by == user


@pytest.mark.parametrize(
    ("slug", "error"),
    [("nope", "not_found"), ("fabulously-optimized", "is_modpack")],
)
def test_import_project_job_fails_with_a_code(slug, error):
    job = jobs.create("mods.import")

    with modrinth(recorded()):
        tasks.import_project.delay(job_id=job["id"], slug=slug).get()

    assert jobs.get(job["id"])["status"] == "failed"
    assert jobs.get(job["id"])["error"] == error


def test_import_project_job_fails_on_any_unexpected_error():
    job = jobs.create("mods.import")

    with (
        modrinth(recorded()),
        mock.patch("apps.mods.services.import_from_modrinth", side_effect=RuntimeError("clash")),
        pytest.raises(RuntimeError),
    ):
        tasks.import_project.apply(kwargs={"job_id": job["id"], "slug": "sodium"}, throw=True)

    assert (jobs.get(job["id"])["status"], jobs.get(job["id"])["error"]) == ("failed", "failed")
