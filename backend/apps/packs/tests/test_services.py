import json
import zipfile
from io import BytesIO

import pytest

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.core.exceptions import DomainError
from apps.mods.models import Project, ProjectType
from apps.mods.tests.factories import ProjectFactory, VersionFactory
from apps.packs import selectors, services, tasks
from apps.packs.models import LoaderRelease, Pack, PackItem

from .factories import PackFactory, add, mod

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("game_versions")]


def items_of(pack: Pack) -> dict[str, bool]:
    """slug → added_as_dependency."""
    return dict(pack.items.values_list("project__slug", "added_as_dependency"))


@pytest.fixture
def draft(user):
    return PackFactory(author=user, status=Pack.Status.DRAFT, published_at=None)


@pytest.fixture
def queued(monkeypatch):
    calls = []
    monkeypatch.setattr(tasks.fill_dependencies, "delay", calls.append)
    return calls


# Adding and removing mods


def test_add_item_picks_the_file_and_pulls_in_required_dependencies(
    draft, user, queued, django_capture_on_commit_callbacks
):
    library = mod(slug="cloth-config")
    api = mod(slug="fabric-api", requires=[library])
    extra = mod(slug="modmenu")
    sodium = mod(slug="sodium", requires=[api], optional=[extra])

    with django_capture_on_commit_callbacks(execute=True):
        item = services.add_item(pack=draft, user=user, project_slug="sodium")

    assert item.version == sodium.versions.get()
    assert items_of(draft) == {"sodium": False, "fabric-api": True, "cloth-config": True}
    assert queued == []  # every dependency is in the catalog


def test_add_item_prefers_the_release_for_the_pack_version_and_loader(draft, user):
    project = ProjectFactory(slug="lithium")
    VersionFactory(project=project, game_versions=["1.21.1"])
    VersionFactory(project=project, loaders=["forge"])
    beta = VersionFactory(project=project, version_type="beta")
    release = VersionFactory(project=project)

    services.add_item(pack=draft, user=user, project_slug="lithium")

    assert draft.items.get().version == release != beta


def test_add_item_without_a_file_for_the_target_is_refused(draft, user):
    mod(slug="old-mod", game_versions=["1.20.1"])

    with pytest.raises(DomainError) as error:
        services.add_item(pack=draft, user=user, project_slug="old-mod")

    assert error.value.code == "no_version"
    assert "26.3 · Fabric" in error.value.message
    assert not draft.items.exists()


def test_add_item_twice_is_refused_but_a_dependency_becomes_the_authors(draft, user):
    api = mod(slug="fabric-api")
    mod(slug="sodium", requires=[api])
    services.add_item(pack=draft, user=user, project_slug="sodium")

    with pytest.raises(DomainError) as error:
        services.add_item(pack=draft, user=user, project_slug="sodium")
    services.add_item(pack=draft, user=user, project_slug="fabric-api")

    assert error.value.code == "already_added"
    assert items_of(draft) == {"sodium": False, "fabric-api": False}


def test_add_item_of_a_project_outside_the_catalog_is_404(draft, user):
    ProjectFactory(slug="hidden", status=Project.Status.PENDING)

    with pytest.raises(DomainError) as error:
        services.add_item(pack=draft, user=user, project_slug="hidden")

    assert error.value.status == 404


def test_unknown_dependencies_are_fetched_in_the_background(
    draft, user, queued, django_capture_on_commit_callbacks
):
    mod(slug="create", unknown=["FLYWHEEL"])

    with django_capture_on_commit_callbacks(execute=True):
        services.add_item(pack=draft, user=user, project_slug="create")

    assert queued == [draft.pk]
    assert selectors.missing_dependency_ids(draft) == {"FLYWHEEL"}


def test_remove_item_takes_away_dependencies_nothing_else_needs(draft, user):
    api = mod(slug="fabric-api")
    config = mod(slug="cloth-config")
    mod(slug="sodium", requires=[api])
    mod(slug="iris", requires=[api, config])
    for slug in ("sodium", "iris"):
        services.add_item(pack=draft, user=user, project_slug=slug)

    services.remove_item(pack=draft, user=user, project_slug="iris")

    assert items_of(draft) == {"sodium": False, "fabric-api": True}
    services.remove_item(pack=draft, user=user, project_slug="sodium")
    assert items_of(draft) == {}


def test_remove_item_keeps_dependencies_the_author_added(draft, user):
    api = mod(slug="fabric-api")
    mod(slug="sodium", requires=[api])
    services.add_item(pack=draft, user=user, project_slug="fabric-api")
    services.add_item(pack=draft, user=user, project_slug="sodium")

    services.remove_item(pack=draft, user=user, project_slug="sodium")

    assert items_of(draft) == {"fabric-api": False}


