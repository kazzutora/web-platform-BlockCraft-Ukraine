"""Engine cases from tech.md 9.6 (1–14); 15–17 (retarget, identify, export) come with R4."""

import pytest

from apps.compat import rules
from apps.compat.resolver import (
    MAX_PROJECTS,
    TooManyProjects,
    candidates,
    pick_version,
    resolve,
)
from apps.compat.types import Dependency, ItemStatus, Reason, Request, Status, Target

from .builders import MemoryIndex, project, version

FABRIC = Target("1.21.1", "fabric")


def run(index: MemoryIndex, *wanted, target: Target = FABRIC):
    requests = [
        Request(index.by_id[item])
        if isinstance(item, str)
        else Request(index.by_id[item[0]], item[1])
        for item in wanted
    ]
    return resolve(requests, target, index)


# 1–3: one project


def test_1_release_is_picked():
    index = MemoryIndex(project("A", version("a1"), version("a2", day=5)))

    result = run(index, "A")

    assert result.status == Status.OK
    assert result.items[0].version.id == "a2"
    assert result.items[0].reason == Reason.REQUESTED


def test_release_wins_over_newer_beta():
    index = MemoryIndex(project("A", version("a1"), version("a2", kind="beta", day=9)))

    assert run(index, "A").items[0].version.id == "a1"


def test_2_only_beta_is_picked_with_a_warning():
    index = MemoryIndex(project("A", version("a1", kind="beta"), version("a0", kind="alpha")))

    result = run(index, "A")

    assert result.items[0].version.id == "a1"
    assert result.status == Status.WARNINGS
    assert [warning.code for warning in result.warnings] == ["beta_only"]


def test_3_no_version_lists_the_nearest_game_versions():
    index = MemoryIndex(
        project(
            "A",
            version("a1", game=("1.21.1", "1.21")),
            version("a2", game=("1.20.1",)),
            version("a3", game=("26.1",), loaders=("forge",)),
            version("snap", game=("26w14a",)),
        )
    )

    result = run(index, "A", target=Target("26.1", "fabric"))

    item = result.items[0]
    assert (item.version, item.status) == (None, ItemStatus.NO_VERSION)
    assert item.nearest_game_versions == ("1.21.1", "1.21", "1.20.1")
    assert result.status == Status.ERRORS


# 4–8: dependencies


def test_4_required_dependency_is_added_with_its_reason():
    index = MemoryIndex(
        project("EXTRA", version("e1", requires=("SODIUM",))),
        project("SODIUM", version("s1")),
    )

    result = run(index, "EXTRA")

    sodium = result.item("sodium")
    assert (sodium.reason, sodium.required_by) == (Reason.DEPENDENCY, ["extra"])
    assert result.status == Status.OK


def test_5_chain_is_followed_one_level_per_index_call():
    index = MemoryIndex(
        project("A", version("a1", requires=("B",))),
        project("B", version("b1", requires=("C",))),
        project("C", version("c1")),
    )

    result = run(index, "A")

    assert [item.project.slug for item in result.items] == ["a", "b", "c"]
    assert result.item("c").required_by == ["b"]
    assert index.calls == 2  # B's level, then C's


def test_6_cycle_does_not_hang():
    index = MemoryIndex(
        project("A", version("a1", requires=("B",))),
        project("B", version("b1", requires=("A",))),
    )

    result = run(index, "A")

    assert len(result.items) == 2
    assert result.item("a").required_by == ["b"]


def test_shared_dependency_is_installed_once_and_knows_both_dependants():
    index = MemoryIndex(
        project("A", version("a1", requires=("API",))),
        project("B", version("b1", requires=("API",))),
        project("API", version("api1")),
    )

    result = run(index, "A", "B")

    assert sorted(result.item("api").required_by) == ["a", "b"]
    assert len(result.items) == 3


def test_7_both_requested_and_one_forbids_the_other():
    index = MemoryIndex(
        project("A", version("a1", forbids=("B",))),
        project("B", version("b1")),
    )

    result = run(index, "A", "B")

    assert result.status == Status.ERRORS
    assert [(c.a, c.b, c.declared_by) for c in result.conflicts] == [("a", "b", "a")]


