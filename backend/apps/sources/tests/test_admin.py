import pytest

from apps.sources.models import SyncRun
from apps.sources.runs import sync_run

pytestmark = pytest.mark.django_db

URL = "/admin/sources/syncrun/"


def test_admin_lists_runs_filtered_by_source_and_status(admin_client):
    with sync_run("modrinth", "modrinth.catalog:mod") as run:
        run.created += 3
    with sync_run("loaders", "loaders.releases"):
        pass

    page = admin_client.get(URL, {"source": "modrinth", "status": "ok"})

    assert page.status_code == 200
    assert b"modrinth.catalog:mod" in page.content
    assert b"loaders.releases" not in page.content


def test_runs_are_read_only_in_admin(admin_client):
    with sync_run("modrinth", "modrinth.versions"):
        pass

    record = SyncRun.objects.get()
    assert admin_client.get(f"{URL}add/").status_code == 403
    page = admin_client.get(f"{URL}{record.pk}/change/")
    assert page.status_code == 200
    assert b'name="_save"' not in page.content
