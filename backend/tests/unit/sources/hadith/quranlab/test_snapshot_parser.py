from __future__ import annotations

import pytest

from basira.models.hadith import (
    HadithGradeCategory,
)
from basira.sources.hadith.quranlab.parser import (
    QuranLabHadeethEncParser,
    QuranLabHadithParseError,
    QuranLabSingleGradeParser,
    QuranLabSnapshotParser,
)


def _ahmad_row() -> dict[str, object]:
    return {
        "hadith_key": "ahmad:1",
        "urn": 80000001,
        "seq": 1,
        "collection": "ahmad",
        "hadith_number": "1",
        "number_sort": 1,
        "language": "ar",
        "text": "حدثنا عبد الله بن نمير",
        "grade": None,
        "grader": None,
        "grade_source": None,
        "is_muallaq": False,
    }


def _hadeethenc_ar() -> dict[str, object]:
    return {
        "hadith_key": "hadeethenc:1751",
        "hadeethenc_id": 1751,
        "collection": "hadeethenc",
        "language": "ar",
        "title": "اغسلنها ثلاثا",
        "text": "عَنْ أُمِّ عَطِيَّةَ",
        "intro": "عَنْ أُمِّ عَطِيَّةَ",
        "grade": "صحيح",
        "grader": (
            "HadeethEnc "
            "(IslamHouse / Saudi MoIA) "
            "editorial board"
        ),
        "grade_source": (
            "HadeethEnc.com "
            "(IslamHouse / Saudi Ministry "
            "of Islamic Affairs)"
        ),
        "attribution_text": "متفق عليه",
        "explanation": "شرح الحديث",
    }


def _hadeethenc_en() -> dict[str, object]:
    return {
        "hadith_key": "hadeethenc:1751",
        "hadeethenc_id": 1751,
        "collection": "hadeethenc",
        "language": "en",
        "title": "Wash her three times",
        "text": "Umm Atiyyah reported...",
        "intro": "Umm Atiyyah reported:",
        "grade": "Authentic",
        "grader": (
            "HadeethEnc "
            "(IslamHouse / Saudi MoIA) "
            "editorial board"
        ),
        "grade_source": (
            "HadeethEnc.com "
            "(IslamHouse / Saudi Ministry "
            "of Islamic Affairs)"
        ),
        "attribution_text": "Agreed upon",
        "explanation": "Hadith explanation",
    }


def test_ahmad_ungraded_row_remains_ungraded() -> None:
    record = QuranLabSingleGradeParser().parse(
        _ahmad_row()
    )

    assert record.grade_assessments == ()
    assert not record.has_grading


def test_hadeethenc_arabic_is_primary() -> None:
    record = QuranLabHadeethEncParser().parse(
        _hadeethenc_ar()
    )

    assert (
        record.record_id
        == "quranlab-hadith:hadeethenc:1751"
    )

    assert (
        record.text_variants[0].arabic_text
        == "عَنْ أُمِّ عَطِيَّةَ"
    )

    assert (
        record.text_variants[0]
        .english_translation
        is None
    )


def test_hadeethenc_english_is_joined_to_arabic() -> None:
    record = QuranLabHadeethEncParser().parse(
        _hadeethenc_ar(),
        english_payload=_hadeethenc_en(),
    )

    variant = record.text_variants[0]

    assert (
        variant.english_translation
        == "Umm Atiyyah reported..."
    )


def test_hadeethenc_grade_is_attributed() -> None:
    record = QuranLabHadeethEncParser().parse(
        _hadeethenc_ar()
    )

    assessment = (
        record.grade_assessments[0]
    )

    assert assessment.grade_text == "صحيح"
    assert (
        assessment.category
        is HadithGradeCategory.SAHIH
    )


def test_hadeethenc_pair_requires_same_key() -> None:
    english = _hadeethenc_en()
    english["hadith_key"] = (
        "hadeethenc:9999"
    )

    with pytest.raises(
        QuranLabHadithParseError,
        match="hadith_key mismatch",
    ):
        QuranLabHadeethEncParser().parse(
            _hadeethenc_ar(),
            english_payload=english,
        )


def test_hadeethenc_pair_requires_same_id() -> None:
    english = _hadeethenc_en()
    english["hadeethenc_id"] = 9999

    with pytest.raises(
        QuranLabHadithParseError,
        match="identity mismatch",
    ):
        QuranLabHadeethEncParser().parse(
            _hadeethenc_ar(),
            english_payload=english,
        )


def test_snapshot_parser_dispatches_ahmad() -> None:
    record = QuranLabSnapshotParser().parse(
        config="ahmad-ar",
        payload=_ahmad_row(),
    )

    assert (
        record.primary_reference.collection_id
        == "ahmad"
    )


def test_snapshot_parser_dispatches_hadeethenc() -> None:
    record = QuranLabSnapshotParser().parse(
        config="hadeethenc-ar",
        payload=_hadeethenc_ar(),
        paired_payload=_hadeethenc_en(),
    )

    assert (
        record.primary_reference.collection_id
        == "hadeethenc"
    )


def test_hadeethenc_english_cannot_be_primary() -> None:
    with pytest.raises(
        QuranLabHadithParseError,
        match="must be paired",
    ):
        QuranLabSnapshotParser().parse(
            config="hadeethenc-en",
            payload=_hadeethenc_en(),
        )


def test_unknown_snapshot_config_is_rejected() -> None:
    with pytest.raises(
        QuranLabHadithParseError,
        match="Unsupported",
    ):
        QuranLabSnapshotParser().parse(
            config="unknown-ar",
            payload=_ahmad_row(),
        )


def test_hadeethenc_grade_translation_conflict_is_preserved_for_review() -> None:
    arabic = _hadeethenc_ar()
    english = _hadeethenc_en()

    arabic["grade"] = "ضعيف"
    english["grade"] = "Authentic hadith"

    record = QuranLabHadeethEncParser().parse(
        arabic,
        english_payload=english,
    )

    assessment = record.grade_assessments[0]

    assert assessment.grade_text == "ضعيف"
    assert (
        assessment.category
        is HadithGradeCategory.DAIF
    )

    assert (
        record.text_variants[0]
        .english_translation
        == english["text"]
    )

    assert record.notes is not None
    assert (
        "hadeethenc_translation_grade_conflict"
        in record.notes
    )
