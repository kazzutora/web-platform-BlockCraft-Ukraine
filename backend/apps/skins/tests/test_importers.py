"""MineSkin gallery and skins added by players, on the recorded answers (fixtures: mineskin/)."""

from unittest import mock

import pytest
from PIL import Image

from apps.core import jobs
from apps.core.models import Source
from apps.skins import importers, services
from apps.skins.importers import Incoming, NotASkin, Outcome
from apps.skins.models import Skin
from apps.sources.clients.mineskin import MineSkinNotFoundError
from apps.sources.clients.mojang import PlayerSkin
from apps.sources.models import SyncRun
from apps.sources.runs import SyncCounter
from apps.sources.schemas.mineskin import SkinPage, SkinResponse
from apps.sources.tests.recorded import load

from .factories import SkinFactory, png_bytes, skin_image, skin_png

pytestmark = pytest.mark.django_db


def incoming(**changes) -> Incoming:
    values = {
        "source": Source.MINESKIN,
        "external_id": "ca7a715a18f3471ea1daea83a88890eb",
        "external_url": importers.mineskin_url("ca7a715a18f3471ea1daea83a88890eb"),
        "texture_url": "https://textures.minecraft.net/texture/4f506a",
        "title": "Мавка",
    }
    return Incoming(**{**values, **changes})


# Titles and links


@pytest.mark.parametrize(
    ("name", "ok"),
    [
        ("Мавка", True),
        ("HouseGuest", True),
        (None, False),
        ("x", False),
        ("archmc-d5ecda4", False),
        ("Kes___ARM_LEFT_2", False),
        ("Mangogoy_BODY_1", False),
        ("Mangogoy_BASE", False),
        ("ca7a715a-18f3-471e", False),
        ("m16I.png", False),
        ("archmc-preset-PIG", False),
        ("хуйня", False),
    ],
)
def test_only_real_names_reach_the_catalog(name, ok):
    assert importers.is_title(name) is ok


def test_mineskin_links_and_uuids():
    uuid = "ca7a715a18f3471ea1daea83a88890eb"

    assert importers.mineskin_uuid(f"https://mineskin.org/skins/{uuid}") == uuid
    assert importers.mineskin_uuid("CA7A715A-18F3-471E-A1DA-EA83A88890EB") == uuid
    assert importers.mineskin_uuid("https://mineskin.org/") is None


# One texture, one skin


def test_a_texture_becomes_a_skin_with_model_colour_and_preview():
    skin, outcome = importers.import_texture(skin_png(slim=True), incoming(model=""))

    assert outcome == Outcome.CREATED
    assert (skin.model, skin.color_bucket, skin.title) == ("slim", "red", "Мавка")
    assert skin.texture.name and skin.preview.name and len(skin.texture_hash) == 64


def test_the_same_picture_from_another_source_is_the_same_skin():
    first, _ = importers.import_texture(skin_png(), incoming())
    second, outcome = importers.import_texture(
        skin_png(), incoming(source=Source.MOJANG, external_id="abc", title="Steve")
    )

    assert (second.pk, outcome) == (first.pk, Outcome.DUPLICATE)
    assert Skin.objects.count() == 1


def test_a_lone_arm_is_not_a_skin():
    arm = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    arm.paste((10, 200, 10, 255), (40, 16, 56, 32))

    with pytest.raises(NotASkin):
        importers.import_texture(png_bytes(arm), incoming())


def test_a_picture_of_the_wrong_size_is_not_a_skin():
    with pytest.raises(NotASkin):
        importers.import_texture(png_bytes(Image.new("RGBA", (32, 32))), incoming())


# MineSkin gallery


