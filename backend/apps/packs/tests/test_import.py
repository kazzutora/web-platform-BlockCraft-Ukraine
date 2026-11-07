import json
import zipfile
from contextlib import contextmanager
from io import BytesIO
from unittest import mock

import pytest

from apps.core.exceptions import DomainError
from apps.mods.models import Project
from apps.mods.schemas import ModrinthProject, ModrinthVersion, VersionFile
from apps.mods.tests.factories import ProjectFactory, VersionFactory
from apps.mods.tests.payloads import project_payload, version_payload
from apps.mods.tests.test_sync import FakeModrinth
from apps.packs import services, tasks
from apps.packs.models import LoaderRelease, Pack

from .factories import PackFactory, mod

pytestmark = pytest.mark.django_db

MRPACK_URL = "https://cdn.modrinth.com/data/FABULOUS/versions/PACKV001/fabulously.mrpack"


def cdn(project_id: str, version_id: str) -> str:
    return f"https://cdn.modrinth.com/data/{project_id}/versions/{version_id}/file.jar"


def mrpack(files: list[dict], dependencies: dict | None = None) -> bytes:
    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": "9.0",
        "name": "Fabulously Optimized",
        "files": [
            {"hashes": {"sha1": "a" * 40, "sha512": "b" * 128}, "fileSize": 10, **file}
            for file in files
        ],
        "dependencies": dependencies or {"minecraft": "26.3", "fabric-loader": "0.17.2"},
    }
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("modrinth.index.json", json.dumps(index))
        archive.writestr("overrides/config/sodium.json", "{}")
    return buffer.getvalue()


class FakeModrinthWithFiles(FakeModrinth):
    def __init__(self, projects, versions, files: dict[str, bytes]):
        super().__init__(projects, versions)
        self.files = files
        self.downloads: list[str] = []

    def get_projects(self, ids):
        # The real API leaves out ids it does not know
        return [ModrinthProject.model_validate(self.projects[i]) for i in ids if i in self.projects]

    def read_zip_member(self, url, *, size, name, max_bytes):
        self.downloads.append(url)
        with zipfile.ZipFile(BytesIO(self.files[url])) as archive:
            return archive.read(name)


def modpack_payload(**overrides) -> dict:
    return project_payload(
        "FABULOUS",
        "fabulously-optimized",
        "modpack",
        categories=["optimization", "lightweight", "unknown"],
        **overrides,
    )


def modpack_version(version_id: str = "PACKV001", **overrides) -> dict:
    payload = version_payload(version_id, "FABULOUS", **overrides)
    payload["files"][0]["url"] = MRPACK_URL
    payload["changelog"] = "* Оновлено **Sodium**"
    return payload


@pytest.fixture
def fake():
    sodium = ProjectFactory(modrinth_id="AANobbMI", slug="sodium")
    VersionFactory(project=sodium, modrinth_version_id="SODIUM01")
    VersionFactory(project=sodium, modrinth_version_id="SODIUM02")
    files = [
        {"path": "mods/sodium.jar", "downloads": [cdn("AANobbMI", "SODIUM01")]},
        # Not in our catalog yet: imported with its versions
        {"path": "mods/iris.jar", "downloads": [cdn("YL57xq9U", "IRIS0001")]},
        # A file we do not know any more: the newest fitting one is used
        {"path": "mods/modmenu.jar", "downloads": [cdn("mOgUt4GM", "GONE0001")]},
        {
            "path": "mods/zoom.jar",
            "downloads": [cdn("w7ThoJFB", "ZOOM0001")],
            "env": {"client": "optional", "server": "unsupported"},
        },
        {
            "path": "mods/server-only.jar",
            "downloads": [cdn("SRVONLY1", "SRV00001")],
            "env": {"client": "unsupported", "server": "required"},
        },
        {"path": "mods/elsewhere.jar", "downloads": ["https://github.com/x/elsewhere.jar"]},
        # A plugin: not a type our catalog keeps
        {"path": "mods/plugin.jar", "downloads": [cdn("PLUGIN01", "PLUG0001")]},
    ]
    modmenu = ProjectFactory(modrinth_id="mOgUt4GM", slug="modmenu")
    VersionFactory(project=modmenu, modrinth_version_id="MODMENU2")
    ProjectFactory(modrinth_id="w7ThoJFB", slug="zoomify")
    VersionFactory(project=Project.objects.get(slug="zoomify"), modrinth_version_id="ZOOM0001")
    return FakeModrinthWithFiles(
        [
            modpack_payload(),
            project_payload("YL57xq9U", "iris"),
            project_payload("PLUGIN01", "essentials", "plugin"),
        ],
        {
            "FABULOUS": [
                modpack_version("PACKBETA", version_type="beta", date="2026-10-10T00:00:00Z"),
                modpack_version(),
                modpack_version("PACKFRG1", loaders=["forge"], game_versions=["1.7.10"]),
            ],
            "YL57xq9U": [version_payload("IRIS0001", "YL57xq9U")],
        },
        {MRPACK_URL: mrpack(files)},
    )


