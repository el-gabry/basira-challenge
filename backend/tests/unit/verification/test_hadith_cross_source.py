from __future__ import annotations

import pytest

from basira.models.hadith import (
    HadithGradeAssessment,
    HadithGradeCategory,
    HadithRecord,
    HadithReference,
    HadithTextVariant,
)
from basira.verification.hadith_cross_source import (
    HadithCoverageRelation,
    HadithCrossSourceVerifier,
    HadithGradeRelation,
    HadithTextRelation,
)


def record(
    *,
    source_id: str,
    hadith_number: str = "5457",
    text: str,
    grade_text: str | None = "صحيح",
    category: HadithGradeCategory = (
        HadithGradeCategory.SAHIH
    ),
) -> HadithRecord:
    assessments = ()

    if grade_text is not None:
        assessments = (
            HadithGradeAssessment(
                source_id=source_id,
                grader_name="Attributed grader",
                grade_text=grade_text,
                category=category,
            ),
        )

    return HadithRecord(
        record_id=(
            f"{source_id}:"
            f"{hadith_number}"
        ),
        primary_reference=(
            HadithReference(
                source_id=source_id,
                collection_id="hadeethenc",
                hadith_number=hadith_number,
            )
        ),
        text_variants=(
            HadithTextVariant(
                source_id=source_id,
                arabic_text=text,
            ),
        ),
        grade_assessments=assessments,
    )


def verifier() -> HadithCrossSourceVerifier:
    return HadithCrossSourceVerifier(
        primary_source_id=(
            "hadeethenc-official"
        ),
        secondary_source_id=(
            "quranlab-hadith"
        ),
    )


def test_exact_text_and_grade_match() -> None:
    result = verifier().verify(
        primary=record(
            source_id="hadeethenc-official",
            text="قال رسول الله صلى الله عليه وسلم",
        ),
        secondary=record(
            source_id="quranlab-hadith",
            text="قال رسول الله صلى الله عليه وسلم",
        ),
    )

    assert (
        result.coverage_relation
        is HadithCoverageRelation.SHARED
    )

    assert (
        result.text_relation
        is HadithTextRelation.EXACT
    )

    assert (
        result.grade_relation
        is HadithGradeRelation.MATCH
    )

    assert not result.review_required


def test_real_5457_diacritic_variant() -> None:
    result = verifier().verify(
        primary=record(
            source_id="hadeethenc-official",
            hadith_number="5457",
            text=(
                "فَإِنَّهُم عِبَادَكَ "
                "وَإِنْ تَغْفِرْ لَهُم"
            ),
        ),
        secondary=record(
            source_id="quranlab-hadith",
            hadith_number="5457",
            text=(
                "فَإِنَّهُم عِبَادُكَ "
                "وَإِنْ تَغْفِرْ لَهُم"
            ),
        ),
    )

    assert (
        result.text_relation
        is HadithTextRelation
        .DIACRITIC_VARIANT
    )

    assert (
        result.grade_relation
        is HadithGradeRelation.MATCH
    )

    assert not result.review_required


def test_material_text_variant_requires_review() -> None:
    result = verifier().verify(
        primary=record(
            source_id="hadeethenc-official",
            text="نص الحديث الأول",
        ),
        secondary=record(
            source_id="quranlab-hadith",
            text="نص مختلف",
        ),
    )

    assert (
        result.text_relation
        is HadithTextRelation.TEXT_VARIANT
    )

    assert result.review_required


def test_grade_conflict_requires_review() -> None:
    result = verifier().verify(
        primary=record(
            source_id="hadeethenc-official",
            text="نص الحديث",
            grade_text="صحيح",
            category=(
                HadithGradeCategory.SAHIH
            ),
        ),
        secondary=record(
            source_id="quranlab-hadith",
            text="نص الحديث",
            grade_text="ضعيف",
            category=(
                HadithGradeCategory.DAIF
            ),
        ),
    )

    assert (
        result.grade_relation
        is HadithGradeRelation.CONFLICT
    )

    assert result.review_required


def test_ungraded_source_is_insufficient() -> None:
    result = verifier().verify(
        primary=record(
            source_id="hadeethenc-official",
            text="نص الحديث",
        ),
        secondary=record(
            source_id="quranlab-hadith",
            text="نص الحديث",
            grade_text=None,
        ),
    )

    assert (
        result.grade_relation
        is HadithGradeRelation.INSUFFICIENT
    )

    assert result.review_required


def test_primary_only_record_requires_review() -> None:
    result = verifier().verify(
        primary=record(
            source_id="hadeethenc-official",
            hadith_number="65585",
            text="حديث موجود في الإصدار الرسمي فقط",
        ),
        secondary=None,
    )

    assert (
        result.coverage_relation
        is HadithCoverageRelation.PRIMARY_ONLY
    )

    assert (
        result.text_relation
        is HadithTextRelation.NOT_COMPARABLE
    )

    assert result.review_required


def test_different_references_cannot_be_compared() -> None:
    with pytest.raises(
        ValueError,
        match="different Hadith references",
    ):
        verifier().verify(
            primary=record(
                source_id="hadeethenc-official",
                hadith_number="1",
                text="أ",
            ),
            secondary=record(
                source_id="quranlab-hadith",
                hadith_number="2",
                text="أ",
            ),
        )
