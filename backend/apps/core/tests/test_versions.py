import pytest

from apps.core.versions import is_release, latest_release, nearest_versions, version_key


def test_versions_sort_numerically_across_both_schemes():
    versions = ["1.21.4", "26.1", "1.21.11", "1.8.9", "26.3"]

    assert sorted(versions, key=version_key) == ["1.8.9", "1.21.4", "1.21.11", "26.1", "26.3"]


@pytest.mark.parametrize(
    ("version", "expected"),
    [("26.3", True), ("1.21.11", True), ("1.21", True), ("26w14a", False), ("26.3-rc-2", False)],
)
def test_is_release(version, expected):
    assert is_release(version) is expected


def test_latest_release_ignores_snapshots():
    assert latest_release(["1.21.1", "26.3", "26w14a", "26.4-pre1"]) == "26.3"
    assert latest_release([]) == ""


def test_nearest_versions_prefer_the_same_line():
    available = ["1.21.1", "1.21.4", "1.20.6", "26.1", "1.21.3"]

    assert nearest_versions("1.21.3", available) == ["1.21.4", "1.21.1", "1.20.6"]
    assert nearest_versions("26.3", available)[0] == "26.1"
