from basira.evidence.models import (
    EvidenceNeed,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
)


def test_revelation_context_query_is_detected() -> None:
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما سبب نزول الآية 58:1؟"
        )
    )

    assert (
        understanding.primary_intent
        == BasiraIntent.TAFSIR_CONTEXT
    )

    requirement = (
        understanding.context_requirement
    )

    assert requirement.requires(
        EvidenceNeed.CANONICAL_TEXT
    )

    assert requirement.requires(
        EvidenceNeed.TAFSIR
    )

    assert requirement.requires(
        EvidenceNeed.REVELATION_CONTEXT
    )

    assert requirement.requires(
        EvidenceNeed.SOURCE_PROVENANCE
    )


def test_quran_meaning_does_not_require_revelation_context() -> None:
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما معنى الآية 2:255؟"
        )
    )

    assert (
        understanding.primary_intent
        == BasiraIntent.QURAN_MEANING
    )

    assert not (
        understanding
        .context_requirement
        .requires(
            EvidenceNeed
            .REVELATION_CONTEXT
        )
    )