def test_8_forbidden_project_comes_as_a_dependency():
    index = MemoryIndex(
        project("A", version("a1", forbids=("B",))),
        project("C", version("c1", requires=("B",))),
        project("B", version("b1")),
    )

    result = run(index, "A", "C")

    assert [(c.a, c.b) for c in result.conflicts] == [("a", "b")]


def test_forbidding_something_absent_is_fine_and_optional_is_suggested():
    index = MemoryIndex(
        project("A", version("a1", forbids=("B",), optional=("OPT", "C"), embedded=("EMB",))),
        project("C", version("c1")),
    )

    result = run(index, "A", "C")

    assert result.status == Status.OK
    assert [(s.project, s.suggested_by) for s in result.suggestions] == [("OPT", "a")]
    assert result.missing == []


# 9: pinned versions


def test_9_pinned_version_that_does_not_fit_the_target():
    index = MemoryIndex(project("A", version("a1"), version("old", game=("1.20.1",))))

    assert run(index, ("A", "a1")).items[0].version.id == "a1"
    item = run(index, ("A", "old")).items[0]
    assert (item.version, item.status) == (None, ItemStatus.PINNED_INCOMPATIBLE)
    assert item.nearest_game_versions == ("1.20.1",)


def test_dependency_pinned_to_a_file_for_another_game_falls_back_with_a_warning():
    index = MemoryIndex(
        project("A", version("a1", requires=("B",), pins={"B": "b-old"})),
        project("B", version("b1"), version("b-old", game=("1.20.1",))),
    )

    result = run(index, "A")

    assert result.item("b").version.id == "b1"
    assert [warning.code for warning in result.warnings] == ["version_mismatch"]


def test_dependency_pinned_to_another_version_than_the_chosen_one():
    index = MemoryIndex(
        project("A", version("a1", requires=("B",), pins={"B": "b0"})),
        project("B", version("b1", day=2), version("b0")),
    )

    result = run(index, "B", "A")

    assert result.item("b").version.id == "b1"
    assert result.warnings[0].code == "version_mismatch"
    assert result.warnings[0].params == {"project": "b", "required_by": "a"}


# 10: shader engines


def shader_index():
    return MemoryIndex(
        project("SHADER", version("sh1", loaders=("iris", "optifine")), kind="shader"),
        project("IRIS", version("ir1", loaders=("fabric", "quilt", "neoforge"))),
        project("OCULUS", version("oc1", loaders=("forge", "neoforge"))),
    )


@pytest.mark.parametrize(
    ("loader", "engine"),
    [("fabric", "iris"), ("quilt", "iris"), ("neoforge", "iris"), ("forge", "oculus")],
)
def test_10_shader_brings_its_engine(loader, engine):
    result = run(shader_index(), "SHADER", target=Target("1.21.1", loader))

    item = result.item(engine)
    assert (item.reason, item.required_by) == (Reason.IMPLICIT, ["shader"])
    assert result.status == Status.OK


def test_optifine_only_shader_asks_for_a_manual_step():
    index = MemoryIndex(project("SH", version("s1", loaders=("optifine",)), kind="shader"))

    result = run(index, "SH")

    assert [warning.code for warning in result.warnings] == ["optifine_manual"]
    assert len(result.items) == 1


def test_canvas_shader_on_fabric_brings_canvas_which_we_may_not_have_yet():
    index = MemoryIndex(project("SH", version("s1", loaders=("canvas",)), kind="shader"))

    assert run(index, "SH").missing == ["canvas"]
    assert run(index, "SH", target=Target("1.21.1", "forge")).items[0].status == (
        ItemStatus.NO_VERSION
    )


def test_vanilla_shader_needs_nothing():
    index = MemoryIndex(project("SH", version("s1", loaders=("vanilla",)), kind="shader"))

    for loader in ("vanilla", "fabric"):
        result = run(index, "SH", target=Target("1.21.1", loader))
        assert (result.status, len(result.items)) == (Status.OK, 1)


