import json

import pytest

from basira.models.scholarly import (
    ScholarlyDomain,
)
from basira.sources.scholarly.surahapp_parser import (
    SurahAppScholarlyParser,
)


def write_json(
    path,
    value,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_parser_preserves_exact_source_text(
    tmp_path,
) -> None:
    source_slug = (
        "tafsir-mokhtasar"
    )

    source_id = (
        "surahapp-tafsir-mokhtasar"
    )

    exact_text = (
        "  نصٌ محفوظ كما ورد.\r\n"
        "سطر ثانٍ.  "
    )

    write_json(
        tmp_path
        / "snapshot-manifest.json",
        {
            "snapshot_version": "v1",
            "integrity_status": "PASS",
            "sources": [
                {
                    "source_id": source_id,
                    "source_slug": (
                        source_slug
                    ),
                    "title": (
                        "المختصر في تفسير "
                        "القرآن الكريم"
                    ),
                    "coverage_mode": (
                        "complete_quran"
                    ),
                    "record_count": 1,
                    "corpus_file": (
                        f"{source_slug}/"
                        "corpus.json"
                    ),
                    "quran_alignment": {
                        "status": "PASS",
                        "unresolved_reference_count": 0,
                    },
                }
            ],
        },
    )

    write_json(
        tmp_path
        / source_slug
        / "project.json",
        {
            "title": "المختصر",
            "type": "aya",
        },
    )

    write_json(
        tmp_path
        / source_slug
        / "corpus.json",
        [
            {
                "content": exact_text,
                "sura_number": 2,
                "sura_name": "البقرة",
                "aya_number": 255,
                "aya_text": "اللَّهُ",
            }
        ],
    )

    passages = (
        SurahAppScholarlyParser()
        .parse_snapshot(
            tmp_path
        )
    )

    assert len(passages) == 1

    passage = passages[0]

    assert passage.text == exact_text

    assert (
        passage.domain
        == ScholarlyDomain.TAFSIR
    )

    assert (
        passage.quran_reference
        == "2:255"
    )

    assert (
        passage.passage_id
        == (
            "surahapp-tafsir-"
            "mokhtasar:2:255"
        )
    )


def test_unknown_source_is_rejected(
    tmp_path,
) -> None:
    write_json(
        tmp_path
        / "snapshot-manifest.json",
        {
            "snapshot_version": "v1",
            "integrity_status": "PASS",
            "sources": [
                {
                    "source_id": "unknown",
                    "source_slug": "unknown",
                    "title": "Unknown",
                    "coverage_mode": "sparse",
                    "record_count": 0,
                    "corpus_file": (
                        "unknown/corpus.json"
                    ),
                    "quran_alignment": {
                        "status": "PASS",
                        "unresolved_reference_count": 0,
                    },
                }
            ],
        },
    )

    with pytest.raises(
        ValueError,
        match=(
            "Unapproved Surah App source"
        ),
    ):
        (
            SurahAppScholarlyParser()
            .parse_snapshot(
                tmp_path
            )
        )
