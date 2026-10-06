from __future__ import annotations

from collections.abc import Iterable

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
)

_NEED_DOMAIN_MAP: dict[
    EvidenceNeed,
    EvidenceDomain,
] = {
    EvidenceNeed.CANONICAL_TEXT: EvidenceDomain.QURAN,
    EvidenceNeed.HADITH_TEXT: EvidenceDomain.HADITH,
    EvidenceNeed.HADITH_GRADE: EvidenceDomain.HADITH,
    EvidenceNeed.RELATED_HADITH: EvidenceDomain.HADITH,
    EvidenceNeed.TAFSIR: EvidenceDomain.TAFSIR,
    EvidenceNeed.REVELATION_CONTEXT: EvidenceDomain.REVELATION_CONTEXT,
    EvidenceNeed.FIQH_EVIDENCE: EvidenceDomain.FIQH,
    EvidenceNeed.FIQH_CONSTRAINTS: EvidenceDomain.FIQH,
    EvidenceNeed.FIQH_MADHHAB_SCOPE: EvidenceDomain.FIQH,
    EvidenceNeed.FIQH_CONDITIONS: EvidenceDomain.FIQH,
    EvidenceNeed.FIQH_EXCEPTIONS: EvidenceDomain.FIQH,
    EvidenceNeed.FIQH_DISAGREEMENT: EvidenceDomain.FIQH,
    EvidenceNeed.CONTEMPORARY_GUIDANCE: EvidenceDomain.FATWA,
}


def evidence_domain_for_need(
    need: EvidenceNeed,
) -> EvidenceDomain | None:
    """
    Return the evidence domain that can structurally
    satisfy a concrete EvidenceNeed.

    Some needs intentionally have no single domain:
    provenance, applicability, actor authority,
    surrounding context, etc. Those remain constraints
    evaluated elsewhere.
    """

    return _NEED_DOMAIN_MAP.get(need)


def evidence_domains_for_needs(
    needs: Iterable[EvidenceNeed],
) -> frozenset[EvidenceDomain]:
    return frozenset(
        domain
        for need in needs
        if (domain := (evidence_domain_for_need(need))) is not None
    )
