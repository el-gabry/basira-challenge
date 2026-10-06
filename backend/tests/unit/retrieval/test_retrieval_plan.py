from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlanner,
    RetrievalStrategy,
)


def build(
    query: str,
):
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(query)
    )

    return (
        BasiraRetrievalPlanner()
        .build(
            understanding
        )
    )


def test_hadith_authenticity_routes_to_hadith() -> None:
    plan = build(
        "ما صحة هذا الحديث؟"
    )

    assert len(
        plan.targets
    ) == 1

    target = plan.targets[0]

    assert (
        target.domain
        is EvidenceDomain.HADITH
    )

    assert (
        RetrievalStrategy
        .EXACT_REFERENCE
        in target.strategies
    )

    assert (
        plan.context_requirement
        .requires(
            EvidenceNeed.HADITH_GRADE
        )
    )


def test_quran_meaning_routes_to_quran_and_tafsir() -> None:
    plan = build(
        "ما معنى آية الكرسي؟"
    )

    domains = tuple(
        target.domain
        for target
        in plan.targets
    )

    assert (
        EvidenceDomain.QURAN
        in domains
    )

    assert (
        EvidenceDomain.TAFSIR
        in domains
    )


def test_sensitive_quran_plan_preserves_context_contract() -> None:
    plan = build(
        "ما معنى آية فاقتلوا "
        "المشركين حيث وجدتموهم؟"
    )

    assert (
        plan.context_requirement
        .requires(
            EvidenceNeed
            .SURROUNDING_CONTEXT
        )
    )

    assert (
        plan.context_requirement
        .requires(
            EvidenceNeed
            .FIQH_CONSTRAINTS
        )
    )


def test_fiqh_question_routes_to_fiqh_and_hadith() -> None:
    plan = build(
        "ما حكم البيع بالتقسيط؟"
    )

    domains = {
        target.domain
        for target
        in plan.targets
    }

    assert (
        EvidenceDomain.FIQH
        in domains
    )

    assert (
        EvidenceDomain.HADITH
        in domains
    )
