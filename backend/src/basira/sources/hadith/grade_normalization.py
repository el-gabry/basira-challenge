from __future__ import annotations

from basira.models.hadith import (
    HadithGradeCategory,
)


def categorize_hadith_grade(
    grade_text: str,
) -> HadithGradeCategory:
    """
    Conservatively map explicit grade wording to a
    broad category.

    Raw source wording remains authoritative.
    Complex scholarly statements intentionally remain
    UNKNOWN rather than being over-interpreted.
    """

    normalized = (
        grade_text
        .strip()
        .casefold()
        .replace("’", "'")
        .replace("‘", "'")
    )

    sahih_prefixes = (
        "sahih",
        "ṣaḥīḥ",
        "authentic",
        "صحيح",
        "صحيحة",
        "صحيحان",
    )

    hasan_prefixes = (
        "hasan",
        "ḥasan",
        "good hadith",
        "حسن",
    )

    daif_prefixes = (
        "daif",
        "da'if",
        "ḍaʿīf",
        "weak hadith",
        "ضعيف",
        "إسناده ضعيف",
    )

    mawdu_prefixes = (
        "mawdu",
        "mawdoo",
        "fabricated",
        "موضوع",
    )

    if normalized.startswith(
        sahih_prefixes
    ):
        return HadithGradeCategory.SAHIH

    if normalized.startswith(
        hasan_prefixes
    ):
        return HadithGradeCategory.HASAN

    if normalized.startswith(
        daif_prefixes
    ):
        return HadithGradeCategory.DAIF

    if normalized.startswith(
        mawdu_prefixes
    ):
        return HadithGradeCategory.MAWDU

    return HadithGradeCategory.UNKNOWN