class FakeMineSkin:
    """The recorded gallery: two pages, each skin answered with the recorded detail."""

    def __init__(self, names: dict[str, str | None] | None = None):
        self.pages = [load("mineskin", "skins_list"), load("mineskin", "skins_list_next")]
        self.detail = load("mineskin", "skin")
        self.names = names or {}
        self.asked: list[str] = []

    def list_skins(self, *, after=None, size=32):
        if after is None:
            return SkinPage.model_validate(self.pages[0])
        if after == self.pages[0]["pagination"]["next"]["after"]:
            return SkinPage.model_validate(self.pages[1])
        return SkinPage.model_validate({"skins": [], "pagination": {"next": {}}})

    def page_rows(self):
        return [row for page in self.pages for row in page["skins"]]

    def get_skin(self, uuid):
        self.asked.append(uuid)
        data = {**self.detail["skin"], "uuid": uuid, "name": self.names.get(uuid, "Мавка")}
        return SkinResponse.model_validate({"skin": data}).skin


class FakeTextures:
    #: Shared by all instances: a different picture for every skin, so none is a duplicate
    count = 0

    def texture(self, url):
        FakeTextures.count += 1
        return png_bytes(skin_image(color=(FakeTextures.count % 256, 120, 40)))


def named_gallery() -> FakeMineSkin:
    fake = FakeMineSkin()
    for row in fake.page_rows():
        row["name"] = f"Скін {row['uuid'][:4]}"
    return fake


def test_sync_imports_named_skins_and_skips_the_rest():
    fake = FakeMineSkin()
    rows = fake.page_rows()
    rows[0]["name"] = "Мавка"
    run = SyncCounter()

    services.sync_mineskin(
        client=fake, textures=FakeTextures(), per_run=50, run=run, progress=lambda m: None
    )

    named = [row for row in rows if importers.is_title(row["name"])]
    assert run.created == len(named) == Skin.objects.count()
    assert fake.asked == [row["uuid"] for row in named]
    assert run.skipped == len(rows) - len(named)
    assert run.failed == 0


def test_sync_stops_at_the_limit_and_the_next_run_skips_what_is_here():
    fake = named_gallery()
    rows = fake.page_rows()

    services.sync_mineskin(
        client=fake, textures=FakeTextures(), per_run=1, run=SyncCounter(), progress=print
    )
    asked = len(fake.asked)
    run = SyncCounter()
    services.sync_mineskin(
        client=fake, textures=FakeTextures(), per_run=50, run=run, progress=print
    )

    assert asked == 1
    assert Skin.objects.count() == len(rows)
    assert (run.unchanged, len(fake.asked)) == (1, len(rows))  # the first one is not asked again


def test_a_picture_already_here_is_skipped_without_asking_mineskin():
    fake = named_gallery()
    row = fake.page_rows()[0]
    SkinFactory(source=Source.MOJANG, texture_url=importers.TEXTURE_URL.format(row["texture"]))

    services.sync_mineskin(
        client=fake, textures=FakeTextures(), per_run=50, run=SyncCounter(), progress=print
    )

    assert row["uuid"] not in fake.asked


def test_sync_task_writes_a_sync_run(settings):
    from apps.skins import tasks

    settings.SYNC_SKINS_PER_RUN = 2
    with (
        mock.patch("apps.skins.tasks.MineSkinClient") as client,
        mock.patch("apps.skins.tasks.MojangClient") as textures,
    ):
        client.return_value.__enter__.return_value = named_gallery()
        textures.return_value.__enter__.return_value = FakeTextures()
        result = tasks.sync_mineskin.delay().get()

    assert result["created"] == 2
    assert SyncRun.objects.get(job="mineskin.gallery").status == "ok"


# A player adds a skin


def player(texture: bytes | None = None, **changes) -> PlayerSkin:
    values = {
        "nickname": "Steve_UA",
        "uuid": "069a79f444e94726a5befca90e38aaf5",
        "model": "classic",
        "texture_png": texture if texture is not None else skin_png(),
        "texture_url": "https://textures.minecraft.net/texture/abc123",
    }
    return PlayerSkin(**{**values, **changes})


