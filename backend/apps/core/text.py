"""Text helpers: Ukrainian transliteration for URLs (the official 2010 system)."""

import re

from django.utils.text import slugify

_LETTERS = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie",
    "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ь": "", "ю": "iu",
    "я": "ia", "'": "", "’": "", "ʼ": "",
    # Letters that are not Ukrainian but show up in server names
    "ы": "y", "э": "e", "ъ": "", "ё": "io",
}  # fmt: skip
# At the start of a word these letters are spelled differently
_WORD_START = {"є": "ye", "ї": "yi", "й": "y", "ю": "yu", "я": "ya"}
# Apostrophes stay inside the word: «Мар'яна» → «Mariana», not «Maryana»
_WORD = re.compile(r"[\w'’ʼ]+|[^\w'’ʼ]+")


def transliterate(text: str) -> str:
    """«Їжак і Ягідка» → «Yizhak i Yahidka»; other characters pass through."""
    result = []
    for chunk in _WORD.findall(text):
        previous = ""
        for index, char in enumerate(chunk):
            lower = char.lower()
            if lower == "г" and previous == "з":
                latin = "gh"  # «зг» → «zgh», so it does not read as «zh»
            elif index == 0 and lower in _WORD_START:
                latin = _WORD_START[lower]
            else:
                latin = _LETTERS.get(lower)
            if latin is None:
                result.append(char)
            else:
                result.append(latin.capitalize() if char.isupper() else latin)
            previous = lower
    return "".join(result)


def slug_from(text: str, *, max_length: int = 60) -> str:
    return slugify(transliterate(text))[:max_length].strip("-")
