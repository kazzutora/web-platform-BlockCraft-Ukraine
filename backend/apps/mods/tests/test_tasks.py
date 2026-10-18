from contextlib import contextmanager
from unittest import mock

import pytest

from apps.library.models import Download
from apps.mods import tasks
from apps.mods.models import Project

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


def test_sync_popular_task_reports_counts(settings):
    settings.MODRINTH_SYNC_LIMITS = {"mod": 5}
    fake = FakeModrinth([project_payload()], {"AANobbMI": [version_payload()]})

    with modrinth(fake):
        result = tasks.sync_popular.delay().get()

    assert result["projects"] == {"mod": 1}
    assert result["versions"] == 1


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

    assert synced == 1
    assert [call[0] for call in fake.version_calls] == ["AANobbMI"]
    assert list(downloaded.versions.values_list("modrinth_version_id", flat=True)) == ["NEWONE01"]