def test_remove_item_not_in_the_pack_is_404(draft, user):
    with pytest.raises(DomainError) as error:
        services.remove_item(pack=draft, user=user, project_slug="nope")
    assert error.value.status == 404


def test_items_can_be_made_optional(draft, user):
    mod(slug="sodium")
    services.add_item(pack=draft, user=user, project_slug="sodium")

    item = services.update_item(pack=draft, user=user, project_slug="sodium", is_required=False)

    assert item.is_required is False


def test_only_the_author_changes_a_pack(draft):
    mod(slug="sodium")
    stranger = UserFactory()

    with pytest.raises(DomainError) as error:
        services.add_item(pack=draft, user=stranger, project_slug="sodium")

    assert error.value.status == 403


def test_moderators_may_change_a_pack_but_nobody_changes_an_official_one(draft):
    mod(slug="sodium")
    moderator = UserFactory(role=User.Role.MODERATOR)
    services.add_item(pack=draft, user=moderator, project_slug="sodium")
    official = PackFactory(is_official=True, modrinth_id="FABULOUS")

    with pytest.raises(DomainError) as error:
        services.update_pack(pack=official, user=official.author, data={"title": "Моя"})

    assert error.value.code == "official_edit"


def test_too_many_items_are_refused(draft, user, monkeypatch):
    monkeypatch.setattr(services, "MAX_ITEMS", 1)
    mod(slug="sodium")
    mod(slug="lithium")
    services.add_item(pack=draft, user=user, project_slug="sodium")

    with pytest.raises(DomainError) as error:
        services.add_item(pack=draft, user=user, project_slug="lithium")

    assert error.value.code == "too_many"


# Compatibility


def test_inspect_reports_missing_files_dependencies_and_conflicts(draft):
    api = mod(slug="fabric-api", title="Fabric API")
    optifine = mod(slug="optifabric", title="OptiFabric")
    sodium = mod(slug="sodium", title="Sodium", requires=[api], breaks=[optifine])
    add(draft, sodium)
    add(draft, mod(slug="optifabric-fan", breaks=[sodium]))  # conflict listed from both sides
    add(draft, optifine)
    add(draft, mod(slug="create", unknown=["FLYWHEEL"]))
    broken = add(draft, mod(slug="broken"))
    PackItem.objects.filter(pk=broken.pk).update(version=None)

    issues = {(issue.type, issue.project.slug) for issue in selectors.inspect(draft)}
    messages = [issue.message for issue in selectors.inspect(draft)]

    assert issues == {
        ("no_version", "broken"),
        ("missing_dependency", "sodium"),
        ("missing_dependency", "create"),
        ("conflict", "sodium"),
        ("conflict", "optifabric-fan"),
    }
    assert "Потрібен «Fabric API», але його немає в зборці." in messages
    assert "Несумісний із «OptiFabric»." in messages


def test_changing_the_game_version_picks_files_again(draft, user):
    api = ProjectFactory(slug="fabric-api")
    VersionFactory(project=api, game_versions=["26.3"])
    VersionFactory(project=api, game_versions=["1.21.1"])
    sodium = ProjectFactory(slug="sodium")
    VersionFactory(
        project=sodium,
        game_versions=["26.3"],
        dependencies=[{"project_id": api.modrinth_id, "dependency_type": "required"}],
    )
    legacy = VersionFactory(project=sodium, game_versions=["1.21.1"])
    only_new = mod(slug="only-new")
    services.add_item(pack=draft, user=user, project_slug="sodium")
    services.add_item(pack=draft, user=user, project_slug="only-new")

    services.update_pack(pack=draft, user=user, data={"game_version": "1.21.1"})

    files = dict(draft.items.values_list("project__slug", "version"))
    # The 1.21.1 file has no dependencies: Fabric API is no longer pulled in
    assert files == {"sodium": legacy.pk, "only-new": None}
    assert only_new.pk in {issue.project.pk for issue in selectors.inspect(draft)}


# Lifecycle


def test_create_pack_is_a_draft_with_rendered_markdown(user):
    pack = services.create_pack(
        author=user,
        data={
            "title": "Ванілла з перчинкою",
            "game_version": "26.3",
            "loader": "fabric",
            "install_md": "Відкрий **Prism**",
            "style_tags": ["vanilla-plus"],
        },
    )

    assert pack.status == Pack.Status.DRAFT
    assert pack.slug == "vanilla-z-perchynkoiu"
    assert "<strong>Prism</strong>" in pack.install_html


