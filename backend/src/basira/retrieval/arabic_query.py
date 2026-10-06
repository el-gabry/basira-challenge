from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

_WHITESPACE_RE = re.compile(r"\s+")


class ArabicDialect(StrEnum):
    MSA = "msa"
    EGYPTIAN = "egyptian"
    GULF = "gulf"
    LEVANTINE = "levantine"
    MAGHREBI = "maghrebi"
    UNKNOWN = "unknown"


@dataclass(
    frozen=True,
    slots=True,
)
class ArabicQuery:
    """
    Search/query representation only.

    The original user text is preserved exactly.
    None of these normalized forms may replace
    canonical Quran/Hadith source text.
    """

    original_text: str
    search_text: str
    intent_text: str
    dialect: ArabicDialect


_DIALECT_MARKERS: dict[
    ArabicDialect,
    frozenset[str],
] = {
    ArabicDialect.EGYPTIAN: frozenset(
        {
            "ايه",
            "ليه",
            "ازاي",
            "مش",
            "ده",
            "دي",
            "عايز",
            "عايزة",
        }
    ),
    ArabicDialect.GULF: frozenset(
        {
            "وش",
            "شلون",
            "مو",
            "هال",
            "هذي",
            "كذا",
        }
    ),
    ArabicDialect.LEVANTINE: frozenset(
        {
            "شو",
            "ليش",
            "كيفك",
            "هاد",
            "هاي",
            "مو",
        }
    ),
    ArabicDialect.MAGHREBI: frozenset(
        {
            "واش",
            "علاش",
            "شنو",
            "بزاف",
        }
    ),
}


_DIALECT_REPLACEMENTS = {
    # Egyptian
    "ايه": "ما",
    "ليه": "لماذا",
    "ازاي": "كيف",
    "مش": "ليس",
    "ده": "هذا",
    "دي": "هذه",
    # Gulf
    "وش": "ما",
    "شلون": "كيف",
    "مو": "ليس",
    "هذي": "هذه",
    "كذا": "هكذا",
    # Levantine
    "شو": "ما",
    "ليش": "لماذا",
    "هاد": "هذا",
    "هاي": "هذه",
    # Maghrebi
    "واش": "ما",
    "علاش": "لماذا",
    "شنو": "ما",
}


_ALEF_TRANSLATION = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
    }
)


def normalize_arabic_search_text(
    value: str,
) -> str:
    """
    Conservative search normalization.

    - preserves letters/content
    - strips combining marks
    - removes tatweel
    - normalizes common Alef forms
    - normalizes whitespace/punctuation

    Never use this as canonical display text.
    """

    text = unicodedata.normalize(
        "NFKC",
        value,
    )

    text = text.translate(
        _ALEF_TRANSLATION
    )

    result: list[str] = []

    for character in text:
        if (
            unicodedata.category(character)
            == "Mn"
        ):
            continue

        if character == "\u0640":
            continue

        if (
            character.isalnum()
            or character.isspace()
        ):
            result.append(
                character.casefold()
            )
            continue

        if unicodedata.category(
            character
        ).startswith(
            ("P", "S")
        ):
            result.append(" ")
            continue

        result.append(
            character
        )

    return _WHITESPACE_RE.sub(
        " ",
        "".join(result),
    ).strip()


def detect_arabic_dialect(
    value: str,
) -> ArabicDialect:
    """
    Conservative lexical hint only.

    UNKNOWN is preferred when evidence is weak.
    This is not a demographic inference about
    the user.
    """

    normalized = (
        normalize_arabic_search_text(
            value
        )
    )

    tokens = set(
        normalized.split()
    )

    scores = {
        dialect: len(
            tokens & markers
        )
        for dialect, markers
        in _DIALECT_MARKERS.items()
    }

    if not scores:
        return ArabicDialect.UNKNOWN

    best_score = max(
        scores.values()
    )

    if best_score == 0:
        return ArabicDialect.UNKNOWN

    winners = [
        dialect
        for dialect, score
        in scores.items()
        if score == best_score
    ]

    if len(winners) != 1:
        return ArabicDialect.UNKNOWN

    return winners[0]


def normalize_arabic_intent_text(
    value: str,
) -> str:
    normalized = (
        normalize_arabic_search_text(
            value
        )
    )

    tokens = normalized.split()

    expanded: list[str] = []

    for token in tokens:
        replacement = (
            _DIALECT_REPLACEMENTS.get(
                token
            )
        )

        if replacement is not None:
            expanded.append(
                replacement
            )
            continue

        # Gulf demonstrative prefix:
        # "هالحديث" -> "هذا الحديث"
        # Used only for intent understanding.
        if (
            token.startswith("هال")
            and len(token) > 3
        ):
            remainder = token[3:]

            expanded.extend(
                [
                    "هذا",
                    f"ال{remainder}",
                ]
            )
            continue

        if token == "صح":
            expanded.append(
                "صحيح"
            )
            continue

        expanded.append(token)

    return " ".join(
        expanded
    )


def build_arabic_query(
    value: str,
) -> ArabicQuery:
    if not value.strip():
        raise ValueError(
            "Arabic query must not be blank."
        )

    return ArabicQuery(
        original_text=value,
        search_text=(
            normalize_arabic_search_text(
                value
            )
        ),
        intent_text=(
            normalize_arabic_intent_text(
                value
            )
        ),
        dialect=(
            detect_arabic_dialect(
                value
            )
        ),
    )
