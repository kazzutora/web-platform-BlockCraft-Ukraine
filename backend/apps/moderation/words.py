"""Profanity filter for titles, bios, comments and reviews (BannedWord, UA / RU / EN)."""

import re

from django.core.cache import cache

from apps.core.exceptions import DomainError

CACHE_KEY = "moderation:banned-words"
CACHE_TTL = 5 * 60
MESSAGE = "Текст містить слово, яке в нас заборонене. Переформулюй, будь ласка."

# «f*ck», «sh1t», «пи3да»: digits and symbols that stand in for letters
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "@": "a", "$": "s", "!": "i"})
# Latin letters that look like Cyrillic ones inside a Cyrillic word («xyй», «сyка»)
_LOOKALIKE = str.maketrans(
    {"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у", "k": "к", "i": "і"}
)
_CYRILLIC_LEET = str.maketrans({"3": "з", "0": "о", "6": "б", "4": "ч", "@": "а"})
_WORD = re.compile(r"[^\W\d_]+")
_CYRILLIC = re.compile(r"[а-яіїєґё]")


def _words() -> tuple[frozenset[str], tuple[str, ...]]:
    """(whole words, roots), cached: every comment checks them."""
    cached = cache.get(CACHE_KEY)
    if cached is None:
        from .models import BannedWord

        rows = list(BannedWord.objects.values_list("word", "is_root"))
        cached = (
            frozenset(word for word, is_root in rows if not is_root),
            tuple(word for word, is_root in rows if is_root),
        )
        cache.set(CACHE_KEY, cached, CACHE_TTL)
    return cached


def forget_cache() -> None:
    cache.delete(CACHE_KEY)


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    tokens = set()
    # Digits read as Latin letters («sh1t») and as Cyrillic ones («пи3да»)
    for variant in (lowered.translate(_LEET), lowered.translate(_CYRILLIC_LEET)):
        for token in _WORD.findall(variant):
            tokens.add(token)
            if _CYRILLIC.search(token):
                tokens.add(token.translate(_LOOKALIKE))
        # «f u c k», «х.у.й»: single letters glued back together
        singles = re.findall(r"(?:\b[^\W\d_]\b[\s.\-_*]*){3,}", variant)
        tokens.update(re.sub(r"[^\w]|_", "", chunk) for chunk in singles)
    return tokens


def find_banned(text: str) -> str | None:
    """The first banned word or root found in the text, or None."""
    if not text:
        return None
    whole, roots = _words()
    for token in _tokens(text):
        if token in whole or any(root in token for root in roots):
            return token
    return None


def check(**fields: str) -> None:
    """`check(title=..., description=...)`: DomainError on the first field with a banned word."""
    for name, text in fields.items():
        if text and find_banned(text):
            raise DomainError(code="banned_word", message=MESSAGE, fields={name: [MESSAGE]})
