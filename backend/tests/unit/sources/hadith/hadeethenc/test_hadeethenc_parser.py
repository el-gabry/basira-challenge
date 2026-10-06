from __future__ import annotations

import pytest

from basira.models.hadith import (
    HadithGradeCategory,
)
from basira.sources.hadith.hadeethenc.models import (
    HadeethEncLanguage,
    HadeethEncRelease,
)
from basira.sources.hadith.hadeethenc.parser import (
    HadeethEncOfficialParser,
    HadeethEncParseError,
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


def ar_row() -> dict[str, object]:
    return {
        "id": 1751,
        "title": "اغسلنها ثلاثا",
        "hadith_text": (
            "عَنْ أُمِّ عَطِيَّةَ"
        ),
        "explanation": "شرح",
        "word_meanings": "",
        "benefits": "",
        "grade": "صحيح",
        "takhrij": "متفق عليه",
        "link": (
            "https://hadeethenc.com/"
            "ar/browse/hadith/1751"
        ),
    }


def en_row() -> dict[str, object]:
    return {
        "id": 1751,
        "title_ar": "اغسلنها ثلاثا",
        "title": "Wash her",
        "hadith_text_ar": (
            "عَنْ أُمِّ عَطِيَّةَ"
        ),
        "hadith_text": (
            "Umm Atiyyah reported..."
        ),
        "explanation_ar": "شرح",
        "explanation": "Explanation",
        "benefits_ar": "",
        "benefits": "",
        "grade_ar": "صحيح",
        "takhrij_ar": "متفق عليه",
        "grade": "[Authentic]",
        "takhrij": "[Agreed upon]",
        "lang": "en",
        "link": (
            "https://hadeethenc.com/"
            "en/browse/hadith/1751"
        ),
    }


def test_parse_official_arabic() -> None:
    record = (
        HadeethEncOfficialParser()
        .parse(
            ar_row(),
            arabic_release=AR_RELEASE,
        )
    )

    assert (
        record.record_id
        == "hadeethenc-official:1751"
    )

    assert (
        record.text_variants[0]
        .arabic_text
        == "عَنْ أُمِّ عَطِيَّةَ"
    )

    assessment = (
        record.grade_assessments[0]
    )

    assert assessment.grade_text == "صحيح"

    assert (
        assessment.category
        is HadithGradeCategory.SAHIH
    )


def test_parse_official_bilingual_record() -> None:
    record = (
        HadeethEncOfficialParser()
        .parse(
            ar_row(),
            arabic_release=AR_RELEASE,
            english_payload=en_row(),
            english_release=EN_RELEASE,
        )
    )

    assert (
        record.text_variants[0]
        .english_translation
        == "Umm Atiyyah reported..."
    )

    assert (
        "official_ar_release=v1.7.0"
        in record.notes
    )

    assert (
        "official_en_release=v1.25.0"
        in record.notes
    )


def test_english_does_not_create_second_grade() -> None:
    record = (
        HadeethEncOfficialParser()
        .parse(
            ar_row(),
            arabic_release=AR_RELEASE,
            english_payload=en_row(),
            english_release=EN_RELEASE,
        )
    )

    assert (
        len(record.grade_assessments)
        == 1
    )


def test_mismatched_language_ids_are_rejected() -> None:
    english = en_row()
    english["id"] = 9999

    with pytest.raises(
        HadeethEncParseError,
        match="IDs differ",
    ):
        HadeethEncOfficialParser().parse(
            ar_row(),
            arabic_release=AR_RELEASE,
            english_payload=english,
            english_release=EN_RELEASE,
        )


def test_parser_preserves_cross_version_grade_conflict() -> None:
    arabic = ar_row()
    english = en_row()

    arabic["id"] = 65065
    arabic["grade"] = "ضعيف"

    english["id"] = 65065
    english["grade_ar"] = "صحيح"
    english["grade"] = "[Authentic hadith]"

    record = HadeethEncOfficialParser().parse(
        arabic,
        arabic_release=AR_RELEASE,
        english_payload=english,
        english_release=EN_RELEASE,
    )

    assert record.notes is not None

    assert (
        "cross_version_grade_conflict"
        in record.notes
    )

    assert "v1.7.0" in record.notes
    assert "v1.25.0" in record.notes
    assert "'ضعيف'" in record.notes
    assert "'صحيح'" in record.notes

    assert len(
        record.grade_assessments
    ) == 2

    first, second = (
        record.grade_assessments
    )

    assert first.grade_text == "ضعيف"

    assert (
        first.category
        is HadithGradeCategory.DAIF
    )

    assert (
        first.source_reference
        == "hadeethenc:65065"
    )

    assert second.grade_text == "صحيح"

    assert (
        second.category
        is HadithGradeCategory.SAHIH
    )

    assert (
        second.source_reference
        == (
            "hadeethenc:65065:"
            "official-en:v1.25.0:"
            "grade_ar"
        )
    )

    assert (
        str(second.source_url)
        == (
            "https://hadeethenc.com/"
            "en/browse/hadith/1751"
        )
    )

    assert (
        first.conflict_group
        == second.conflict_group
        == (
            "hadeethenc:65065:"
            "grade:cross-version"
        )
    )

    assert (
        first.conflict_type
        == second.conflict_type
        == "cross_version_grade_conflict"
    )
