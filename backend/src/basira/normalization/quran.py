from __future__ import annotations

import unicodedata

_ALEF_EQUIVALENTS = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
    }
)


def normalize_quran_search_text(
    text: str,
) -> str:
    """
    Normalize Arabic Quran text for retrieval only.

    This function must never be used to overwrite or modify
    canonical source text.
    """

    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = text.translate(
        _ALEF_EQUIVALENTS
    )

    characters: list[str] = []

    for character in text:
        category = unicodedata.category(
            character
        )

        # Remove Arabic diacritics and Quranic combining marks.
        if category.startswith("M"):
            continue

        # Remove tatweel.
        if character == "\u0640":
            continue

        # Preserve letters and whitespace only.
        # This removes verse numbers, punctuation and Quran symbols
        # from the search representation.
        if category.startswith("L"):
            characters.append(character)
        elif character.isspace():
            characters.append(" ")

    return " ".join(
        "".join(characters).split()
    )