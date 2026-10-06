from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from basira.competition.quranpedia_translation_adapter import (
    QURANPEDIA_TRANSLATION_MANIFEST_PATH,
    QURANPEDIA_TRANSLATION_PASSPORT_PATH,
    QuranpediaTranslationAdmissionError,
    QuranpediaTranslationEvidenceAdapter,
)
from basira.evidence.models import (
    EvidenceDomain,
)

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)

SNAPSHOT_REL = Path(
    "data/competition/normalized/quranpedia/"
    "2026-10-06/translation-13638.json"
)


def test_english_quran_2255_is_governed() -> None:
    node = QuranpediaTranslationEvidenceAdapter(
        repo_root=PROJECT_ROOT
    ).get(
        surah=2,
        ayah=255,
    )

    assert node is not None

    assert node.domain is EvidenceDomain.QURAN

    assert (
        node.source_id
        == "quranpedia:translation:en:13638"
    )

    assert node.claim_type == "quran_translation"

    assert node.reference == "2:255"

    assert node.related_quran == (
        "2:255",
    )

    assert (
        node.authority_scope
        == "translation_of_quran_meanings"
    )

    assert (
        "His Kursi extends over "
        "the heavens and the earth"
        in node.text
    )

    assert "<" not in node.text

    assert (
        node.source_url
        == (
            "https://quranpedia.net/"
            "translation-books/13638.json"
        )
    )


def test_english_quran_has_all_references() -> None:
    adapter = (
        QuranpediaTranslationEvidenceAdapter(
            repo_root=PROJECT_ROOT
        )
    )

    assert len(
        adapter._records
    ) == 6236

    assert (
        2,
        255,
    ) in adapter._records

    assert (
        114,
        6,
    ) in adapter._records


def test_mixed_source_markup_extracts_only_english() -> None:
    node = QuranpediaTranslationEvidenceAdapter(
        repo_root=PROJECT_ROOT
    ).get(
        surah=95,
        ayah=1,
    )

    assert node is not None

    assert (
        node.text
        == "By the fig and the olive"
    )

    assert "<" not in node.text


def test_translation_snapshot_tampering_fails_closed(
    tmp_path: Path,
) -> None:
    for relative in (
        QURANPEDIA_TRANSLATION_PASSPORT_PATH,
        QURANPEDIA_TRANSLATION_MANIFEST_PATH,
        SNAPSHOT_REL,
    ):
        source = (
            PROJECT_ROOT
            / relative
        )

        target = (
            tmp_path
            / relative
        )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copyfile(
            source,
            target,
        )

    snapshot = (
        tmp_path
        / SNAPSHOT_REL
    )

    payload = json.loads(
        snapshot.read_text(
            encoding="utf-8"
        )
    )

    payload["ayahs"][0][
        "translated_text"
    ] = (
        "<div style='direction: ltr'>"
        "tampered"
        "</div>"
    )

    snapshot.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    adapter = QuranpediaTranslationEvidenceAdapter(
        repo_root=tmp_path
    )

    with pytest.raises(
        QuranpediaTranslationAdmissionError,
        match="snapshot_hash_mismatch",
    ):
        adapter.get(
            surah=2,
            ayah=255,
        )
