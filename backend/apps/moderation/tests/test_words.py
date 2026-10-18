import pytest

from apps.core.exceptions import DomainError
from apps.moderation import words
from apps.moderation.models import BannedWord

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "text",
    [
        "ну ти й мудак",
        "ХУЙНЯ якась",
        "пи3да",  # digit for a Cyrillic letter
        "xyйня",  # Latin look-alikes inside a Cyrillic word
        "what the fuck",
        "sh1t happens",
        "f u c k",
        "ти сука",
    ],
)
def test_banned_words_are_found(text):
    assert words.find_banned(text)


@pytest.mark.parametrize(
    "text",
    [
        "Сьогодні дебати про найкращий шейдер",
        "бляха від ремінця",
        "Сучасний сервер з мінііграми",  # «сука» is checked as a whole word only
        "Classic survival, no griefing",
        "",
    ],
)
def test_ordinary_text_passes(text):
    assert words.find_banned(text) is None


def test_check_names_the_field():
    with pytest.raises(DomainError) as error:
        words.check(title="Нормальна назва", description="повний мудак")

    assert error.value.code == "banned_word"
    assert list(error.value.fields) == ["description"]


def test_new_words_apply_without_waiting_for_the_cache():
    assert words.find_banned("кринж") is None

    BannedWord.objects.create(word="Кринж", language="uk")

    assert words.find_banned("суцільний кринжатина")
