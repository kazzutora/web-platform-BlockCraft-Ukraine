from datetime import timedelta

import pytest
from django.utils import timezone

from apps.sources import selectors
from apps.sources.models import SyncRun

pytestmark = pytest.mark.django_db

URL = "/api/v1/sources"


def run(job: str, *, source: str = "modrinth", ago: int = 0, **fields) -> SyncRun:
    started = timezone.now() - timedelta(hours=ago)
    return SyncRun.objects.create(
        source=source,
        job=job,
        started_at=started,
        finished_at=started + timedelta(minutes=5),
        status=fields.pop("status", SyncRun.Status.OK),
        **fields,
    )


def by_key(body: list[dict]) -> dict[str, dict]:
    return {source["key"]: source for source in body}


def test_every_registered_source_is_listed_even_before_any_sync(api_client):
    body = by_key(api_client.get(URL).json())

    assert set(body) == {"modrinth", "mineskin", "mojang", "loaders"}
    modrinth = body["modrinth"]
    assert modrinth["name"] == "Modrinth"
    assert modrinth["terms_url"] == "https://modrinth.com/legal/terms"
    assert modrinth["last_sync"] is None
    assert [job["key"] for job in modrinth["jobs"]] == [
        "game_versions",
        "catalog",
        "versions",
        "modpacks",
    ]
    assert body["mojang"]["jobs"] == []


def test_catalog_runs_of_every_type_add_up_and_the_worst_status_wins(api_client):
    run("modrinth.catalog:mod", ago=30, created=50)  # older run of the same job: ignored
    run("modrinth.catalog:mod", ago=2, created=3, updated=10)
    run("modrinth.catalog:shader", ago=2, updated=4, failed=1, status=SyncRun.Status.PARTIAL)
    run("modrinth.game_versions", ago=1, unchanged=922)

    modrinth = by_key(api_client.get(URL).json())["modrinth"]
    jobs = {job["key"]: job["last_run"] for job in modrinth["jobs"]}

    assert jobs["catalog"]["status"] == "partial"
    assert (jobs["catalog"]["created"], jobs["catalog"]["updated"], jobs["catalog"]["failed"]) == (
        3,
        14,
        1,
    )
    assert jobs["versions"] is None
    assert modrinth["last_sync"]["unchanged"] == 922  # the most recent job


def test_a_running_job_has_no_finish_time(api_client):
    SyncRun.objects.create(source="loaders", job="loaders.releases")

    last = by_key(api_client.get(URL).json())["loaders"]["last_sync"]

    assert (last["status"], last["finished_at"]) == ("running", None)


def test_the_overview_is_cached_and_cheap(api_client, django_assert_max_num_queries):
    run("modrinth.catalog:mod")
    with django_assert_max_num_queries(1):
        api_client.get(URL)
    with django_assert_max_num_queries(0):
        api_client.get(URL)
    selectors.forget_sources()
    with django_assert_max_num_queries(1):
        api_client.get(URL)
