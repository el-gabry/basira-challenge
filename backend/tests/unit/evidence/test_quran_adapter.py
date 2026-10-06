from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.evidence.quran_adapter import (
    QuranEvidenceAdapter,
)
from basira.models.quran import QuranVerse


def test_quran_verse_becomes_evidence_node() -> None:
    verse = QuranVerse(
        source_id=(
            "tanzil-quran-v1.1-uthmani"
        ),
        surah_number=2,
        ayah_number=255,
        text_uthmani=(
            "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ"
        ),
        text_search=(
            "الله لا اله الا هو"
        ),
    )

    node = (
        QuranEvidenceAdapter()
        .from_verse(verse)
    )

    assert (
        node.domain
        is EvidenceDomain.QURAN
    )

    assert node.reference == "2:255"

    assert (
        node.text
        == "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ"
    )

    assert (
        node.claim_type
        == "quran_text"
    )