def test_create_pack_limits_styles(user):
    with pytest.raises(DomainError) as error:
        services.create_pack(
            author=user,
            data={"title": "Пак", "game_version": "26.3", "loader": "fabric",
                  "style_tags": ["tech", "magic", "quests", "adventure"]},
        )  # fmt: skip
    assert error.value.fields == {"style_tags": ["Обери до 3 стилів."]}


def test_publish_needs_two_mods_with_files(draft, user):
    add(draft, mod(slug="sodium"))
    with pytest.raises(DomainError) as error:
        services.publish_pack(pack=draft, user=user)
    assert error.value.code == "too_few"

    broken = add(draft, mod(slug="broken"))
    PackItem.objects.filter(pk=broken.pk).update(version=None)
    with pytest.raises(DomainError) as error:
        services.publish_pack(pack=draft, user=user)
    assert error.value.code == "unresolved"


def test_publish_goes_live_at_once(draft, user):
    add(draft, mod(slug="sodium"))
    add(draft, mod(slug="lithium"))

    services.publish_pack(pack=draft, user=user)

    assert draft.status == Pack.Status.PUBLISHED
    assert draft.published_at is not None
    with pytest.raises(DomainError) as error:
        services.publish_pack(pack=draft, user=user)
    assert error.value.code == "already_published"


def test_fork_copies_the_pack_as_a_draft_and_counts_it(user):
    original = PackFactory(loader_version="")
    LoaderRelease.objects.create(loader="fabric", game_version="26.3", version="0.17.9")
    add(original, mod(slug="sodium"))
    add(original, mod(slug="fabric-api"), added_as_dependency=True)

    copy = services.fork_pack(pack=original, user=user)

    original.refresh_from_db()
    assert (copy.author, copy.status, copy.forked_from) == (user, Pack.Status.DRAFT, original)
    assert copy.loader_version == "0.17.9"
    assert items_of(copy) == {"sodium": False, "fabric-api": True}
    assert original.forks_count == 1

    services.delete_pack(pack=copy, user=user)
    original.refresh_from_db()
    assert original.forks_count == 0


def test_delete_pack(user):
    pack = PackFactory(author=user)

    services.delete_pack(pack=pack, user=user)

    assert not Pack.objects.exists()


# .mrpack


def read_index(content: bytes) -> dict:
    with zipfile.ZipFile(BytesIO(content)) as archive:
        assert archive.namelist() == ["modrinth.index.json"]
        return json.loads(archive.read("modrinth.index.json"))


def test_export_mrpack_lists_files_on_modrinth(draft):
    sodium = add(draft, mod(slug="sodium"))
    add(draft, mod(slug="faithful", project_type=ProjectType.RESOURCEPACK), is_required=False)
    add(draft, mod(slug="complementary", project_type=ProjectType.SHADER))
    version = sodium.version

    index = read_index(services.export_mrpack(pack=draft))

    draft.refresh_from_db()
    assert draft.downloads_count == 1
    assert index["formatVersion"] == 1
    assert index["game"] == "minecraft"
    assert index["name"] == draft.title
    assert index["dependencies"] == {"minecraft": "26.3", "fabric-loader": "0.17.2"}
    assert index["files"][0] == {
        "path": f"mods/{version.file_name}",
        "hashes": {"sha1": "1" * 40, "sha512": "5" * 128},
        "downloads": [version.file_url],
        "fileSize": 1024,
    }
    assert [file["path"].split("/")[0] for file in index["files"]] == [
        "mods",
        "resourcepacks",
        "shaderpacks",
    ]
    assert index["files"][1]["env"] == {"client": "optional", "server": "optional"}


@pytest.mark.parametrize(
    ("loader", "key"),
    [("forge", "forge"), ("neoforge", "neoforge"), ("quilt", "quilt-loader")],
)
def test_export_names_the_loader_like_modrinth(loader, key):
    pack = PackFactory(loader=loader, loader_version="")
    LoaderRelease.objects.create(loader=loader, game_version="26.3", version="1.2.3")

    assert services.mrpack_index(pack)["dependencies"] == {"minecraft": "26.3", key: "1.2.3"}


def test_export_skips_files_without_hashes_and_needs_a_loader_version():
    pack = PackFactory(loader_version="")
    item = add(pack, mod(slug="sodium"))
    item.version.sha1 = ""
    item.version.save()

    with pytest.raises(DomainError) as error:
        services.mrpack_index(pack)
    assert error.value.status == 409

    pack.loader_version = "0.17.2"
    assert services.mrpack_index(pack)["files"] == []
