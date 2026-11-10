"""retarget and guess_target (tech.md 9.5, cases 15–16 of 9.6)."""

from apps.compat.operations import Current, guess_target, retarget
from apps.compat.resolver import resolve
from apps.compat.types import Request, Target

from .builders import MemoryIndex, project, version


def test_15_retarget_splits_kept_changed_dropped_added():
    index = MemoryIndex(
        project("KEEP", version("k1", game=("1.21.1", "26.1"))),
        project(
            "MOVE",
            version("m26", game=("26.1",)),
            version("m121", game=("1.21.1",), requires=("NEW",)),
        ),
        project("GONE", version("g26", game=("26.1",))),
        project("NEW", version("n1", game=("1.21.1",))),
    )
    current = [Current("keep", "k1"), Current("move", "m26"), Current("gone", "g26")]
    after = resolve(
        [Request(index.by_id[name]) for name in ("KEEP", "MOVE", "GONE")],
        Target("1.21.1", "fabric"),
        index,
    )

    diff = retarget(current, after)

    assert (diff.kept, diff.changed, diff.dropped, diff.added) == (
        ["keep"],
        [("move", "m26", "m121")],
        ["gone"],
        ["new"],
    )


def test_16_guess_takes_the_release_most_files_share_and_its_loader():
    files = [
        version("a", game=("1.21", "1.21.1"), loaders=("fabric",)),
        version("b", game=("1.21.1",), loaders=("fabric", "quilt")),
        version("c", game=("1.21.1", "26w14a"), loaders=("fabric",)),
        version("d", game=("1.20.1",), loaders=("forge",)),
        version("rp", game=("1.21.1",), loaders=("minecraft",)),  # not a mod: no vote
    ]

    guess = guess_target(files)

    assert guess.target == Target("1.21.1", "fabric")
    assert (guess.fitting, guess.identified) == (3, 4)


def test_16_guess_needs_mod_files_with_releases():
    assert guess_target([]).target is None
    assert guess_target([version("rp", loaders=("minecraft",))]).target is None
    snapshot_only = guess_target([version("s", game=("26w14a",))])
    assert (snapshot_only.target, snapshot_only.identified) == (None, 1)


def test_16_ties_go_to_the_newer_release():
    files = [version("a", game=("1.20.1",)), version("b", game=("1.21.1",))]

    assert guess_target(files).target == Target("1.21.1", "fabric")
