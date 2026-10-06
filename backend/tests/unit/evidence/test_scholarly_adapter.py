from __future__ import annotations

import pytest
from pydantic import ValidationError

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.evidence.scholarly_adapter import (
    ScholarlyEvidenceAdapter,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)


def test_tafsir_passage_maps_to_evidence() -> None:
    passage = ScholarlyPassage(
        passage_id="test-tafsir:2:255",
        source_id="test-tafsir",
        domain=(
            ScholarlyDomain.TAFSIR
        ),
        work_id="test-work",
        work_title="Test Tafsir",
        author_name="Test Author",
        text="تفسير الآية",
        source_version="1.0",
        source_url=(
            "https://example.test/2/255"
        ),
        surah_number=2,
        ayah_start=255,
        ayah_end=255,
    )

    node = (
        ScholarlyEvidenceAdapter()
        .from_passage(passage)
    )

    assert (
        node.domain
        is EvidenceDomain.TAFSIR
    )

    assert (
        node.reference
        == "2:255"
    )

    assert (
        node.work_title
        == "Test Tafsir"
    )

    assert (
        node.author_name
        == "Test Author"
    )

    assert (
        node.related_quran
        == ("2:255",)
    )


def test_multi_ayah_tafsir_reference() -> None:
    passage = ScholarlyPassage(
        passage_id="test:29:1-3",
        source_id="test",
        domain=(
            ScholarlyDomain.TAFSIR
        ),
        work_id="test",
        work_title="Test",
        text="تفسير مجموعة آيات",
        surah_number=29,
        ayah_start=1,
        ayah_end=3,
    )

    assert (
        passage.quran_reference
        == "29:1-3"
    )


def test_invalid_quran_span_is_rejected() -> None:
    with pytest.raises(
        ValidationError
    ):
        ScholarlyPassage(
            passage_id="invalid",
            source_id="test",
            domain=(
                ScholarlyDomain.TAFSIR
            ),
            work_id="test",
            work_title="Test",
            text="invalid",
            surah_number=2,
            ayah_start=10,
            ayah_end=5,
        )


def test_non_quran_fiqh_passage_is_valid() -> None:
    passage = ScholarlyPassage(
        passage_id="fiqh:test:1",
        source_id="fiqh-test",
        domain=(
            ScholarlyDomain.FIQH
        ),
        work_id="fiqh-work",
        work_title="Fiqh Work",
        chapter_title="البيع",
        text="نص فقهي",
    )

    node = (
        ScholarlyEvidenceAdapter()
        .from_passage(passage)
    )

    assert (
        node.domain
        is EvidenceDomain.FIQH
    )

    assert (
        node.reference
        == "البيع"
    )

    assert not (
        node.related_quran
    )
