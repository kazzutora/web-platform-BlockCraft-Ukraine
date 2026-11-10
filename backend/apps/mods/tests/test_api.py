from unittest import mock

import pytest

from apps.library.models import Download
from apps.mods.models import ProjectType, ProjectVersion

from .factories import CategoryFactory, ProjectFactory, VersionFactory

pytestmark = pytest.mark.django_db


def slugs(response) -> list[str]:
    return [item["slug"] for item in response.json()["results"]]


def test_catalog_lists_only_published_most_downloaded_first(api_client):
    ProjectFactory(slug="small", modrinth_downloads=10)
    ProjectFactory(slug="big", modrinth_downloads=10_000)
    ProjectFactory(slug="waiting", is_hidden=True)
    ProjectFactory(slug="hidden", is_hidden=True)

    response = api_client.get("/api/v1/mods")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert slugs(response) == ["big", "small"]


def test_filters_combine(api_client):
    optimization = CategoryFactory(slug="optimization")
    utility = CategoryFactory(slug="utility")
    ProjectFactory(
        slug="match", loaders=["fabric"], game_versions=["26.3"], categories=[optimization, utility]
    )
    ProjectFactory(
        slug="forge-only", loaders=["forge"], game_versions=["26.3"], categories=[optimization]
    )
    ProjectFactory(
        slug="old", loaders=["fabric"], game_versions=["1.20.1"], categories=[optimization]
    )
    ProjectFactory(
        slug="one-category", loaders=["fabric"], game_versions=["26.3"], categories=[utility]
    )

    response = api_client.get(
        "/api/v1/mods",
        {
            "type": "mod",
            "game_version": "26.3",
            "loader": "fabric",
            "category": "optimization,utility",
        },
    )

    assert slugs(response) == ["match"]


def test_loader_filter_keeps_shaders_and_resource_packs(api_client):
    ProjectFactory(slug="shader", project_type=ProjectType.SHADER, loaders=["iris"])
    ProjectFactory(slug="forge-mod", loaders=["forge"])

    assert slugs(api_client.get("/api/v1/mods", {"loader": "fabric"})) == ["shader"]


def test_gpu_load_search_and_sorting(api_client):
    ProjectFactory(
        slug="light-shader", project_type=ProjectType.SHADER, gpu_load="light", title="Soft Light"
    )
    ProjectFactory(
        slug="heavy-shader", project_type=ProjectType.SHADER, gpu_load="heavy", title="Ultra"
    )
    ProjectFactory(slug="sodium", title="Sodium", summary_uk="Більше кадрів", score=4.9)

    assert slugs(api_client.get("/api/v1/mods", {"gpu_load": "light"})) == ["light-shader"]
    assert slugs(api_client.get("/api/v1/mods", {"q": "кадрів"})) == ["sodium"]
    assert slugs(api_client.get("/api/v1/mods", {"sort": "top"}))[0] == "sodium"
    assert api_client.get("/api/v1/mods", {"sort": "random"}).status_code == 400


def test_page_size_is_capped(api_client):
    for _ in range(3):
        ProjectFactory()

    response = api_client.get("/api/v1/mods", {"page_size": 2})
    assert len(response.json()["results"]) == 2
    assert response.json()["next"]


def test_catalog_has_no_n_plus_one(api_client, django_assert_max_num_queries):
    category = CategoryFactory()
    for _ in range(10):
        ProjectFactory(categories=[category])

    with django_assert_max_num_queries(3):
        response = api_client.get("/api/v1/mods")
    assert len(response.json()["results"]) == 10


def test_card_shows_ukrainian_summary_and_latest_release(api_client):
    ProjectFactory(
        summary="English", summary_uk="Українською", game_versions=["1.21.1", "26.3", "26w14a"]
    )

    card = api_client.get("/api/v1/mods").json()["results"][0]
    assert card["summary"] == "Українською"
    assert card["latest_game_version"] == "26.3"


def test_detail_includes_description_and_translation_flag(api_client):
    ProjectFactory(slug="sodium", body_html="<p>Hi</p>")

    response = api_client.get("/api/v1/mods/sodium")

    assert response.status_code == 200
    assert response.json()["body_html"] == "<p>Hi</p>"
    assert response.json()["needs_translation"] is True
    assert response.json()["source"] == {
        "name": "Modrinth",
        "url": "https://modrinth.com/mod/sodium",
    }


def test_detail_of_unpublished_project_is_404(api_client):
    ProjectFactory(slug="waiting", is_hidden=True)

    assert api_client.get("/api/v1/mods/waiting").status_code == 404