def test_import_modpack_creates_an_official_pack(fake):
    pack = services.import_modpack(client=fake, data=fake.get_projects(["FABULOUS"])[0])

    assert pack.is_official
    assert pack.status == Pack.Status.PUBLISHED
    assert pack.author.nickname == "BlockCraft"
    assert not pack.author.has_usable_password()
    pack.author.refresh_from_db()
    assert pack.author.published_count == 1
    assert (pack.game_version, pack.loader, pack.loader_version) == ("26.3", "fabric", "0.17.2")
    assert pack.style_tags == ["performance", "lightweight"]
    assert pack.source_file_url == MRPACK_URL
    assert pack.modrinth_version_id == "PACKV001"
    assert "<strong>Sodium</strong>" in pack.changelog_html
    files = {
        item.project.slug: (item.version.modrinth_version_id, item.is_required)
        for item in pack.items.select_related("project", "version")
    }
    assert files == {
        "sodium": ("SODIUM01", True),
        "iris": ("IRIS0001", True),
        "modmenu": ("MODMENU2", True),
        "zoomify": ("ZOOM0001", False),
    }
    assert Project.objects.get(slug="iris").status == Project.Status.PUBLISHED
    assert fake.downloads == [MRPACK_URL]


def test_import_modpack_again_only_refreshes_downloads_until_a_new_version(fake):
    data = fake.get_projects(["FABULOUS"])[0]
    pack = services.import_modpack(client=fake, data=data)

    again = services.import_modpack(
        client=fake, data=ModrinthProject.model_validate(modpack_payload(downloads=5_000_000))
    )

    pack.refresh_from_db()
    assert again.pk == pack.pk
    assert pack.modrinth_downloads == 5_000_000
    assert fake.downloads == [MRPACK_URL]

    fake.versions["FABULOUS"].append(modpack_version("PACKV002", date="2026-10-20T00:00:00Z"))
    services.import_modpack(client=fake, data=data)

    pack.refresh_from_db()
    assert pack.modrinth_version_id == "PACKV002"
    assert Pack.objects.count() == 1
    pack.author.refresh_from_db()
    assert pack.author.published_count == 1


def test_modpacks_without_a_supported_version_are_skipped(fake):
    fake.versions["FABULOUS"] = [
        modpack_version("PACKFRG1", loaders=["forge"], game_versions=["1.7.10"])
    ]

    assert services.import_modpack(client=fake, data=fake.get_projects(["FABULOUS"])[0]) is None
    assert not Pack.objects.exists()


def test_pick_modpack_version_prefers_the_newest_release():
    versions = [
        ModrinthVersion.model_validate(modpack_version("OLDREL01", date="2026-01-01T00:00:00Z")),
        ModrinthVersion.model_validate(modpack_version("NEWREL01", date="2026-09-01T00:00:00Z")),
        ModrinthVersion.model_validate(
            modpack_version("BETA0001", version_type="beta", date="2026-10-01T00:00:00Z")
        ),
        ModrinthVersion.model_validate(
            modpack_version("VANILLA1", loaders=["minecraft"], date="2026-10-02T00:00:00Z")
        ),
    ]

    assert services.pick_modpack_version(versions).id == "NEWREL01"
    assert services.pick_modpack_version(versions[2:3]).id == "BETA0001"