def test_iris_shader_in_a_vanilla_game_is_an_optifine_step():
    result = run(shader_index(), "SHADER", target=Target("1.21.1", "vanilla"))

    assert [warning.code for warning in result.warnings] == ["optifine_manual"]


# 11–12, 14: loaders


@pytest.mark.parametrize("loader", ["fabric", "forge", "vanilla"])
def test_11_resource_pack_ignores_the_game_loader(loader):
    index = MemoryIndex(
        project("RP", version("r1", loaders=("minecraft",)), kind="resourcepack"),
        project("RP2", version("r2", loaders=("vanilla",)), kind="resourcepack", slug="rp2"),
    )

    result = run(index, "RP", "RP2", target=Target("1.21.1", loader))

    assert result.status == Status.OK


@pytest.mark.parametrize(
    ("target", "picked"),
    [
        (Target("1.21.1", "quilt"), "fab"),
        (Target("1.20.1", "neoforge"), "frg"),
        (Target("1.21.1", "neoforge"), None),
        (Target("1.21.1", "forge"), "frg"),
    ],
)
def test_12_quilt_takes_fabric_and_neoforge_takes_forge_only_on_1_20_1(target, picked):
    index = MemoryIndex(
        project(
            "A",
            version("fab", game=("1.20.1", "1.21.1"), loaders=("fabric",)),
            version("frg", game=("1.20.1", "1.21.1"), loaders=("forge",)),
        )
    )

    version_ = run(index, "A", target=target).items[0].version
    assert (version_.id if version_ else None) == picked


def test_13_unknown_dependency_makes_the_result_incomplete():
    index = MemoryIndex(project("A", version("a1", requires=("FAPI", "FAPI"))))

    result = run(index, "A")

    assert result.status == Status.INCOMPLETE
    assert result.missing == ["FAPI"]


def test_14_mod_in_a_vanilla_game_needs_a_loader_unless_it_ships_a_datapack():
    index = MemoryIndex(
        project("MOD", version("m1")),
        project(
            "TERRA",
            version("t-fabric", loaders=("fabric",), day=3),
            version("t-pack", loaders=("datapack",)),
        ),
    )

    result = run(index, "MOD", "TERRA", target=Target("1.21.1", "vanilla"))

    assert result.item("mod").status == ItemStatus.MOD_NEEDS_LOADER
    assert result.item("terra").version.id == "t-pack"


def test_datapack_takes_only_datapack_files():
    index = MemoryIndex(
        project("DP", version("d1", loaders=("datapack",)), kind="datapack"),
    )

    assert candidates(index.by_id["DP"], Target("1.21.1", "forge"))[0].id == "d1"


def test_limit_of_projects():
    index = MemoryIndex(*(project(f"P{n}", version(f"v{n}")) for n in range(MAX_PROJECTS + 1)))

    with pytest.raises(TooManyProjects):
        run(index, *index.by_id)


def test_pick_version_alone():
    sodium = project("S", version("s1"))

    assert pick_version(sodium, FABRIC).version.id == "s1"
    assert rules.needs_loader(Target("1.21.1", "vanilla"), "mod")


def test_dependency_named_only_by_its_version_is_found_and_pinned():
    index = MemoryIndex(
        project("A", version("a1", requires=())),
        project("B", version("b1", day=3), version("b0")),
    )
    a = index.by_id["A"]
    a_version = a.versions[0]
    pinned = type(a_version)(
        **{
            **a_version.__dict__,
            "dependencies": (Dependency(None, "b0", "required"),),
        }
    )
    index.by_id["A"] = type(a)(**{**a.__dict__, "versions": (pinned,)})

    result = run(index, "A")

    assert result.item("b").version.id == "b0"
    assert result.item("b").required_by == ["a"]


def test_dependency_with_an_unknown_version_only_warns():
    index = MemoryIndex(project("A", version("a1")))
    a = index.by_id["A"]
    broken = type(a.versions[0])(
        **{**a.versions[0].__dict__, "dependencies": (Dependency(None, "GONE", "required"),)}
    )
    index.by_id["A"] = type(a)(**{**a.__dict__, "versions": (broken,)})

    result = run(index, "A")

    assert [(w.code, w.params) for w in result.warnings] == [
        ("unknown_dependency", {"required_by": "a"})
    ]