def test_versions_recommend_a_file_and_list_dependencies(api_client):
    sodium = ProjectFactory(slug="sodium", external_id="AANobbMI")
    iris = ProjectFactory(slug="iris")
    VersionFactory(
        project=iris,
        modrinth_version_id="IRIS26",
        dependencies=[
            {"project_id": "AANobbMI", "dependency_type": "required"},
            {"project_id": "UNKNOWN1", "dependency_type": "optional"},
        ],
    )
    VersionFactory(project=sodium)

    data = api_client.get(
        "/api/v1/mods/iris/versions", {"game_version": "26.3", "loader": "fabric"}
    ).json()

    assert data["recommended"]["id"] == "IRIS26"
    assert data["dependencies"][0]["project"]["slug"] == "sodium"
    assert data["dependencies"][1]["project"] is None
    assert data["nearest_game_versions"] == []


def test_versions_suggest_nearest_game_versions_when_nothing_fits(api_client):
    project = ProjectFactory(slug="sodium")
    VersionFactory(project=project, game_versions=["1.21.1"])

    data = api_client.get(
        "/api/v1/mods/sodium/versions", {"game_version": "1.21.4", "loader": "fabric"}
    ).json()

    assert data["recommended"] is None
    assert data["nearest_game_versions"] == ["1.21.1"]


def test_download_redirects_counts_and_records_for_signed_in_users(api_client, auth_client, user):
    project = ProjectFactory(slug="sodium")
    version = VersionFactory(project=project)

    guest = api_client.get(
        "/api/v1/mods/sodium/download", {"game_version": "26.3", "loader": "fabric"}
    )
    signed = auth_client.get(
        "/api/v1/mods/sodium/download", {"game_version": "26.3", "loader": "fabric"}
    )

    assert guest.status_code == signed.status_code == 302
    assert guest["Location"] == version.file_url
    project.refresh_from_db()
    assert project.downloads_count == 2
    download = Download.objects.get()
    assert (download.user, download.version, download.game_version, download.loader) == (
        user,
        version,
        "26.3",
        "fabric",
    )


def test_download_of_a_specific_version(api_client):
    project = ProjectFactory(slug="sodium")
    VersionFactory(project=project)
    old = VersionFactory(project=project, modrinth_version_id="OLD00001", game_versions=["1.20.1"])

    response = api_client.get("/api/v1/mods/sodium/download", {"version": "OLD00001"})

    assert response["Location"] == old.file_url


def test_download_without_a_matching_file_explains_and_suggests(api_client):
    project = ProjectFactory(slug="sodium")
    VersionFactory(project=project, game_versions=["1.21.1"], loaders=["fabric"])

    response = api_client.get(
        "/api/v1/mods/sodium/download", {"game_version": "26.3", "loader": "fabric"}
    )

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "no_version"
    assert "26.3 · Fabric" in body["detail"]
    assert body["nearest_game_versions"] == ["1.21.1"]
    assert ProjectVersion.objects.count() == 1


def test_import_requires_sign_in(api_client):
    response = api_client.post("/api/v1/mods/import", {"url": "sodium"}, format="json")

    assert response.status_code == 401


@pytest.mark.parametrize(
    "url",
    [
        "https://modrinth.com/mod/lithium",
        "modrinth.com/shader/lithium/",
        "https://modrinth.com/datapack/lithium",
        "https://www.modrinth.com/project/Lithium?tab=versions",
        "lithium",
    ],
)
def test_import_queues_a_job_by_link_or_slug(
    auth_client, api_client, user, url, django_capture_on_commit_callbacks
):
    with (
        mock.patch("apps.mods.tasks.import_project.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = auth_client.post("/api/v1/mods/import", {"url": url}, format="json")

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    delay.assert_called_once_with(job_id=job_id, slug="lithium", user_id=user.pk)
    job = api_client.get(f"/api/v1/jobs/{job_id}").json()
    assert (job["status"], job["kind"], job["result"]) == ("queued", "mods.import", None)


def test_import_of_a_known_project_answers_with_its_slug(auth_client):
    sodium = ProjectFactory(slug="sodium")

    with mock.patch("apps.mods.tasks.import_project.delay") as delay:
        response = auth_client.post(
            "/api/v1/mods/import", {"url": "https://modrinth.com/mod/sodium"}, format="json"
        )

    assert response.status_code == 200
    assert response.json() == {"job_id": None, "slug": "sodium", "title": sodium.title}
    delay.assert_not_called()


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("https://curseforge.com/minecraft/mc-mods/jei", "invalid"),
        ("https://modrinth.com/modpack/fabulously-optimized", "is_modpack"),
        ("hidden-one", "hidden_project"),
    ],
)
def test_import_refuses_other_links_modpacks_and_hidden_projects(auth_client, url, code):
    ProjectFactory(slug="hidden-one", is_hidden=True)

    with mock.patch("apps.mods.tasks.import_project.delay") as delay:
        response = auth_client.post("/api/v1/mods/import", {"url": url}, format="json")

    assert response.status_code == 400
    assert response.json()["code"] == code
    assert list(response.json()["fields"]) == ["url"]
    delay.assert_not_called()


