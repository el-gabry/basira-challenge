from __future__ import annotations

import pytest

from basira.models.hadith import (
    HadithGradeCategory,
)
from basira.sources.hadith.quranlab.parser import (
    QuranLabHadithParseError,
    QuranLabHadithParser,
)


def _bukhari_row() -> dict[str, object]:
    return {
        "hadith_key": "bukhari:1",
        "urn": 10000001,
        "seq": 1,
        "collection": "bukhari",
        "language": "ar",
        "hadith_number": "1",
        "number_sort": 1,
        "book_number": 1,
        "in_book_number": 1,
        "sunnah_url": (
            "https://sunnah.com/bukhari:1"
        ),
        "text": (
            "حَدَّثَنَا الْحُمَيْدِيُّ  "
            "عَبْدُ اللَّهِ بْنُ الزُّبَيْرِ"
        ),
        "grades": [],
        "n_grades": 0,
        "grade_summary": None,
        "is_muallaq": False,
    }


def _tirmidhi_row() -> dict[str, object]:
    return {
        "hadith_key": "tirmidhi:1",
        "urn": 40000001,
        "seq": 1,
        "collection": "tirmidhi",
        "language": "ar",
        "hadith_number": "1",
        "number_sort": 1,
        "book_number": 1,
        "in_book_number": 1,
        "sunnah_url": (
            "https://sunnah.com/tirmidhi:1"
        ),
        "text": (
            "حَدَّثَنَا قُتَيْبَةُ بْنُ سَعِيدٍ"
        ),
        "grades": [
            {
                "grader": (
                    "Ahmad Muhammad Shakir"
                ),
                "grade": "Sahih",
            },
            {
                "grader": "Al-Albani",
                "grade": "Sahih",
            },
            {
                "grader": "Zubair Ali Zai",
                "grade": (
                    "Sahih - Bukhari And Muslim"
                ),
            },
        ],
        "n_grades": 3,
        "grade_summary": (
            "Ahmad Muhammad Shakir: Sahih; "
            "Al-Albani: Sahih; "
            "Zubair Ali Zai: "
            "Sahih - Bukhari And Muslim"
        ),
        "is_muallaq": False,
    }


def test_parse_bukhari_reference() -> None:
    parser = QuranLabHadithParser()

    record = parser.parse(
        _bukhari_row()
    )

    reference = record.primary_reference

    assert (
        record.record_id
        == "quranlab-hadith:bukhari:1"
    )

    assert reference.collection_id == "bukhari"
    assert reference.hadith_number == "1"
    assert reference.book_number == "1"
    assert reference.in_book_number == "1"
    assert reference.is_muallaq is False


def test_parse_preserves_arabic_text_exactly() -> None:
    row = _bukhari_row()

    parser = QuranLabHadithParser()

    record = parser.parse(row)

    assert (
        record.text_variants[0].arabic_text
        == row["text"]
    )


def test_bukhari_missing_grades_remains_ungraded() -> None:
    record = QuranLabHadithParser().parse(
        _bukhari_row()
    )

    assert record.grade_assessments == ()
    assert not record.has_grading


def test_tirmidhi_preserves_all_grade_attributions() -> None:
    record = QuranLabHadithParser().parse(
        _tirmidhi_row()
    )

    assert len(
        record.grade_assessments
    ) == 3

    assert {
        assessment.grader_name
        for assessment
        in record.grade_assessments
    } == {
        "Ahmad Muhammad Shakir",
        "Al-Albani",
        "Zubair Ali Zai",
    }


def test_grade_wording_is_preserved() -> None:
    record = QuranLabHadithParser().parse(
        _tirmidhi_row()
    )

    zubair = next(
        assessment
        for assessment
        in record.grade_assessments
        if assessment.grader_name
        == "Zubair Ali Zai"
    )

    assert (
        zubair.grade_text
        == "Sahih - Bukhari And Muslim"
    )


def test_explicit_sahih_is_normalized_conservatively() -> None:
    record = QuranLabHadithParser().parse(
        _tirmidhi_row()
    )

    assert all(
        assessment.category
        is HadithGradeCategory.SAHIH
        for assessment
        in record.grade_assessments
    )


def test_grade_count_mismatch_is_rejected() -> None:
    row = _tirmidhi_row()
    row["n_grades"] = 2

    with pytest.raises(
        QuranLabHadithParseError
    ):
        QuranLabHadithParser().parse(
            row
        )


def test_non_arabic_row_is_rejected() -> None:
    row = _bukhari_row()
    row["language"] = "en"

    with pytest.raises(
        QuranLabHadithParseError,
        match="Arabic rows only",
    ):
        QuranLabHadithParser().parse(
            row
        )


def test_parser_does_not_treat_quranlab_as_verified_authority() -> None:
    record = QuranLabHadithParser().parse(
        _tirmidhi_row()
    )

    assert all(
        assessment.source_id
        == "quranlab-hadith"
        for assessment
        in record.grade_assessments
    )
