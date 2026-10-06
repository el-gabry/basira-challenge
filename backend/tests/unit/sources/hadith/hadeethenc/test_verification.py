from __future__ import annotations

from basira.sources.hadith.hadeethenc.models import (
    HadeethEncArabicRow,
    HadeethEncEnglishRow,
    HadeethEncLanguage,
    HadeethEncRelease,
)
from basira.sources.hadith.hadeethenc.verification import (
    HadeethEncConflictType,
    detect_cross_version_grade_conflict,
)

AR_RELEASE = HadeethEncRelease(
    language=HadeethEncLanguage.ARABIC,
    version="v1.7.0",
    last_updated="2025-11-12 00:00:55",
    source_url="https://hadeethenc.com/ar",
    update_check_url=(
        "https://hadeethenc.com/"
        "en/check/ar/v1.7.0"
    ),
)

EN_RELEASE = HadeethEncRelease(
    language=HadeethEncLanguage.ENGLISH,
    version="v1.25.0",
    last_updated="2026-05-10 17:43:35",
    source_url="https://hadeethenc.com/en",
    update_check_url=(
        "https://hadeethenc.com/"
        "en/check/en/v1.25.0"
    ),
)


def arabic_row(
    *,
    grade: str = "ضعيف",
) -> HadeethEncArabicRow:
    return HadeethEncArabicRow(
        id=65065,
        title="عنوان",
        hadith_text="نص الحديث",
        explanation="",
        word_meanings="",
        benefits="",
        grade=grade,
        takhrij="رواه الترمذي",
        link=(
            "https://hadeethenc.com/"
            "ar/browse/hadith/65065"
        ),
    )


def english_row(
    *,
    grade_ar: str = "صحيح",
) -> HadeethEncEnglishRow:
    return HadeethEncEnglishRow(
        id=65065,
        title_ar="عنوان",
        title="Title",
        hadith_text_ar="نص الحديث",
        hadith_text="Hadith text",
        explanation_ar="",
        explanation="",
        benefits_ar="",
        benefits="",
        grade_ar=grade_ar,
        takhrij_ar="رواه الترمذي",
        grade="[Authentic hadith]",
        takhrij="[Narrated by At-Termedhy]",
        lang="en",
        link=(
            "https://hadeethenc.com/"
            "en/browse/hadith/65065"
        ),
    )


def test_detects_cross_version_grade_conflict() -> None:
    conflict = (
        detect_cross_version_grade_conflict(
            arabic_row(),
            english_row(),
            arabic_release=AR_RELEASE,
            english_release=EN_RELEASE,
        )
    )

    assert conflict is not None

    assert (
        conflict.conflict_type
        is HadeethEncConflictType
        .CROSS_VERSION_GRADE_CONFLICT
    )

    assert conflict.hadith_id == 65065
    assert conflict.arabic_value == "ضعيف"

    assert (
        conflict.english_embedded_arabic_value
        == "صحيح"
    )


def test_equal_cross_version_grade_has_no_conflict() -> None:
    conflict = (
        detect_cross_version_grade_conflict(
            arabic_row(
                grade="صحيح"
            ),
            english_row(
                grade_ar="صحيح"
            ),
            arabic_release=AR_RELEASE,
            english_release=EN_RELEASE,
        )
    )

    assert conflict is None
