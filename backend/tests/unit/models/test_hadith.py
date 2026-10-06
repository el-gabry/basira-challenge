from __future__ import annotations

import pytest
from pydantic import ValidationError

from basira.models.hadith import (
    HadithGradeAssessment,
    HadithGradeCategory,
    HadithRecord,
    HadithReference,
    HadithTextVariant,
)


def _reference(
    *,
    source_id: str = "hadith-source",
    hadith_number: str = "1",
) -> HadithReference:
    return HadithReference(
        source_id=source_id,
        collection_id="sahih-example",
        collection_name="Sahih Example",
        hadith_number=hadith_number,
    )


def _variant(
    *,
    source_id: str = "hadith-source",
) -> HadithTextVariant:
    return HadithTextVariant(
        source_id=source_id,
        arabic_text="إنما الأعمال بالنيات",
    )


def test_reference_preserves_source_provenance() -> None:
    reference = _reference()

    assert reference.key == (
        "hadith-source",
        "sahih-example",
        "1",
    )


def test_reference_normalizes_required_metadata() -> None:
    reference = HadithReference(
        source_id="  hadith-source  ",
        collection_id="  collection-a ",
        hadith_number="  42 ",
    )

    assert reference.source_id == "hadith-source"
    assert reference.collection_id == "collection-a"
    assert reference.hadith_number == "42"


def test_translation_requires_provenance() -> None:
    with pytest.raises(
        ValidationError,
        match="translation_source_id",
    ):
        HadithTextVariant(
            source_id="arabic-source",
            arabic_text="نص الحديث",
            english_translation="Hadith text",
        )


def test_translation_source_requires_translation() -> None:
    with pytest.raises(
        ValidationError,
        match="english_translation",
    ):
        HadithTextVariant(
            source_id="arabic-source",
            arabic_text="نص الحديث",
            translation_source_id=(
                "translation-source"
            ),
        )


def test_attributed_translation_is_valid() -> None:
    variant = HadithTextVariant(
        source_id="arabic-source",
        arabic_text="نص الحديث",
        english_translation="Hadith text",
        translation_source_id=(
            "translation-source"
        ),
    )

    assert (
        variant.translation_source_id
        == "translation-source"
    )


def test_grade_requires_named_grader() -> None:
    with pytest.raises(
        ValidationError,
    ):
        HadithGradeAssessment(
            source_id="grading-source",
            grader_name="   ",
            grade_text="صحيح",
            category=HadithGradeCategory.SAHIH,
        )


def test_grade_preserves_raw_wording_and_category() -> None:
    assessment = HadithGradeAssessment(
        source_id="grading-source",
        grader_name="Scholar",
        grade_text="صحيح لغيره",
        category=HadithGradeCategory.SAHIH,
    )

    assert assessment.grade_text == "صحيح لغيره"
    assert (
        assessment.category
        is HadithGradeCategory.SAHIH
    )


def test_record_requires_text_variant() -> None:
    with pytest.raises(
        ValidationError,
    ):
        HadithRecord(
            record_id="record-1",
            primary_reference=_reference(),
            text_variants=(),
        )


def test_record_rejects_duplicate_references() -> None:
    reference = _reference()

    with pytest.raises(
        ValidationError,
        match="references must be unique",
    ):
        HadithRecord(
            record_id="record-1",
            primary_reference=reference,
            alternate_references=(
                reference.model_copy(
                    deep=True
                ),
            ),
            text_variants=(
                _variant(),
            ),
        )


def test_record_can_store_multiple_source_references() -> None:
    record = HadithRecord(
        record_id="record-1",
        primary_reference=_reference(
            source_id="source-a",
            hadith_number="1",
        ),
        alternate_references=(
            _reference(
                source_id="source-b",
                hadith_number="100",
            ),
        ),
        text_variants=(
            _variant(
                source_id="source-a"
            ),
            _variant(
                source_id="source-b"
            ),
        ),
    )

    assert len(record.references) == 2


def test_record_does_not_require_single_absolute_grade() -> None:
    record = HadithRecord(
        record_id="record-1",
        primary_reference=_reference(),
        text_variants=(
            _variant(),
        ),
        grade_assessments=(
            HadithGradeAssessment(
                source_id="grading-source-a",
                grader_name="Scholar A",
                grade_text="صحيح",
                category=(
                    HadithGradeCategory.SAHIH
                ),
            ),
            HadithGradeAssessment(
                source_id="grading-source-b",
                grader_name="Scholar B",
                grade_text="حسن",
                category=(
                    HadithGradeCategory.HASAN
                ),
            ),
        ),
    )

    assert record.has_grading
    assert len(
        record.grade_assessments
    ) == 2


def test_record_without_grade_is_valid() -> None:
    record = HadithRecord(
        record_id="record-1",
        primary_reference=_reference(),
        text_variants=(
            _variant(),
        ),
    )

    assert not record.has_grading


def test_source_ids_include_all_provenance_sources() -> None:
    record = HadithRecord(
        record_id="record-1",
        primary_reference=_reference(
            source_id="reference-source"
        ),
        text_variants=(
            HadithTextVariant(
                source_id="arabic-source",
                arabic_text="نص الحديث",
                english_translation="Hadith text",
                translation_source_id=(
                    "translation-source"
                ),
            ),
        ),
        grade_assessments=(
            HadithGradeAssessment(
                source_id="grading-source",
                grader_name="Scholar",
                grade_text="صحيح",
                category=(
                    HadithGradeCategory.SAHIH
                ),
            ),
        ),
    )

    assert record.source_ids == {
        "reference-source",
        "arabic-source",
        "translation-source",
        "grading-source",
    }

def test_reference_preserves_in_book_number() -> None:
    reference = HadithReference(
        source_id="quranlab-hadith",
        collection_id="bukhari",
        hadith_number="1",
        book_number="1",
        in_book_number="1",
    )

    assert reference.book_number == "1"
    assert reference.in_book_number == "1"


def test_reference_preserves_source_specific_muallaq_status() -> None:
    reference = HadithReference(
        source_id="quranlab-hadith",
        collection_id="bukhari",
        hadith_number="1",
        is_muallaq=False,
    )

    assert reference.is_muallaq is False



def test_arabic_text_is_preserved_exactly() -> None:
    original = "  حَدَّثَنَا   رَسُولُ اللَّهِ\nصلى الله عليه وسلم  "

    variant = HadithTextVariant(
        source_id="source-a",
        arabic_text=original,
    )

    assert variant.arabic_text == original


def test_english_translation_is_preserved_exactly() -> None:
    original = (
        "Narrated by the Companion:\n"
        "The Prophet  said   this."
    )

    variant = HadithTextVariant(
        source_id="arabic-source",
        arabic_text="نص الحديث",
        english_translation=original,
        translation_source_id="english-source",
    )

    assert variant.english_translation == original
