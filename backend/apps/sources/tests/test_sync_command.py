from io import StringIO
from unittest import mock

import pytest
from django.core.management import CommandError, call_command

from apps.core.models import Source
from apps.sources import registry


def run(*args: str) -> str:
    out = StringIO()
    call_command("sync", *args, stdout=out)
    return out.getvalue()


def test_every_registered_job_can_be_loaded():
    keys = [source.key for source in registry.SOURCES]
    assert len(keys) == len(set(keys))
    assert {Source.MODRINTH, Source.MINESKIN, Source.MOJANG} <= set(keys)
    for source in registry.SOURCES:
        assert source.name and source.description and source.url.startswith("https://")
        for job in source.jobs:
            assert callable(job.load())


def test_one_source_runs_all_its_jobs():
    with (
        mock.patch("apps.sources.tasks.sync_game_versions") as game_versions,
        mock.patch("apps.mods.tasks.sync_catalog") as catalog,
        mock.patch("apps.mods.tasks.sync_versions") as versions,
        mock.patch("apps.packs.tasks.import_official") as modpacks,
        mock.patch("apps.packs.tasks.refresh_loader_versions") as loaders,
    ):
        output = run("--source", "modrinth")

    modpacks.assert_called_once_with()

    game_versions.assert_called_once_with()
    catalog.assert_called_once_with()
    versions.assert_called_once_with()
    loaders.assert_not_called()
    assert "modrinth.catalog" in output


def test_limit_goes_only_to_jobs_that_accept_it():
    with (
        mock.patch("apps.sources.tasks.sync_game_versions") as game_versions,
        mock.patch("apps.mods.tasks.sync_catalog") as catalog,
        mock.patch("apps.mods.tasks.sync_versions") as versions,
        mock.patch("apps.packs.tasks.import_official") as modpacks,
    ):
        run("--source", "modrinth", "--limit", "20")

    modpacks.assert_called_once_with(limit=20)

    game_versions.assert_called_once_with()

    catalog.assert_called_once_with(limit=20)
    versions.assert_called_once_with()


def test_one_job_of_a_source():
    with (
        mock.patch("apps.mods.tasks.sync_catalog") as catalog,
        mock.patch("apps.mods.tasks.sync_versions") as versions,
    ):
        run("--source", "modrinth", "--job", "catalog", "--limit", "20")

    catalog.assert_called_once_with(limit=20)
    versions.assert_not_called()


def test_a_source_without_jobs_says_so():
    assert "no sync jobs yet" in run("--source", "mojang")


@pytest.mark.parametrize(
    "args",
    [("--source", "namemc"), ("--source", "modrinth", "--job", "skins"), ("--job", "catalog")],
)
def test_unknown_source_or_job_is_an_error(args):
    with pytest.raises(CommandError):
        run(*args)
