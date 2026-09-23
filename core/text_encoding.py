from __future__ import annotations

import unicodedata

# Letters that Unicode decomposition does not reduce to a plain Latin letter.
EXPLICIT_TRANSLITERATIONS: dict[str, str] = {
    "ø": "o",
    "Ø": "O",
    "æ": "ae",
    "Æ": "AE",
    "ß": "ss",
    "đ": "d",
    "Đ": "D",
    "ł": "l",
    "Ł": "L",
    "þ": "th",
    "Þ": "TH",
    "ð": "d",
    "Ð": "D",
    "œ": "oe",
    "Œ": "OE",
}


def make_encodable(text: str, encoding: str) -> tuple[str, bool]:
    """Return text that `encoding` can write, and whether a character had no replacement.

    Characters the encoding already supports (Cyrillic, typographic quotes, №, ...)
    are kept as they are; others are transliterated to Latin, and "?" is the last resort.
    """
    result: list[str] = []
    used_fallback = False
    for char in text:
        if _can_encode(char, encoding):
            result.append(char)
            continue

        replacement = EXPLICIT_TRANSLITERATIONS.get(char)
        if replacement is None:
            decomposed = unicodedata.normalize("NFKD", char)
            replacement = "".join(c for c in decomposed if not unicodedata.combining(c))

        if replacement and _can_encode(replacement, encoding):
            result.append(replacement)
        else:
            result.append("?")
            used_fallback = True

    return "".join(result), used_fallback


def _can_encode(text: str, encoding: str) -> bool:
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True
