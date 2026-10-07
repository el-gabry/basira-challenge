import pytest

from basira.competition.quranpedia_adapter import (
    QuranpediaAdmissionError,
    _collect_ayah_records,
    _record_to_verse,
)


def _snapshot(
    *,
    parent_id: int = 67,
):
    return {
        "surahs": [
            {
                "id": parent_id,
                "name": "سورة الملك",
                "coded_name": "x",
                "ayahs": [
                    {
                        "surah": "67",
                        "number": 5,
                        "number_in_hafs": [5],
                        "text": (
                            "وَلَقَدْ زَيَّنَّا "
                            "السَّمَاءَ الدُّنْيَا"
                        ),
                        "juz": 29,
                        "page_number": 562,
                    }
                ],
            }
        ]
    }


def test_collect_preserves_parent_surah_identity() -> None:
    records = _collect_ayah_records(
        _snapshot()
    )

    assert len(records) == 1

    record = records[0]

    assert record["_parent_surah_id"] == 67
    assert (
        record["_parent_surah_name_ar"]
        == "سورة الملك"
    )


def test_record_to_verse_exposes_clean_surah_name() -> None:
    record = _collect_ayah_records(
        _snapshot()
    )[0]

    verse = _record_to_verse(
        record,
        source_id="quranpedia:test",
        narration="حفص عن عاصم",
    )

    assert verse.reference == "67:5"
    assert verse.surah_name_ar == "الملك"


def test_parent_surah_identity_mismatch_fails_closed() -> None:
    record = _collect_ayah_records(
        _snapshot(
            parent_id=66,
        )
    )[0]

    with pytest.raises(
        QuranpediaAdmissionError,
        match="parent_surah_identity_mismatch",
    ):
        _record_to_verse(
            record,
            source_id="quranpedia:test",
            narration="حفص عن عاصم",
        )
