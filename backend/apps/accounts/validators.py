import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from apps.moderation import words

NICKNAME_MIN_LENGTH = 3
NICKNAME_MAX_LENGTH = 24
NICKNAME_PATTERN = r"^[a-zA-Z0-9_]+$"

# Names that would impersonate the team or Minecraft itself, or clash with routes.
# The BannedWord list (moderation) applies on top of this.
RESERVED_NICKNAMES = frozenset(
    {
        "admin", "administrator", "moderator", "mod", "support", "help", "staff", "system",
        "root", "official", "blockcraft", "blockcraftua", "mojang", "microsoft", "minecraft",
        "notch", "jeb", "me", "settings", "login", "logout", "register", "welcome", "api",
        "null", "undefined", "anonymous", "guest", "user",
    }
)  # fmt: skip

# Unambiguous roots of slurs and obscenities (UA / RU / EN, transliterated) that may not
# appear anywhere in a nickname. Short roots are left out: they hit ordinary names.
BANNED_FRAGMENTS = (
    "hitler", "nazi", "fuck", "shit", "nigger", "nigga", "faggot", "porn",
    "pidor", "pidar", "pizd", "blyad", "blyat", "yebat", "mudak", "zalupa", "gandon",
    "shluha", "shlyuha",
)  # fmt: skip

validate_nickname_format = RegexValidator(
    regex=NICKNAME_PATTERN,
    message="Нік може містити лише латинські літери, цифри та «_».",
    code="invalid_nickname",
)


def validate_nickname_length(value: str) -> None:
    if not NICKNAME_MIN_LENGTH <= len(value) <= NICKNAME_MAX_LENGTH:
        raise ValidationError(
            f"Нік має бути від {NICKNAME_MIN_LENGTH} до {NICKNAME_MAX_LENGTH} символів.",
            code="invalid_nickname_length",
        )


def validate_nickname_allowed(value: str) -> None:
    normalized = value.lower()
    if normalized in RESERVED_NICKNAMES:
        raise ValidationError("Цей нік зарезервовано. Обери інший.", code="reserved_nickname")
    squashed = re.sub(r"[_0-9]", "", normalized)
    if any(fragment in squashed for fragment in BANNED_FRAGMENTS) or words.find_banned(squashed):
        raise ValidationError("Нік містить недопустиме слово.", code="banned_nickname")


nickname_validators = [
    validate_nickname_format,
    validate_nickname_length,
    validate_nickname_allowed,
]
