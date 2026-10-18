import pytest

from apps.core.text import slug_from, transliterate


@pytest.mark.parametrize(
    ("text", "latin"),
    [
        ("Їжак і Ягідка", "Yizhak i Yahidka"),
        ("Згода", "Zghoda"),
        ("Щастя", "Shchastia"),
        ("Юрій", "Yurii"),
        ("Київ", "Kyiv"),
        ("Мар'яна", "Mariana"),
        ("CraftUA 2", "CraftUA 2"),
    ],
)
def test_transliteration_follows_the_official_system(text, latin):
    assert transliterate(text) == latin


def test_slugs_are_latin_and_short():
    assert slug_from("Українське виживання 1.21!") == "ukrainske-vyzhyvannia-121"
    assert len(slug_from("Дуже " * 40, max_length=20)) <= 20
