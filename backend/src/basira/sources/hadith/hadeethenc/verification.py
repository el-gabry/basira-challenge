from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.sources.hadith.hadeethenc.models import (
    HadeethEncArabicRow,
    HadeethEncEnglishRow,
    HadeethEncRelease,
)


class HadeethEncConflictType(StrEnum):
    CROSS_VERSION_GRADE_CONFLICT = (
        "cross_version_grade_conflict"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class HadeethEncSourceConflict:
    conflict_type: HadeethEncConflictType
    hadith_id: int

    arabic_release_version: str
    english_release_version: str

    arabic_value: str
    english_embedded_arabic_value: str


def detect_cross_version_grade_conflict(
    arabic: HadeethEncArabicRow,
    english: HadeethEncEnglishRow,
    *,
    arabic_release: HadeethEncRelease,
    english_release: HadeethEncRelease,
) -> HadeethEncSourceConflict | None:
    """
    Detect disagreement between the official Arabic
    release grade and the Arabic grade embedded in a
    different-language HadeethEnc release.

    Comparison is deliberately exact. Source wording
    is never silently normalized or reconciled.
    """

    if arabic.id != english.id:
        raise ValueError(
            "Cannot compare different HadeethEnc IDs."
        )

    if (
        arabic.grade is None
        or english.grade_ar is None
    ):
        return None

    if arabic.grade == english.grade_ar:
        return None

    return HadeethEncSourceConflict(
        conflict_type=(
            HadeethEncConflictType
            .CROSS_VERSION_GRADE_CONFLICT
        ),
        hadith_id=arabic.id,
        arabic_release_version=(
            arabic_release.version
        ),
        english_release_version=(
            english_release.version
        ),
        arabic_value=arabic.grade,
        english_embedded_arabic_value=(
            english.grade_ar
        ),
    )