def zip_with(name: str, content: str) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, content)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "content",
    [
        b"not a zip",
        mrpack([])[:40],
        zip_with("readme.txt", "hi"),
        zip_with("modrinth.index.json", '{"files": []}'),
    ],
    ids=["garbage", "truncated", "no index", "not an index"],
)
def test_read_index_refuses_what_is_not_a_modpack(content):
    fake = FakeModrinthWithFiles([], {}, {MRPACK_URL: content})
    file = VersionFile(url=MRPACK_URL, filename="x.mrpack", size=len(content))

    with pytest.raises(DomainError) as error:
        services.read_index(client=fake, file=file)

    assert error.value.code == "invalid_mrpack"


def test_import_popular_modpacks_skips_broken_ones(fake):
    fake.projects["BROKEN01"] = project_payload("BROKEN01", "broken-pack", "modpack")
    fake.versions["BROKEN01"] = [version_payload("BRKN0001", "BROKEN01")]
    fake.files[cdn("BROKEN01", "BRKN0001")] = b"oops"
    fake.versions["BROKEN01"][0]["files"][0]["url"] = cdn("BROKEN01", "BRKN0001")

    imported = services.import_popular_modpacks(client=fake, limit=10)

    assert imported == ["fabulously-optimized"]


# Tasks


@contextmanager
def modrinth(fake):
    with mock.patch("apps.packs.tasks.ModrinthClient") as factory:
        factory.return_value.__enter__.return_value = fake
        yield


def test_import_official_task(fake, settings):
    settings.MODRINTH_OFFICIAL_PACKS = 3

    with modrinth(fake):
        assert tasks.import_official.delay().get() == ["fabulously-optimized"]


def test_fill_dependencies_task_brings_in_and_adds_missing_ones(user):
    pack = PackFactory(author=user, status=Pack.Status.DRAFT)
    create = mod(slug="create", unknown=["FLYWHEEL"])
    services.add_item(pack=pack, user=user, project_slug=create.slug)
    fake = FakeModrinthWithFiles(
        [project_payload("FLYWHEEL", "flywheel")],
        {"FLYWHEEL": [version_payload("FLY00001", "FLYWHEEL")]},
        {},
    )

    with modrinth(fake):
        added = tasks.fill_dependencies.delay(pack.pk).get()

    assert added == 1
    item = pack.items.get(project__slug="flywheel")
    assert item.added_as_dependency
    assert item.version.modrinth_version_id == "FLY00001"
    with modrinth(fake):
        assert tasks.fill_dependencies.delay(pack.pk).get() == 0
        assert tasks.fill_dependencies.delay(999_999).get() == 0


def test_refresh_loader_versions_task_stores_builds():
    LoaderRelease.objects.create(loader="fabric", game_version="26.3", version="0.1.0")
    found = {("fabric", "26.3"): "0.17.2", ("neoforge", "1.21.1"): "21.1.200"}

    with mock.patch("apps.packs.tasks.LoaderClient") as factory:
        factory.return_value.__enter__.return_value.latest_many.return_value = found
        assert tasks.refresh_loader_versions.delay().get() == 2

    assert dict(LoaderRelease.objects.values_list("loader", "version")) == {
        "fabric": "0.17.2",
        "neoforge": "21.1.200",
    }


def test_versions_of_projects_in_packs_are_kept_fresh(user):
    from apps.mods import tasks as mod_tasks

    pack = PackFactory()
    project = mod(slug="iris", modrinth_id="YL57xq9U")
    pack.items.create(project=project, version=project.versions.get())
    fake = FakeModrinth([], {"YL57xq9U": [version_payload("IRIS0002", "YL57xq9U")]})

    with mock.patch("apps.mods.tasks.ModrinthClient") as factory:
        factory.return_value.__enter__.return_value = fake
        assert mod_tasks.sync_versions_for_tracked.delay().get() == 1

    # The file left Modrinth: the item stays and waits for another pick
    item = pack.items.get()
    assert item.version is None
    assert project.versions.get().modrinth_version_id == "IRIS0002"
