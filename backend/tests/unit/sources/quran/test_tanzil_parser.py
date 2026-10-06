from pathlib import Path

import pytest

import basira.sources.quran.tanzil.parser as parser_module
from basira.sources.quran.tanzil.parser import (
    TANZIL_SOURCE_ID,
    TanzilDatasetError,
    TanzilQuranParser,
)


def write_file(
    path: Path,
    content: str,
) -> Path:
    path.write_text(
        content,
        encoding="utf-8",
    )
    return path


def test_parse_aligned_tanzil_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        parser_module,
        "EXPECTED_VERSE_COUNT",
        2,
    )

    uthmani = write_file(
        tmp_path / "uthmani.txt",
        "\n".join(
            [
                "1|1|بِسْمِ ٱللَّهِ",
                "1|2|ٱلْحَمْدُ لِلَّهِ",
            ]
        ),
    )

    simple = write_file(
        tmp_path / "simple.txt",
        "\n".join(
            [
                "1|1|بسم الله",
                "1|2|الحمد لله",
            ]
        ),
    )

    verses = TanzilQuranParser().parse_files(
        uthmani_path=uthmani,
        simple_plain_path=simple,
    )

    assert len(verses) == 2

    first = verses[0]

    assert first.source_id == TANZIL_SOURCE_ID
    assert first.reference == "1:1"
    assert first.text_uthmani == "بِسْمِ ٱللَّهِ"
    assert first.text_search == "بسم الله"


def test_parser_does_not_depend_on_file_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        parser_module,
        "EXPECTED_VERSE_COUNT",
        2,
    )

    uthmani = write_file(
        tmp_path / "uthmani.txt",
        "\n".join(
            [
                "2|2|النص الثاني",
                "2|1|النص الأول",
            ]
        ),
    )

    simple = write_file(
        tmp_path / "simple.txt",
        "\n".join(
            [
                "2|1|بحث الأول",
                "2|2|بحث الثاني",
            ]
        ),
    )

    verses = TanzilQuranParser().parse_files(
        uthmani_path=uthmani,
        simple_plain_path=simple,
    )

    assert [
        verse.reference
        for verse in verses
    ] == [
        "2:1",
        "2:2",
    ]

    assert verses[0].text_search == "بحث الأول"
    assert verses[1].text_search == "بحث الثاني"


def test_comments_and_metadata_are_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        parser_module,
        "EXPECTED_VERSE_COUNT",
        1,
    )

    uthmani = write_file(
        tmp_path / "uthmani.txt",
        "\n".join(
            [
                "# Tanzil metadata",
                "1|1|بسم الله",
                "# license",
            ]
        ),
    )

    simple = write_file(
        tmp_path / "simple.txt",
        "\n".join(
            [
                "metadata line",
                "1|1|بسم الله",
            ]
        ),
    )

    verses = TanzilQuranParser().parse_files(
        uthmani_path=uthmani,
        simple_plain_path=simple,
    )

    assert len(verses) == 1
    assert verses[0].reference == "1:1"


def test_duplicate_reference_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        parser_module,
        "EXPECTED_VERSE_COUNT",
        2,
    )

    uthmani = write_file(
        tmp_path / "uthmani.txt",
        "\n".join(
            [
                "1|1|first",
                "1|1|duplicate",
            ]
        ),
    )

    simple = write_file(
        tmp_path / "simple.txt",
        "\n".join(
            [
                "1|1|first",
                "1|2|second",
            ]
        ),
    )

    with pytest.raises(
        TanzilDatasetError,
        match="Duplicate Quran reference",
    ):
        TanzilQuranParser().parse_files(
            uthmani_path=uthmani,
            simple_plain_path=simple,
        )


def test_unexpected_verse_count_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        parser_module,
        "EXPECTED_VERSE_COUNT",
        2,
    )

    uthmani = write_file(
        tmp_path / "uthmani.txt",
        "1|1|بسم الله",
    )

    simple = write_file(
        tmp_path / "simple.txt",
        "1|1|بسم الله",
    )

    with pytest.raises(
        TanzilDatasetError,
        match="Unexpected Tanzil verse count",
    ):
        TanzilQuranParser().parse_files(
            uthmani_path=uthmani,
            simple_plain_path=simple,
        )


def test_mismatched_reference_sets_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        parser_module,
        "EXPECTED_VERSE_COUNT",
        2,
    )

    uthmani = write_file(
        tmp_path / "uthmani.txt",
        "\n".join(
            [
                "1|1|first",
                "1|2|second",
            ]
        ),
    )

    simple = write_file(
        tmp_path / "simple.txt",
        "\n".join(
            [
                "1|1|first",
                "1|3|third",
            ]
        ),
    )

    with pytest.raises(
        TanzilDatasetError,
        match="references do not match",
    ):
        TanzilQuranParser().parse_files(
            uthmani_path=uthmani,
            simple_plain_path=simple,
        )


def test_empty_quran_text_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        parser_module,
        "EXPECTED_VERSE_COUNT",
        1,
    )

    uthmani = write_file(
        tmp_path / "uthmani.txt",
        "1|1|   ",
    )

    simple = write_file(
        tmp_path / "simple.txt",
        "1|1|بسم الله",
    )

    with pytest.raises(
        TanzilDatasetError,
        match="Empty Quran text",
    ):
        TanzilQuranParser().parse_files(
            uthmani_path=uthmani,
            simple_plain_path=simple,
        )


def test_missing_file_is_rejected(
    tmp_path: Path,
) -> None:
    parser = TanzilQuranParser()

    with pytest.raises(FileNotFoundError):
        parser.parse_files(
            uthmani_path=tmp_path / "missing.txt",
            simple_plain_path=tmp_path / "also-missing.txt",
        )