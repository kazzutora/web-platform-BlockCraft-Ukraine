import json
import zipfile
from io import BytesIO
from unittest import mock

import pytest
from PIL import Image

from apps.accounts.tests.factories import UserFactory
from apps.core.exceptions import DomainError
from apps.mods.models import ProjectType
from apps.mods.tests.factories import ProjectFactory, VersionFactory
from apps.mods.tests.fakes import FakeModrinth
from apps.notifications.models import Notification
from apps.packs import services, tasks
from apps.packs.models import CompatStatus, LoaderRelease, Origin, Pack, Reason

from .factories import PackFactory, add, mod

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("game_versions")]


def items_of(pack: Pack) -> dict[str, tuple[str, list[str]]]:
    """slug → (reason, required_by)."""
    return {
        slug: (reason, required_by)
        for slug, reason, required_by in pack.items.values_list(
            "project__slug", "reason", "required_by"
        )
    }


@pytest.fixture
def draft(user):
    return PackFactory(author=user, status=Pack.Status.DRAFT, published_at=None)


@pytest.fixture(autouse=True)
def no_covers(monkeypatch):
    calls = []
    monkeypatch.setattr(tasks.render_cover, "delay", calls.append)
    return calls


# The set and its resolution


def test_adding_a_project_brings_its_dependencies_with_reasons(draft, user):
    api = mod(slug="fabric-api")
    sodium_extra = mod(slug="sodium-extra", requires=[mod(slug="sodium", requires=[api])])

    services.add_item(pack=draft, user=user, project_slug=sodium_extra.slug)

    assert items_of(draft) == {
        "sodium-extra": ("requested", []),
        "sodium": ("dependency", ["sodium-extra"]),
        "fabric-api": ("dependency", ["sodium"]),
    }
    draft.refresh_from_db()
    assert (draft.items_count, draft.compat_status) == (3, CompatStatus.OK)
    assert draft.compat_report["items"][0]["project"]["slug"] == "sodium-extra"


def test_a_shader_brings_its_engine(draft, user):
    mod(slug="iris")
    shader = ProjectFactory(slug="bsl", project_type=ProjectType.SHADER, loaders=["iris"])
    VersionFactory(project=shader, game_versions=["26.3"], loaders=["iris", "optifine"])

    services.add_item(pack=draft, user=user, project_slug="bsl")

    assert items_of(draft)["iris"] == ("implicit", ["bsl"])


def test_picking_a_dependency_makes_it_the_authors(draft, user):
    sodium = mod(slug="sodium")
    services.add_item(pack=draft, user=user, project_slug=mod(slug="extra", requires=[sodium]).slug)

    services.add_item(pack=draft, user=user, project_slug="sodium")

    assert items_of(draft)["sodium"] == ("requested", ["extra"])
    with pytest.raises(DomainError) as error:
        services.add_item(pack=draft, user=user, project_slug="sodium")
    assert error.value.code == "already_added"


def test_removing_a_project_takes_unneeded_dependencies_with_it(draft, user):
    sodium = mod(slug="sodium")
    services.add_item(pack=draft, user=user, project_slug=mod(slug="extra", requires=[sodium]).slug)
    services.add_item(pack=draft, user=user, project_slug=mod(slug="lithium").slug)

    with pytest.raises(DomainError) as error:
        services.remove_item(pack=draft, user=user, project_slug="sodium")
    assert error.value.code == "needed"

    services.remove_item(pack=draft, user=user, project_slug="extra")

    assert set(items_of(draft)) == {"lithium"}


def test_a_conflict_blocks_publishing(draft, user):
    lights = mod(slug="sodium-dynamic-lights")
    services.add_item(pack=draft, user=user, project_slug=mod(slug="lamb", breaks=[lights]).slug)
    services.add_item(pack=draft, user=user, project_slug=lights.slug)

    draft.refresh_from_db()
    assert draft.compat_status == CompatStatus.ERRORS
    assert draft.compat_report["conflicts"][0]["declared_by"] == "lamb"
    with pytest.raises(DomainError) as error:
        services.publish_pack(pack=draft, user=user)
    assert error.value.code == "pack_has_errors"


def test_publishing_needs_two_picks_and_a_finished_check(draft, user, monkeypatch):
    services.add_item(pack=draft, user=user, project_slug=mod(slug="one").slug)
    with pytest.raises(DomainError) as error:
        services.publish_pack(pack=draft, user=user)
    assert error.value.code == "too_few"

    monkeypatch.setattr("apps.compat.services.queue_missing", lambda ids: list(ids))
    services.add_item(
        pack=draft, user=user, project_slug=mod(slug="two", unknown=["GONE0001"]).slug
    )
    with pytest.raises(DomainError) as error:
        services.publish_pack(pack=draft, user=user)
    assert (error.value.code, error.value.status) == ("not_checked", 409)


