from basira.evidence.models import (
    EvidenceDomain,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlanner,
    RetrievalStrategy,
)


def test_revelation_context_query_routes_required_domains() -> None:
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما سبب نزول الآية 58:1؟"
        )
    )

    plan = (
        BasiraRetrievalPlanner()
        .build(
            understanding
        )
    )

    domains = tuple(
        target.domain
        for target in plan.targets
    )

    assert domains == (
        EvidenceDomain.QURAN,
        EvidenceDomain.TAFSIR,
        EvidenceDomain.REVELATION_CONTEXT,
    )


def test_quran_meaning_does_not_route_revelation_context() -> None:
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما معنى الآية 2:255؟"
        )
    )

    plan = (
        BasiraRetrievalPlanner()
        .build(
            understanding
        )
    )

    domains = tuple(
        target.domain
        for target in plan.targets
    )

    assert domains == (
        EvidenceDomain.QURAN,
        EvidenceDomain.TAFSIR,
    )

    assert (
        EvidenceDomain.REVELATION_CONTEXT
        not in domains
    )


def test_general_conceptual_query_routes_tafsir_lexical_fallback() -> None:
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ماذا يقول الإسلام عن الصبر؟"
        )
    )

    plan = (
        BasiraRetrievalPlanner()
        .build(
            understanding
        )
    )

    domains = tuple(
        target.domain
        for target in plan.targets
    )

    assert domains == (
        EvidenceDomain.QURAN,
        EvidenceDomain.HADITH,
        EvidenceDomain.TAFSIR,
    )

    tafsir_target = next(
        target
        for target in plan.targets
        if target.domain
        is EvidenceDomain.TAFSIR
    )

    assert (
        RetrievalStrategy
        .LEXICAL_FALLBACK
        in tafsir_target.strategies
    )