def test_mutual_ban_is_one_conflict_and_a_project_without_a_file_clashes_with_nothing():
    index = MemoryIndex(
        project("A", version("a1", forbids=("B",))),
        project("B", version("b1", forbids=("A",))),
        project("C", version("c1", forbids=("D",))),
        project("D", version("d1", game=("1.20.1",))),
    )

    result = run(index, "A", "B", "C", "D")

    assert [(c.a, c.b) for c in result.conflicts] == [("a", "b")]


def test_unavailable_dependencies_are_errors_not_waiting():
    index = MemoryIndex(project("A", version("a1")))
    result = run(index, "A")
    result.unavailable = ["GONE"]

    assert result.status == Status.ERRORS


def test_a_dependency_of_another_loader_on_a_multi_loader_file_is_skipped():
    index = MemoryIndex(
        project("TERRA", version("t1", loaders=("fabric", "neoforge"), requires=("KFF", "API"))),
        project("KFF", version("k1", loaders=("neoforge",))),  # Kotlin for Forge
        project("API", version("a1", loaders=("fabric",))),
    )

    result = run(index, "TERRA")

    assert [item.project.slug for item in result.items] == ["terra", "api"]
    assert result.status == Status.OK
    neo = run(index, "TERRA", target=Target("1.21.1", "neoforge"))
    # And the other way round: Fabric API is not needed on NeoForge
    assert [item.project.slug for item in neo.items] == ["terra", "kff"]


def test_a_single_loader_file_keeps_a_dependency_without_files():
    index = MemoryIndex(
        project("A", version("a1", requires=("LIB",))),
        project("LIB", version("l1", loaders=("forge",))),
    )

    assert run(index, "A").item("lib").status == ItemStatus.NO_VERSION


def test_a_shipped_modpack_keeps_its_pinned_files_and_adds_nothing():
    index = MemoryIndex(
        project(
            "A",
            version("a-old", game=("1.21",), requires=("API",)),
            version("a-new", game=("1.21.1",)),
        ),
        project("API", version("api1")),
        project("B", version("b1", forbids=("A",))),
    )
    requests = [Request(index.by_id["A"], "a-old"), Request(index.by_id["B"], "b1")]

    result = resolve(requests, FABRIC, index, trust_pins=True)

    assert result.item("a").version.id == "a-old"
    assert [w.code for w in result.warnings] == ["pinned_other_game"]
    assert result.item("api") is None
    assert [(c.a, c.b) for c in result.conflicts] == [("b", "a")]


def test_a_shipped_modpack_may_be_bigger_than_a_request():
    index = MemoryIndex(*(project(f"P{n}", version(f"v{n}")) for n in range(MAX_PROJECTS + 5)))
    requests = [Request(item) for item in index.by_id.values()]

    with pytest.raises(TooManyProjects):
        resolve(requests, FABRIC, index)
    assert len(resolve(requests, FABRIC, index, limit=1000).items) == MAX_PROJECTS + 5


def test_a_ban_of_one_version_does_not_hit_another():
    index = MemoryIndex(project("ADDON", version("x1")), project("BASE", version("base2", day=5)))
    addon = index.by_id["ADDON"]
    banning = type(addon.versions[0])(
        **{
            **addon.versions[0].__dict__,
            "dependencies": (Dependency("BASE", "base1", "incompatible"),),
        }
    )
    index.by_id["ADDON"] = type(addon)(**{**addon.__dict__, "versions": (banning,)})

    assert run(index, "ADDON", "BASE").conflicts == []
    assert len(run(index, "ADDON", ("BASE", "base2")).conflicts) == 0
    index.by_id["BASE"] = project("BASE", version("base1"))
    assert [(c.a, c.b) for c in run(index, "ADDON", "BASE").conflicts] == [("addon", "base")]
