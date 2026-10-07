from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol


class _QuranVerse(Protocol):
    surah_number: int
    ayah_number: int
    text_search: str
    surah_name_ar: str | None
    surah_name_en: str | None


class QuranRepositoryProtocol(Protocol):
    def get(
        self,
        surah_number: int,
        ayah_number: int,
    ) -> _QuranVerse | None: ...


@dataclass(
    frozen=True,
    slots=True,
)
class CanonicalQuranPoint:
    surah: int
    ayah: int

    @property
    def reference(self) -> str:
        return f"{self.surah}:{self.ayah}"


_ARABIC_DIACRITICS = re.compile(
    r"[\u0610-\u061a\u064b-\u065f\u0670"
    r"\u06d6-\u06ed]"
)

_NON_WORD = re.compile(
    r"[^\w\u0600-\u06ff]+",
    re.UNICODE,
)

_CANONICAL_REFERENCE = re.compile(
    r"(?<!\d)"
    r"(?P<surah>\d{1,3})"
    r"\s*:\s*"
    r"(?P<ayah>\d{1,3})"
    r"(?!\d)"
)

_ARABIC_AYAH_NUMBER = re.compile(
    r"(?:الاية|اية)"
    r"\s*"
    r"(?P<ayah>\d{1,3})"
)

_ENGLISH_AYAH_NUMBER = re.compile(
    r"(?:ayah|verse)"
    r"\s*"
    r"(?P<ayah>\d{1,3})"
)

_DISCOVERY_SCAFFOLDING = (
    "ما معنى قوله تعالى",
    "ما معني قوله تعالى",
    "ما تفسير قوله تعالى",
    "ما معنى قول الله تعالى",
    "ما معني قول الله تعالى",
    "ما تفسير قول الله تعالى",
    "ما معنى",
    "ما معني",
    "ما تفسير",
    "فسر قوله تعالى",
    "فسر قول الله تعالى",
    "تفسير قوله تعالى",
    "تفسير قول الله تعالى",
    "what is the meaning of",
    "what does this verse mean",
    "what does the verse mean",
    "what does",
    "explain the verse",
    "explain",
    "interpret the verse",
)


def _normalize(
    value: str,
) -> str:
    text = unicodedata.normalize(
        "NFKC",
        value,
    )

    text = _ARABIC_DIACRITICS.sub(
        "",
        text,
    )

    text = (
        text
        .replace("ـ", "")
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ٱ", "ا")
        .replace("ى", "ي")
    )

    # Unicode-aware punctuation removal.
    #
    # Do not preserve the whole Arabic Unicode block:
    # that range also contains punctuation such as "؟"،
    # which can break exact Surah-name boundaries.
    #
    # Identity normalization keeps only letters, numbers
    # and whitespace. It grants no evidence authority.
    text = "".join(
        char
        if (
            char.isalnum()
            or char.isspace()
        )
        else " "
        for char in text.casefold()
    )

    return " ".join(
        text.split()
    )


def _valid_point(
    *,
    repository: QuranRepositoryProtocol,
    surah: int,
    ayah: int,
) -> CanonicalQuranPoint | None:
    if not 1 <= surah <= 114:
        return None

    if ayah < 1:
        return None

    verse = repository.get(
        surah,
        ayah,
    )

    if verse is None:
        return None

    return CanonicalQuranPoint(
        surah=surah,
        ayah=ayah,
    )


def _first_verse(
    repository: QuranRepositoryProtocol,
    surah: int,
) -> _QuranVerse | None:
    return repository.get(
        surah,
        1,
    )


def _resolve_named_surah(
    *,
    normalized_question: str,
    repository: QuranRepositoryProtocol,
) -> int | None:
    matches: set[int] = set()

    for surah in range(
        1,
        115,
    ):
        verse = _first_verse(
            repository,
            surah,
        )

        if verse is None:
            continue

        names = (
            getattr(
                verse,
                "surah_name_ar",
                None,
            ),
            getattr(
                verse,
                "surah_name_en",
                None,
            ),
        )

        for raw_name in names:
            if not raw_name:
                continue

            name = _normalize(
                raw_name
            )

            if not name:
                continue

            # Match the complete Surah name, never a
            # substring of another Surah name.
            #
            # Example:
            #   "سورة الحجرات"
            # must NOT also resolve as
            #   "سورة الحجر".
            arabic_pattern = (
                rf"(?:^|\s)"
                rf"سورة\s+{re.escape(name)}"
                rf"(?:\s|$)"
            )

            english_pattern = (
                rf"(?:^|\s)"
                rf"surah\s+{re.escape(name)}"
                rf"(?:\s|$)"
            )

            if (
                re.search(
                    arabic_pattern,
                    normalized_question,
                )
                or re.search(
                    english_pattern,
                    normalized_question,
                )
            ):
                matches.add(
                    surah
                )

    if len(matches) != 1:
        return None

    return next(
        iter(matches)
    )


