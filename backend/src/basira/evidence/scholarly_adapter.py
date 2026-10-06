from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)

_DOMAIN_MAP = {
    ScholarlyDomain.TAFSIR: EvidenceDomain.TAFSIR,
    ScholarlyDomain.REVELATION_CONTEXT: EvidenceDomain.REVELATION_CONTEXT,
    ScholarlyDomain.FIQH: EvidenceDomain.FIQH,
    ScholarlyDomain.FATWA: EvidenceDomain.FATWA,
    ScholarlyDomain.AQIDAH: EvidenceDomain.AQIDAH,
    ScholarlyDomain.SIRA: EvidenceDomain.SIRA,
    ScholarlyDomain.HISTORY: EvidenceDomain.HISTORY,
    ScholarlyDomain.LANGUAGE: EvidenceDomain.LANGUAGE,
    ScholarlyDomain.GENERAL: EvidenceDomain.GENERAL,
}


class ScholarlyEvidenceAdapter:
    """
    Convert attributed scholarly passages into the
    shared Basira EvidenceNode representation.
    """

    def from_passage(
        self,
        passage: ScholarlyPassage,
    ) -> EvidenceNode:
        quran_reference = passage.quran_reference

        related_quran = (quran_reference,) if quran_reference is not None else ()

        return EvidenceNode(
            evidence_id=(passage.passage_id),
            domain=(_DOMAIN_MAP[passage.domain]),
            text=passage.text,
            source_id=passage.source_id,
            source_version=(passage.source_version),
            reference=(
                quran_reference or passage.section_title or passage.chapter_title
            ),
            source_url=(passage.source_url),
            work_id=passage.work_id,
            work_title=(passage.work_title),
            author_name=(passage.author_name),
            institution=(passage.institution),
            publisher=(passage.publisher),
            volume=passage.volume,
            page=passage.page,
            topic=(passage.chapter_title or passage.section_title),
            claim_type=(f"{passage.domain.value}_passage"),
            related_quran=(related_quran),
        )
