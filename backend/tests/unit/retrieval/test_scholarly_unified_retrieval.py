from basira.evidence.models import (
    EvidenceDomain,
)
from basira.models.quran import QuranVerse
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
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
from basira.retrieval.revelation_context_retriever import (
    RevelationContextRetriever,
)
from basira.retrieval.tafsir_retriever import (
    TafsirDomainRetriever,
)
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
)
from basira.sources.quran.repository import (
    QuranRepository,
)
from basira.sources.scholarly.repository import (
    ScholarlyRepository,
)


class AllowAllRuntime:
    def allows(
        self,
        *,
        source_id: str,
        runtime_use: object,
    ) -> bool:
        del source_id
        del runtime_use

        return True


def make_tafsir(
    source_id: str,
) -> ScholarlyPassage:
    return ScholarlyPassage(
        passage_id=(
            f"{source_id}:58:1"
        ),
        source_id=source_id,
        domain=ScholarlyDomain.TAFSIR,
        work_id=source_id,
        work_title=source_id,
        text=(
            f"tafsir text from {source_id}"
        ),
        surah_number=58,
        ayah_start=1,
        ayah_end=1,
    )


def test_revelation_context_query_retrieves_multi_role_evidence() -> None:
    quran_repository = QuranRepository(
        (
            QuranVerse(
                source_id="test-quran",
                surah_number=58,
                ayah_number=1,
                text_uthmani=(
                    "قَدْ سَمِعَ اللَّهُ"
                ),
                text_search=(
                    "قد سمع الله"
                ),
            ),
        )
    )

    scholarly_repository = (
        ScholarlyRepository(
            (
                make_tafsir(
                    "katheer"
                ),
                make_tafsir(
                    "saadi"
                ),
                make_tafsir(
                    "mokhtasar"
                ),
                ScholarlyPassage(
                    passage_id=(
                        "nozool:58:1"
                    ),
                    source_id="nozool",
                    domain=(
                        ScholarlyDomain
                        .REVELATION_CONTEXT
                    ),
                    work_id=(
                        "ayat-nozool"
                    ),
                    work_title=(
                        "صحيح أسباب النزول"
                    ),
                    text=(
                        "نص سبب النزول."
                    ),
                    surah_number=58,
                    ayah_start=1,
                    ayah_end=1,
                ),
            )
        )
    )

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

    retriever = BasiraUnifiedRetriever(
        {
            EvidenceDomain.QURAN: (
                QuranDomainRetriever(
                    repository=(
                        quran_repository
                    ),
                    runtime=(
                        AllowAllRuntime()
                    ),  # type: ignore[arg-type]
                )
            ),
            EvidenceDomain.TAFSIR: (
                TafsirDomainRetriever(
                    repository=(
                        scholarly_repository
                    )
                )
            ),
            EvidenceDomain.REVELATION_CONTEXT: (
                RevelationContextRetriever(
                    repository=(
                        scholarly_repository
                    )
                )
            ),
        }
    )

    result = retriever.retrieve(
        plan
    )

    assert (
        result.unavailable_domains
        == frozenset()
    )

    assert len(
        result.evidence
    ) == 5

    quran = tuple(
        node
        for node in result.evidence
        if node.domain
        == EvidenceDomain.QURAN
    )

    tafsir = tuple(
        node
        for node in result.evidence
        if node.domain
        == EvidenceDomain.TAFSIR
    )

    revelation_context = tuple(
        node
        for node in result.evidence
        if node.domain
        == EvidenceDomain.REVELATION_CONTEXT
    )

    assert len(quran) == 1
    assert len(tafsir) == 3
    assert len(revelation_context) == 1

    assert all(
        node.reference == "58:1"
        for node in (
            *quran,
            *tafsir,
            *revelation_context,
        )
    )