def _explicit_reference(
    *,
    question: str,
    repository: QuranRepositoryProtocol,
) -> CanonicalQuranPoint | None:
    raw_identity_text = unicodedata.normalize(
        "NFKC",
        question,
    )

    canonical = (
        _CANONICAL_REFERENCE
        .search(raw_identity_text)
    )

    normalized = _normalize(
        question
    )

    if canonical is not None:
        return _valid_point(
            repository=repository,
            surah=int(
                canonical.group(
                    "surah"
                )
            ),
            ayah=int(
                canonical.group(
                    "ayah"
                )
            ),
        )

    ayah_match = (
        _ARABIC_AYAH_NUMBER
        .search(normalized)
        or
        _ENGLISH_AYAH_NUMBER
        .search(normalized)
    )

    if ayah_match is None:
        return None

    surah = _resolve_named_surah(
        normalized_question=normalized,
        repository=repository,
    )

    if surah is None:
        return None

    return _valid_point(
        repository=repository,
        surah=surah,
        ayah=int(
            ayah_match.group(
                "ayah"
            )
        ),
    )



def resolve_explicit_quran_point(
    *,
    question: str,
    repository: QuranRepositoryProtocol,
) -> CanonicalQuranPoint | None:
    """
    Resolve only an explicit Quran identity.

    Supported identity forms include:
    - canonical numeric reference such as 2:255;
    - explicit Surah name + ayah number.

    This function performs identity resolution only.
    It grants no evidence or publication authority.

    Partial Quran text discovery is deliberately excluded
    from this path so a HARD anchor cannot be created from
    general discovery wording.
    """

    return _explicit_reference(
        question=question,
        repository=repository,
    )

def _discovery_tokens(
    question: str,
) -> tuple[str, ...]:
    normalized = _normalize(
        question
    )

    for phrase in (
        _DISCOVERY_SCAFFOLDING
    ):
        normalized_phrase = (
            _normalize(phrase)
        )

        normalized = (
            normalized.replace(
                normalized_phrase,
                " ",
            )
        )

    tokens = tuple(
        token
        for token in normalized.split()
        if token
        not in {
            "القران",
            "الكريم",
            "الاية",
            "اية",
            "سورة",
            "quran",
            "quranic",
            "ayah",
            "verse",
            "surah",
        }
    )

    return tokens


def _iter_repository_verses(
    repository: QuranRepositoryProtocol,
):
    for surah in range(
        1,
        115,
    ):
        first = repository.get(
            surah,
            1,
        )

        if first is None:
            continue

        yield first

        # Longest Quran surah has fewer than 300 ayat.
        # Repository lookup is deterministic and local.
        for ayah in range(
            2,
            301,
        ):
            verse = repository.get(
                surah,
                ayah,
            )

            if verse is None:
                continue

            yield verse


def _partial_text_reference(
    *,
    question: str,
    repository: QuranRepositoryProtocol,
) -> CanonicalQuranPoint | None:
    tokens = _discovery_tokens(
        question
    )

    if len(tokens) < 3:
        return None

    candidates: list[
        tuple[
            int,
            int,
            int,
        ]
    ] = []

    max_width = min(
        len(tokens),
        10,
    )

    for width in range(
        max_width,
        2,
        -1,
    ):
        phrases = tuple(
            " ".join(
                tokens[
                    start:
                    start + width
                ]
            )
            for start in range(
                0,
                len(tokens)
                - width
                + 1,
            )
        )

        matches: set[
            tuple[int, int]
        ] = set()

        for verse in (
            _iter_repository_verses(
                repository
            )
        ):
            verse_text = _normalize(
                getattr(
                    verse,
                    "text_search",
                    "",
                )
            )

            if not verse_text:
                continue

            padded_verse = (
                f" {verse_text} "
            )

            if any(
                f" {phrase} "
                in padded_verse
                for phrase in phrases
                if phrase
            ):
                matches.add(
                    (
                        int(
                            verse.surah_number
                        ),
                        int(
                            verse.ayah_number
                        ),
                    )
                )

        if len(matches) == 1:
            surah, ayah = next(
                iter(matches)
            )

            candidates.append(
                (
                    width,
                    surah,
                    ayah,
                )
            )

            break

        if len(matches) > 1:
            # Ambiguous Quran identity:
            # fail closed rather than selecting by rank.
            return None

    if not candidates:
        return None

    _, surah, ayah = max(
        candidates
    )

    return CanonicalQuranPoint(
        surah=surah,
        ayah=ayah,
    )


def resolve_canonical_quran_point(
    *,
    question: str,
    repository: QuranRepositoryProtocol,
) -> CanonicalQuranPoint | None:
    """
    Resolve user wording to one canonical Quran coordinate.

    This component grants NO evidence authority.

    It may only produce a deterministic Quran identity.
    The resulting coordinate must still be fetched through
    the existing governed Quran / Tafsir source adapters.
    """

    explicit = _explicit_reference(
        question=question,
        repository=repository,
    )

    if explicit is not None:
        return explicit

    return _partial_text_reference(
        question=question,
        repository=repository,
    )