@pytest.mark.parametrize("job_id", ["not-a-uuid", "8a4f2a8e-36a4-4c2e-9d55-2a3a9c1f0c11"])
def test_unknown_job_is_404(api_client, job_id):
    assert api_client.get(f"/api/v1/jobs/{job_id}").status_code == 404


def test_categories_by_type(api_client):
    CategoryFactory(slug="optimization", project_type=ProjectType.MOD, name_uk="Оптимізація")
    CategoryFactory(slug="low", project_type=ProjectType.SHADER, name_uk="Слабкий ПК")

    response = api_client.get("/api/v1/categories", {"type": "shader"})

    assert response.json() == [
        {"slug": "low", "name": "Слабкий ПК", "project_type": "shader", "header": "categories"}
    ]


def test_similar_projects_share_categories(api_client):
    optimization = CategoryFactory(slug="optimization")
    ProjectFactory(slug="sodium", categories=[optimization])
    ProjectFactory(slug="lithium", categories=[optimization])
    ProjectFactory(slug="jei")

    assert [p["slug"] for p in api_client.get("/api/v1/mods/sodium/similar").json()] == ["lithium"]


def test_datapack_tab_includes_mods_that_ship_a_datapack(api_client):
    ProjectFactory(slug="mysticmons", project_type=ProjectType.DATAPACK, loaders=["datapack"])
    ProjectFactory(slug="terralith", loaders=["datapack", "fabric"])
    ProjectFactory(slug="sodium", loaders=["fabric"])

    tab = slugs(api_client.get("/api/v1/mods", {"type": "datapack", "all": "1"}))

    assert sorted(tab) == ["mysticmons", "terralith"]


@pytest.fixture
def my_game(api_client, game_versions):
    api_client.cookies["bc_game"] = "1.21.1:fabric"
    ProjectFactory(slug="fits", loaders=["fabric"], game_versions=["1.21.1"])
    ProjectFactory(slug="forge", loaders=["forge"], game_versions=["1.21.1"])
    ProjectFactory(slug="old", loaders=["fabric"], game_versions=["1.20.1"])
    return api_client


def test_catalog_defaults_to_my_game_and_all_turns_it_off(my_game):
    assert slugs(my_game.get("/api/v1/mods")) == ["fits"]
    assert sorted(slugs(my_game.get("/api/v1/mods", {"all": "1"}))) == ["fits", "forge", "old"]
    # A parameter in the query wins over «Моя гра», even an empty one
    assert sorted(slugs(my_game.get("/api/v1/mods", {"loader": ""}))) == ["fits", "forge"]
    assert slugs(my_game.get("/api/v1/mods", {"game_version": "1.20.1"})) == ["old"]


def test_cards_say_whether_they_fit_my_game(my_game, api_client):
    cards = my_game.get("/api/v1/mods", {"all": "1"}).json()["results"]

    assert {card["slug"]: card["fits_my_game"] for card in cards} == {
        "fits": True,
        "forge": False,
        "old": False,
    }
    api_client.cookies.clear()
    assert {card["fits_my_game"] for card in api_client.get("/api/v1/mods").json()["results"]} == {
        None
    }


def test_guest_cache_is_separate_for_each_game(my_game, api_client):
    assert slugs(my_game.get("/api/v1/mods")) == ["fits"]

    api_client.cookies["bc_game"] = "1.20.1:fabric"

    assert slugs(api_client.get("/api/v1/mods")) == ["old"]


def test_vanilla_game_keeps_mods_that_ship_a_datapack(api_client):
    ProjectFactory(slug="terralith", loaders=["datapack", "fabric"])
    ProjectFactory(slug="sodium", loaders=["fabric"])
    ProjectFactory(slug="shader", project_type=ProjectType.SHADER, loaders=["iris"])

    tab = slugs(api_client.get("/api/v1/mods", {"loader": "vanilla"}))

    assert sorted(tab) == ["shader", "terralith"]
