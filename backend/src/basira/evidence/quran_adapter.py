from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.models.quran import (
    QuranVerse,
)


class QuranEvidenceAdapter:
    """
    Convert an authorized QuranVerse into Basira's
    unified evidence representation.

    Uthmani text remains the evidence/display text.
    Search-normalized text never replaces it.
    """

    def from_verse(
        self,
        verse: QuranVerse,
    ) -> EvidenceNode:
        return EvidenceNode(
            evidence_id=(
                f"{verse.source_id}:"
                f"{verse.reference}"
            ),
            domain=EvidenceDomain.QURAN,
            text=verse.text_uthmani,
            source_id=verse.source_id,
            reference=verse.reference,
            claim_type="quran_text",
            related_quran=(
                verse.reference,
            ),
        )