def test_publish_by_link(draft, user):
    for slug in ("one", "two"):
        services.add_item(pack=draft, user=user, project_slug=mod(slug=slug).slug)

    services.publish_pack(pack=draft, user=user, visibility="link")

    draft.refresh_from_db()
    assert (draft.status, draft.visibility) == (Pack.Status.PUBLISHED, "link")
    assert draft.published_at is not None
    assert len(draft.share_token) == 16


def test_changing_the_game_resolves_again(draft, user):
    services.add_item(pack=draft, user=user, project_slug=mod(slug="new-only").slug)

    services.update_pack(pack=draft, user=user, data={"game_version": "1.21.1"})

    draft.refresh_from_db()
    item = draft.items.get()
    assert item.version is None
    assert draft.compat_status == CompatStatus.ERRORS
    assert draft.compat_report["items"][0]["status"] == "no_version"


def test_others_and_modrinth_packs_cannot_be_edited(draft, user):
    stranger = UserFactory()
    official = PackFactory(origin=Origin.MODRINTH)
    project = mod(slug="x")

    with pytest.raises(DomainError) as error:
        services.add_item(pack=draft, user=stranger, project_slug=project.slug)
    assert error.value.code == "forbidden"
    with pytest.raises(DomainError) as error:
        services.add_item(pack=official, user=official.author, project_slug=project.slug)
    assert error.value.code == "official_edit"


# Copies


def test_fork_for_another_game_keeps_only_the_authors_picks(draft, user):
    sodium = mod(slug="sodium", game_versions=["26.3", "1.21.1"])
    extra = mod(slug="extra", requires=[sodium], game_versions=["26.3", "1.21.1"])
    services.add_item(pack=draft, user=user, project_slug=extra.slug)
    friend = UserFactory()

    copy = services.fork_pack(pack=draft, user=friend, game_version="1.21.1")

    assert (copy.author, copy.game_version, copy.status) == (friend, "1.21.1", Pack.Status.DRAFT)
    assert items_of(copy) == {"extra": ("requested", []), "sodium": ("dependency", ["extra"])}
    draft.refresh_from_db()
    assert draft.forks_count == 1


def test_retarget_preview_tells_what_stays_changes_falls_out_and_joins(draft, user):
    both = mod(slug="both", game_versions=["26.3", "1.21.1"])
    old_only = mod(slug="new-only")
    joins = mod(slug="joins", game_versions=["1.21.1"])
    shifting = ProjectFactory(slug="shifting")
    VersionFactory(project=shifting, modrinth_version_id="SHIFT263", game_versions=["26.3"])
    VersionFactory(
        project=shifting,
        modrinth_version_id="SHIFT121",
        game_versions=["1.21.1"],
        dependencies=[{"project_id": joins.external_id, "dependency_type": "required"}],
    )
    for project in (both, old_only, shifting):
        services.add_item(pack=draft, user=user, project_slug=project.slug)

    diff = services.retarget_preview(pack=draft, game_version="1.21.1", loader="fabric")

    assert diff.kept == ["both"]
    assert diff.changed == [("shifting", "SHIFT263", "SHIFT121")]
    assert diff.dropped == ["new-only"]
    assert diff.added == ["joins"]


# .mrpack


def test_mrpack_index_follows_the_format(draft, user):
    LoaderRelease.objects.create(loader="fabric", game_version="26.3", version="0.17.2")
    draft.loader_version = ""
    draft.save()
    sodium = mod(slug="sodium")
    rp = ProjectFactory(slug="fresh", project_type=ProjectType.RESOURCEPACK, loaders=["minecraft"])
    VersionFactory(project=rp, game_versions=["26.3"], loaders=["minecraft"], sha1="2" * 40)
    dp = ProjectFactory(slug="terra", project_type=ProjectType.DATAPACK, loaders=["datapack"])
    VersionFactory(project=dp, game_versions=["26.3"], loaders=["datapack"], sha1="3" * 40)
    for slug in ("sodium", "fresh", "terra"):
        services.add_item(pack=draft, user=user, project_slug=slug)
    services.update_item(pack=draft, user=user, project_slug="fresh", optional=True)

    index = services.mrpack_index(Pack.objects.get(pk=draft.pk))

    assert (index["formatVersion"], index["game"]) == (1, "minecraft")
    assert index["dependencies"] == {"minecraft": "26.3", "fabric-loader": "0.17.2"}
    files = {file["path"].split("/")[0]: file for file in index["files"]}
    assert set(files) == {"mods", "resourcepacks"}  # datapacks go into a world
    assert set(files["mods"]["hashes"]) == {"sha1", "sha512"}
    assert files["mods"]["downloads"][0].startswith("https://cdn.modrinth.com/")
    assert files["resourcepacks"]["env"] == {"client": "optional", "server": "optional"}
    assert sodium.versions.get().file_name in files["mods"]["path"]


