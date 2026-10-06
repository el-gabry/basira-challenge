from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.models.quran import QuranVerse
from basira.models.source_manifest import (
    IntegrityStatus,
    SourceDomain,
    SourceManifest,
    SourceRole,
    SourceStatus,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.quran_retriever import (
    QuranDomainRetriever,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlanner,
)
from basira.sources.quran.repository import (
    QuranRepository,
)
from basira.sources.registry import (
    TrustedSourceRegistry,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)

SOURCE_ID = (
    "tanzil-quran-v1.1-uthmani"
)


def repository() -> QuranRepository:
    return QuranRepository(
        [
            QuranVerse(
                source_id=SOURCE_ID,
                surah_number=2,
                ayah_number=255,
                text_uthmani=(
                    "اللَّهُ لَا إِلَٰهَ "
                    "إِلَّا هُوَ الْحَيُّ "
                    "الْقَيُّومُ"
                ),
                text_search=(
                    "الله لا اله الا هو "
                    "الحي القيوم"
                ),
            ),
            QuranVerse(
                source_id=SOURCE_ID,
                surah_number=2,
                ayah_number=256,
                text_uthmani=(
                    "لَا إِكْرَاهَ فِي الدِّينِ"
                ),
                text_search=(
                    "لا اكراه في الدين"
                ),
            ),
        ]
    )


def runtime(
    *,
    approved: bool = True,
) -> FailClosedSourceRuntime:
    manifest = SourceManifest(
        source_id=SOURCE_ID,
        source_name="Tanzil Quran",
        domain=SourceDomain.QURAN,
        role=(
            SourceRole
            .INDEPENDENT_VERIFIER
        ),
        status=(
            SourceStatus.APPROVED
            if approved
            else SourceStatus.PENDING
        ),
        integrity_status=(
            IntegrityStatus.VERIFIED
        ),
    )

    return FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [manifest]
        )
    )


def quran_target(
    query: str,
):
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(query)
    )

    plan = (
        BasiraRetrievalPlanner()
        .build(
            understanding
        )
    )

    target = next(
        target
        for target in plan.targets
        if (
            target.domain
            is EvidenceDomain.QURAN
        )
    )

    return (
        understanding,
        target,
    )


def test_numeric_reference_retrieval() -> None:
    understanding, target = (
        quran_target(
            "ما معنى الآية 2:255؟"
        )
    )

    nodes = QuranDomainRetriever(
        repository=repository(),
        runtime=runtime(),
    ).retrieve(
        understanding=understanding,
        target=target,
    )

    assert len(nodes) == 1
    assert nodes[0].reference == "2:255"


def test_quran_quote_retrieval() -> None:
    understanding, target = (
        quran_target(
            "ما معنى آية "
            "الله لا إله إلا هو الحي القيوم؟"
        )
    )

    nodes = QuranDomainRetriever(
        repository=repository(),
        runtime=runtime(),
    ).retrieve(
        understanding=understanding,
        target=target,
    )

    assert nodes

    assert (
        nodes[0].reference
        == "2:255"
    )


def test_runtime_denies_pending_quran_source() -> None:
    understanding, target = (
        quran_target(
            "ما معنى الآية 2:255؟"
        )
    )

    nodes = QuranDomainRetriever(
        repository=repository(),
        runtime=runtime(
            approved=False
        ),
    ).retrieve(
        understanding=understanding,
        target=target,
    )

    assert nodes == ()
