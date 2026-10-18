import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.accounts.validators import nickname_validators

from .factories import UserFactory

# Nicknames are checked against the BannedWord table too
pytestmark = pytest.mark.django_db


def validate(value: str) -> None:
    for validator in nickname_validators:
        validator(value)


@pytest.mark.parametrize("nickname", ["Steve_UA", "abc", "x" * 24, "Mavka2026", "__init__x"])
def test_valid_nicknames(nickname):
    validate(nickname)


@pytest.mark.parametrize(
    ("nickname", "code"),
    [
        ("ab", "invalid_nickname_length"),
        ("x" * 25, "invalid_nickname_length"),
        ("Стів", "invalid_nickname"),
        ("steve ua", "invalid_nickname"),
        ("steve-ua", "invalid_nickname"),
        ("ADMIN", "reserved_nickname"),
        ("Mojang", "reserved_nickname"),
        ("hit_ler_88", "banned_nickname"),
        ("xX_BlYaT_Xx", "banned_nickname"),
    ],
)
def test_invalid_nicknames(nickname, code):
    with pytest.raises(ValidationError) as error:
        validate(nickname)
    assert error.value.code == code


@pytest.mark.django_db
def test_nickname_is_unique_ignoring_case_in_database():
    UserFactory(nickname="Steve_UA")

    with pytest.raises(IntegrityError):
        UserFactory(nickname="STEVE_ua")
