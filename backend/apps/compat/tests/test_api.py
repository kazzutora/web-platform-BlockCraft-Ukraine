import itertools
from unittest import mock

import pytest

from apps.mods.tests.factories import ProjectFactory, VersionFactory

pytestmark = pytest.mark.django_db


def requires(*projects, kind="required"):
    return [
        {"project_id": p.external_id, "version_id": None, "dependency_type": kind} for p in projects
    ]


@pytest.fixture
def sodium_extra():
    sodium = ProjectFactory(slug="sodium", external_id="AANobbMI")
    VersionFactory(project=sodium, game_versions=["1.21.1"], modrinth_version_id="SOD1")
    extra = ProjectFactory(slug="sodium-extra", game_versions=["1.21.1"])
    VersionFactory(
        project=extra,
        game_versions=["1.21.1"],
        modrinth_version_id="EXT1",
        dependencies=[
            *requires(sodium),
            {"project_id": "NOTHERE1", "version_id": None, "dependency_type": "optional"},
        ],
    )
    return extra


def test_install_explains_dependencies_for_a_guest(api_client, sodium_extra):
    data = api_client.get(
        "/api/v1/mods/sodium-extra/install", {"game_version": "1.21.1", "loader": "fabric"}
    ).json()

    assert data["status"] == "ok"
    assert data["target"] == {"game_version": "1.21.1", "loader": "fabric"}
    first, dependency = data["items"]
    assert (first["project"]["slug"], first["version"]["id"], first["reason"]) == (
        "sodium-extra",
        "EXT1",
        "requested",
    )
    assert (dependency["project"]["slug"], dependency["reason"], dependency["required_by"]) == (
        "sodium",
        "dependency",
        ["sodium-extra"],
    )
    assert data["suggestions"] == [
        {"project_id": "NOTHERE1", "project": None, "suggested_by": "sodium-extra"}
    ]


def test_install_defaults_to_my_game_then_to_the_project(api_client, sodium_extra, game_versions):
    assert api_client.get("/api/v1/mods/sodium-extra/install").json()["target"] == {
        "game_version": "1.21.1",
        "loader": "fabric",
    }
    api_client.cookies["bc_game"] = "1.20.1:forge"

    data = api_client.get("/api/v1/mods/sodium-extra/install").json()

    assert data["target"] == {"game_version": "1.20.1", "loader": "forge"}
    assert data["items"][0]["status"] == "no_version"
    assert data["items"][0]["nearest_game_versions"] == []


def test_install_of_a_hidden_project_is_404(api_client):
    ProjectFactory(slug="gone", is_hidden=True)

    assert api_client.get("/api/v1/mods/gone/install").status_code == 404