def test_export_is_a_zip_with_the_index_and_counts_a_download(draft, user):
    services.add_item(pack=draft, user=user, project_slug=mod(slug="sodium").slug)

    content = services.export_mrpack(pack=draft)

    with zipfile.ZipFile(BytesIO(content)) as archive:
        assert archive.namelist() == ["modrinth.index.json"]
        assert json.loads(archive.read("modrinth.index.json"))["name"] == draft.title
    draft.refresh_from_db()
    assert draft.downloads_count == 1


def test_without_a_loader_version_export_says_so(draft):
    draft.loader_version = ""
    draft.save()

    with pytest.raises(DomainError) as error:
        services.mrpack_index(draft)
    assert (error.value.code, error.value.status) == ("no_loader_version", 409)


# Cover


def png(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_cover_is_a_mosaic_of_the_first_icons(draft, user):
    fake = FakeModrinth()
    fake.images = {}
    for index, color in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
        url = f"https://cdn.modrinth.com/data/P{index}/icon.png"
        fake.images[url] = png(color)
        add(draft, mod(slug=f"p{index}", icon_url=url), reason=Reason.REQUESTED)
    add(draft, mod(slug="broken", icon_url="https://cdn.modrinth.com/data/x/missing.png"))
    fake.images["https://cdn.modrinth.com/data/x/missing.png"] = b"not an image"

    assert services.render_cover(client=fake, pack=draft)

    draft.refresh_from_db()
    with Image.open(draft.cover) as cover:
        assert cover.size == (600, 600)
        red, green, blue = cover.getpixel((150, 150))[:3]
        assert red > 240 and green < 20 and blue < 20  # WebP is lossy


def test_cover_without_icons_is_left_alone(draft):
    add(draft, mod(slug="plain", icon_url=""))

    assert not services.render_cover(client=FakeModrinth(), pack=draft)


# Nightly recheck


def test_recheck_tells_the_author_when_a_pack_got_worse(user):
    pack = PackFactory(author=user)
    sodium = mod(slug="sodium")
    add(pack, sodium)
    add(pack, mod(slug="extra", requires=[sodium]))
    services.recheck(pack)
    sodium.versions.all().delete()  # Modrinth dropped the file

    with mock.patch("apps.packs.tasks.services.recheck", wraps=services.recheck):
        counts = tasks.recheck.delay().get()

    assert counts == {"checked": 1, "worse": 1}
    note = Notification.objects.get(user=user)
    assert (note.type, note.payload["id"]) == ("pack_attention", pack.slug)
    assert tasks.recheck.delay().get() == {"checked": 1, "worse": 0}


# Review fixes


def test_changing_the_game_forgets_the_old_loader_build(draft, user):
    draft.loader_version = "0.15.0"
    draft.save()

    services.update_pack(
        pack=draft, user=user, data={"game_version": "1.21.1", "loader_version": "0.15.0"}
    )
    draft.refresh_from_db()
    assert draft.loader_version == ""

    services.update_pack(
        pack=draft, user=user, data={"game_version": "26.3", "loader_version": "0.17.9"}
    )
    draft.refresh_from_db()
    assert draft.loader_version == "0.17.9"  # chosen with the move: kept


def test_mrpack_takes_only_files_on_modrinths_cdn(draft, user):
    services.add_item(pack=draft, user=user, project_slug=mod(slug="good").slug)
    bad = mod(slug="bad")
    bad.versions.update(file_url="https://evil.example/bad.jar")
    services.add_item(pack=draft, user=user, project_slug=bad.slug)

    paths = [file["downloads"][0] for file in services.mrpack_index(draft)["files"]]

    assert len(paths) == 1 and paths[0].startswith("https://cdn.modrinth.com/")


def test_a_huge_modpack_is_refused_with_words(user, monkeypatch):
    monkeypatch.setattr(services, "MAX_ITEMS", 1)
    pack = PackFactory(origin=Origin.MODRINTH)
    add(pack, mod())
    add(pack, mod())

    for call in (
        lambda: services.fork_pack(pack=pack, user=user),
        lambda: services.retarget_preview(pack=pack, game_version="1.21.1", loader="fabric"),
    ):
        with pytest.raises(DomainError) as error:
            call()
        assert error.value.code == "too_big_to_copy"


def test_first_check_is_not_a_worsening(user):
    pack = PackFactory(author=user)
    add(pack, mod(slug="ok"))

    assert tasks.recheck.delay().get() == {"checked": 1, "worse": 0}
    assert not Notification.objects.exists()