def test_a_skin_by_nickname_is_added_with_who_added_it(user):
    with mock.patch("apps.skins.services.mojang.lookup", return_value=player()):
        skin, outcome = services.add_by_nickname(nickname="Steve_UA", user=user)

    assert outcome == Outcome.CREATED
    assert (skin.source, skin.external_id, skin.player_name) == ("mojang", "abc123", "Steve_UA")
    assert skin.added_by == user


@pytest.mark.parametrize(
    ("answer", "code"),
    [(None, "player_not_found"), (player(texture_png=None, texture_url=""), "default_skin")],
)
def test_a_skin_by_nickname_that_cannot_be_added(user, answer, code):
    with (
        mock.patch("apps.skins.services.mojang.lookup", return_value=answer),
        pytest.raises(services.DomainError) as error,
    ):
        services.add_by_nickname(nickname="Nobody", user=user)
    assert error.value.code == code


def test_mojang_rate_limit_is_unavailable_not_an_error(user):
    with (
        mock.patch(
            "apps.skins.services.mojang.lookup", side_effect=services.mojang.MojangError("429")
        ),
        pytest.raises(services.DomainError) as error,
    ):
        services.add_by_nickname(nickname="Steve_UA", user=user)
    assert error.value.code == "source_unavailable"


def test_post_skins_queues_a_job_and_the_job_tells_the_result(
    auth_client, django_capture_on_commit_callbacks
):
    from apps.skins.tasks import import_skin

    with (
        mock.patch("apps.skins.tasks.import_skin.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = auth_client.post("/api/v1/skins", {"nickname": "Steve_UA"}, format="json")
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    with mock.patch("apps.skins.services.mojang.lookup", return_value=player()):
        import_skin(**delay.call_args.kwargs)

    job = auth_client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "done"
    assert job["result"]["id"] == Skin.objects.get().pk


def test_a_mineskin_link_already_here_answers_at_once(auth_client):
    skin = SkinFactory(external_id="ca7a715a18f3471ea1daea83a88890eb")

    response = auth_client.post(
        "/api/v1/skins", {"mineskin": f"https://mineskin.org/skins/{skin.external_id}"}
    )

    assert (response.status_code, response.json()["id"]) == (200, skin.pk)


def test_an_unknown_mineskin_skin_fails_the_job(user):
    from apps.skins.tasks import import_skin

    job = jobs.create("skins.add")
    client = mock.Mock()
    client.get_skin.side_effect = MineSkinNotFoundError("gone")
    with mock.patch("apps.skins.tasks.MineSkinClient") as factory:
        factory.return_value.__enter__.return_value = client
        import_skin(job_id=job["id"], kind="mineskin", value="0" * 32, user_id=user.pk)

    assert jobs.get(job["id"])["error"] == "not_found"


def test_adding_needs_one_of_nickname_or_link(auth_client, api_client):
    assert auth_client.post("/api/v1/skins", {}, format="json").status_code == 400
    assert api_client.post("/api/v1/skins", {"nickname": "Steve"}).status_code == 401


def test_a_player_cannot_add_a_skin_under_a_banned_name(user):
    from apps.moderation.models import BannedWord
    from apps.moderation.words import forget_cache

    BannedWord.objects.create(word="поганець", language="uk")
    forget_cache()

    with pytest.raises(NotASkin, match="bad_name"):
        importers.import_texture(skin_png(), incoming(title="Поганець"), added_by=user)


def test_an_unnamed_mineskin_skin_added_by_a_player_gets_a_neutral_title(user):
    fake = FakeMineSkin(names={"0" * 32: "archmc-d5ecda4"})

    skin, _ = services.import_mineskin(
        client=fake, textures=FakeTextures(), uuid="0" * 32, added_by=user
    )

    assert skin.title == services.UNNAMED


def test_a_hidden_mineskin_skin_is_refused_at_once(auth_client):
    skin = SkinFactory(external_id="ca7a715a18f3471ea1daea83a88890eb", is_hidden=True)

    response = auth_client.post("/api/v1/skins", {"mineskin": skin.external_id})

    assert (response.status_code, response.json()["code"]) == (400, "hidden_skin")