def test_missing_dependency_is_imported_once_and_the_answer_is_incomplete(
    api_client, django_capture_on_commit_callbacks
):
    mod = ProjectFactory(slug="needs-api")
    VersionFactory(
        project=mod,
        game_versions=["1.21.1"],
        dependencies=[
            {"project_id": "FABRICAPI", "version_id": None, "dependency_type": "required"}
        ],
    )
    query = {"game_version": "1.21.1", "loader": "fabric"}

    with (
        mock.patch("apps.mods.tasks.import_missing.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        first = api_client.get("/api/v1/mods/needs-api/install", query).json()
        api_client.get("/api/v1/mods/needs-api/install", query)

    assert (first["status"], first["missing"]) == ("incomplete", ["FABRICAPI"])
    delay.assert_called_once_with(["FABRICAPI"])


def test_install_reads_a_fixed_number_of_queries(api_client, django_assert_max_num_queries):
    chain = [ProjectFactory(slug=f"p{n}") for n in range(6)]
    for current, following in itertools.pairwise(chain):
        VersionFactory(project=current, game_versions=["1.21.1"], dependencies=requires(following))
    VersionFactory(project=chain[-1], game_versions=["1.21.1"])

    with django_assert_max_num_queries(20):
        data = api_client.get(
            "/api/v1/mods/p0/install", {"game_version": "1.21.1", "loader": "fabric"}
        ).json()

    assert len(data["items"]) == 6


def resolve(client, items, **target):
    body = {"game_version": "1.21.1", "loader": "fabric", "items": items, **target}
    return client.post("/api/v1/compat/resolve", body, format="json")


def test_resolve_shows_a_conflict_and_who_declared_it(api_client):
    lights = ProjectFactory(slug="sodium-dynamic-lights")
    VersionFactory(project=lights, game_versions=["1.21.1"])
    lamb = ProjectFactory(slug="lambdynamiclights")
    VersionFactory(
        project=lamb, game_versions=["1.21.1"], dependencies=requires(lights, kind="incompatible")
    )

    response = resolve(
        api_client, [{"slug": "lambdynamiclights"}, {"slug": "sodium-dynamic-lights"}]
    )

    assert response.status_code == 200
    assert response.json()["status"] == "errors"
    assert response.json()["conflicts"] == [
        {"a": "lambdynamiclights", "b": "sodium-dynamic-lights", "declared_by": "lambdynamiclights"}
    ]


def test_resolve_takes_a_pinned_version(api_client):
    mod = ProjectFactory(slug="mod")
    VersionFactory(project=mod, game_versions=["1.21.1"], modrinth_version_id="NEW1")
    VersionFactory(project=mod, game_versions=["1.20.1"], modrinth_version_id="OLD1")

    item = resolve(api_client, [{"slug": "mod", "version_id": "OLD1"}]).json()["items"][0]

    assert (item["status"], item["nearest_game_versions"]) == ("pinned_incompatible", ["1.20.1"])


def test_resolve_refuses_unknown_and_too_many_projects(api_client):
    ProjectFactory(slug="known")

    unknown = resolve(api_client, [{"slug": "known"}, {"slug": "nope"}])
    too_many = resolve(api_client, [{"slug": "known"}] * 301)
    bad_loader = resolve(api_client, [{"slug": "known"}], loader="bukkit")

    assert (unknown.status_code, unknown.json()["code"]) == (400, "unknown_projects")
    assert unknown.json()["unknown"] == ["nope"]
    assert (too_many.status_code, too_many.json()["code"]) == (400, "pack_too_large")
    assert bad_loader.status_code == 400


def test_shader_engine_comes_from_the_catalog(api_client):
    iris = ProjectFactory(slug="iris", loaders=["fabric"])
    VersionFactory(project=iris, game_versions=["1.21.1"])
    shader = ProjectFactory(slug="complementary", project_type="shader", loaders=["iris"])
    VersionFactory(project=shader, game_versions=["1.21.1"], loaders=["iris", "optifine"])

    items = resolve(api_client, [{"slug": "complementary"}]).json()["items"]

    assert [(item["project"]["slug"], item["reason"]) for item in items] == [
        ("complementary", "requested"),
        ("iris", "implicit"),
    ]


def test_guest_without_my_game_gets_the_shader_with_its_engine(api_client):
    iris = ProjectFactory(slug="iris", loaders=["fabric"])
    VersionFactory(project=iris, game_versions=["1.21.1"])
    shader = ProjectFactory(
        slug="complementary", project_type="shader", loaders=["iris"], game_versions=["1.21.1"]
    )
    VersionFactory(project=shader, game_versions=["1.21.1"], loaders=["iris", "optifine"])

    data = api_client.get("/api/v1/mods/complementary/install").json()

    assert data["target"] == {"game_version": "1.21.1", "loader": "fabric"}
    assert [item["project"]["slug"] for item in data["items"]] == ["complementary", "iris"]


def test_a_dependency_modrinth_lacks_becomes_unavailable(
    api_client, django_capture_on_commit_callbacks
):
    from apps.compat.services import mark_unavailable

    mod = ProjectFactory(slug="needs-gone")
    VersionFactory(
        project=mod,
        game_versions=["1.21.1"],
        dependencies=[
            {"project_id": "GONE0001", "version_id": None, "dependency_type": "required"}
        ],
    )
    mark_unavailable(["GONE0001"])
    query = {"game_version": "1.21.1", "loader": "fabric"}

    with mock.patch("apps.mods.tasks.import_missing.delay") as delay:
        data = api_client.get("/api/v1/mods/needs-gone/install", query).json()

    assert (data["status"], data["missing"], data["unavailable"]) == ("errors", [], ["GONE0001"])
    delay.assert_not_called()


def test_import_task_marks_what_modrinth_does_not_have():
    from apps.compat.services import _split_unavailable
    from apps.compat.types import Resolution, Target
    from apps.mods import tasks
    from apps.mods.tests.fakes import recorded

    with mock.patch("apps.mods.tasks.ModrinthClient") as factory:
        factory.return_value.__enter__.return_value = recorded()
        with mock.patch("apps.mods.tasks.supported_game_versions", return_value=["1.21.1"]):
            assert tasks.import_missing.delay(["AANobbMI", "NOPE0001"]).get() == 1

    result = Resolution(Target("1.21.1", "fabric"), missing=["NOPE0001"])
    _split_unavailable(result)
    assert (result.missing, result.unavailable) == ([], ["NOPE0001"])


def test_hidden_dependency_is_flagged(api_client):
    hidden = ProjectFactory(slug="hidden-lib", is_hidden=True)
    VersionFactory(project=hidden, game_versions=["1.21.1"])
    mod = ProjectFactory(slug="uses-hidden")
    VersionFactory(project=mod, game_versions=["1.21.1"], dependencies=requires(hidden))

    items = api_client.get(
        "/api/v1/mods/uses-hidden/install", {"game_version": "1.21.1", "loader": "fabric"}
    ).json()["items"]

    assert [(i["project"]["slug"], i["project"]["hidden"]) for i in items] == [
        ("uses-hidden", False),
        ("hidden-lib", True),
    ]


def test_install_is_cached(api_client, sodium_extra, django_assert_max_num_queries):
    query = {"game_version": "1.21.1", "loader": "fabric"}
    first = api_client.get("/api/v1/mods/sodium-extra/install", query).json()

    with django_assert_max_num_queries(3):  # the project itself, game context
        again = api_client.get("/api/v1/mods/sodium-extra/install", query).json()

    assert again == first


def test_resolve_is_throttled_for_everyone(api_client, settings):
    ProjectFactory(slug="known")
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

    with mock.patch.dict(rates, {"compat": "2/min"}):
        codes = [resolve(api_client, [{"slug": "known"}]).status_code for _ in range(3)]

    assert codes == [200, 200, 429]
