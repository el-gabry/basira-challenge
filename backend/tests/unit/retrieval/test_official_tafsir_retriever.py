from __future__ import annotations

from basira.competition.retrieval_bridge import (
    CompetitionSourceUnavailable,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.models.quran import QuranVerse
from basira.retrieval.official_tafsir_retriever import (
    OfficialTafsirDomainRetriever,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlan,
    RetrievalStrategy,
    RetrievalTarget,
)
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
)
from basira.sources.quran.repository import (
    QuranRepository,
)

QUESTION = "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟"


def repository() -> QuranRepository:
    return QuranRepository(
        (
            QuranVerse(
                source_id=("quranpedia:mushaf:1"),
                surah_number=2,
                ayah_number=255,
                text_uthmani=(
                    "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالْأَرْضَ"
                ),
                text_search=(
                    "الله لا اله الا هو الحي القيوم وسع كرسيه السماوات والارض"
                ),
                narration="حفص عن عاصم",
            ),
        )
    )


def understanding(
    question: str = QUESTION,
):
    return BasiraQueryUnderstandingService().understand(question)


def tafsir_target():
    return RetrievalTarget(
        domain=EvidenceDomain.TAFSIR,
        strategies=(RetrievalStrategy.LEXICAL_FALLBACK,),
        references=("2:255",),
    )


class RecordingAdapter:
    def __init__(self) -> None:
        self.request = None

    def retrieve(
        self,
        request,
    ):
        self.request = request

        return (
            EvidenceNode(
                evidence_id=("dorar-tafsir:test"),
                domain=(EvidenceDomain.TAFSIR),
                text="معنى الكرسي",
                source_id=("dorar-tafsir-v1"),
                reference=("https://dorar.net/tafseer/2/43#tt7"),
                related_quran=(
                    "2:254",
                    "2:255",
                    "2:256",
                    "2:257",
                ),
                claim_type=("tafsir_linguistic_explanation"),
            ),
        )


class UnavailableAdapter:
    def retrieve(
        self,
        request,
    ):
        del request

        raise CompetitionSourceUnavailable("dorar_tafsir")


def test_anchor_becomes_focus_but_identity_is_preserved():
    adapter = RecordingAdapter()

    retriever = OfficialTafsirDomainRetriever(
        adapter=adapter,
        quran_repository=repository(),
    )

    nodes = retriever.retrieve(
        understanding=understanding(),
        target=tafsir_target(),
        limit=10,
    )

    assert nodes

    request = adapter.request

    assert request is not None

    assert request.query == "وسع كرسيه السماوات والارض"

    assert request.query != "2:255"

    assert request.references == ("2:255",)

    # One accepted passage, not literal
    # search-result top-1.
    assert request.limit == 1


def test_no_overlap_uses_fallback_without_dropping_identity():
    adapter = RecordingAdapter()

    retriever = OfficialTafsirDomainRetriever(
        adapter=adapter,
        quran_repository=repository(),
    )

    retriever.retrieve(
        understanding=understanding("فسر الآية رقم 2:255"),
        target=tafsir_target(),
        limit=10,
    )

    request = adapter.request

    assert request is not None
    assert request.query
    assert request.query != "2:255"

    assert request.references == ("2:255",)


def test_runs_inside_existing_basira_unified_spine():
    adapter = RecordingAdapter()

    domain = OfficialTafsirDomainRetriever(
        adapter=adapter,
        quran_repository=repository(),
    )

    understood = understanding()

    plan = BasiraRetrievalPlan(
        understanding=understood,
        targets=(tafsir_target(),),
        context_requirement=(understood.context_requirement),
    )

    result = BasiraUnifiedRetriever(
        {
            EvidenceDomain.TAFSIR: domain,
        }
    ).retrieve(
        plan,
        limit_per_domain=10,
    )

    assert result.unavailable_domains == frozenset()

    assert len(result.evidence) == 1

    assert result.evidence[0].source_id == "dorar-tafsir-v1"

    assert "2:255" in result.evidence[0].related_quran


def test_source_unavailable_maps_to_domain_unavailable():
    domain = OfficialTafsirDomainRetriever(
        adapter=UnavailableAdapter(),
        quran_repository=repository(),
    )

    understood = understanding()

    plan = BasiraRetrievalPlan(
        understanding=understood,
        targets=(tafsir_target(),),
        context_requirement=(understood.context_requirement),
    )

    result = BasiraUnifiedRetriever(
        {
            EvidenceDomain.TAFSIR: domain,
        }
    ).retrieve(plan)

    assert result.evidence == ()

    assert result.unavailable_domains == frozenset(
        {
            EvidenceDomain.TAFSIR,
        }
    )


def test_named_kursi_uses_verified_tafsir_discovery_hint() -> None:
    adapter = RecordingAdapter()

    retriever = OfficialTafsirDomainRetriever(
        adapter=adapter,
        quran_repository=repository(),
    )

    nodes = retriever.retrieve(
        understanding=understanding("تفسير آية الكرسي"),
        target=tafsir_target(),
        limit=10,
    )

    assert nodes

    request = adapter.request

    assert request is not None

    assert request.query == "وسع كرسيه"

    assert request.references == ("2:255",)

    assert request.limit == 1
