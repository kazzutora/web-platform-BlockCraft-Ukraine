import pytest

from apps.sources.models import SyncRun
from apps.sources.runs import MAX_ERRORS, sync_run

pytestmark = pytest.mark.django_db


def test_a_clean_run_stores_counters_and_finishes_ok():
    with sync_run("modrinth", "modrinth.catalog:mod", {"limit": 5}) as run:
        assert SyncRun.objects.get().status == SyncRun.Status.RUNNING
        run.created += 2
        run.updated += 1
        run.unchanged += 4
        run.skipped += 1

    record = SyncRun.objects.get()
    assert record.status == SyncRun.Status.OK
    assert (record.created, record.updated, record.unchanged, record.skipped, record.failed) == (
        2,
        1,
        4,
        1,
        0,
    )
    assert record.params == {"limit": 5}
    assert record.finished_at is not None
    assert record.duration is not None


def test_a_failing_item_is_counted_and_the_job_goes_on():
    with sync_run("modrinth", "modrinth.versions") as run:
        for slug in ["sodium", "iris", "lithium"]:
            with run.item(project=slug):
                if slug == "iris":
                    raise ValueError("no versions")
                run.updated += 1

    record = SyncRun.objects.get()
    assert record.status == SyncRun.Status.PARTIAL
    assert (record.updated, record.failed) == (2, 1)
    assert record.errors == [
        {"message": "no versions", "type": "ValueError", "context": {"project": "iris"}}
    ]


def test_a_run_where_every_item_fails_is_failed():
    with sync_run("mineskin", "mineskin.gallery") as run, run.item(skin="a"):
        raise RuntimeError("down")

    assert SyncRun.objects.get().status == SyncRun.Status.FAILED


def test_an_escaping_exception_fails_the_run_and_is_re_raised():
    with pytest.raises(ConnectionError), sync_run("modrinth", "modrinth.catalog:shader") as run:
        run.created += 1
        raise ConnectionError("Modrinth is down")

    record = SyncRun.objects.get()
    assert record.status == SyncRun.Status.FAILED
    assert record.created == 1
    assert record.errors == [
        {"message": "Modrinth is down", "type": "ConnectionError", "context": {"stage": "run"}}
    ]


def test_only_the_first_errors_are_kept_as_examples():
    with sync_run("modrinth", "modrinth.versions") as run:
        for number in range(MAX_ERRORS + 5):
            run.fail(f"error {number}", item=number)

    record = SyncRun.objects.get()
    assert record.failed == MAX_ERRORS + 5
    assert len(record.errors) == MAX_ERRORS
    assert record.errors[0] == {"message": "error 0", "context": {"item": "0"}}
