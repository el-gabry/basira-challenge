from __future__ import annotations

from dataclasses import replace

from basira.api.governed_runtime import (
    _quran_repository,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalBridge,
)
from basira.competition.unified_retriever import (
    CompetitionUnifiedRetriever,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.models.quran import (
    QuranVerse,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlanner,
)
from basira.sources.quran.repository import (
    QuranRepository,
)


class RecordingQuranAdapter:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def retrieve(
        self,
        request,
    ):
        self.queries.append(request.query)

        return (
            EvidenceNode(
                evidence_id="competition:quran:2:255",
                domain=EvidenceDomain.QURAN,
                text=("اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ"),
                source_id="quranpedia:mushaf:1",
                reference="2:255",
                claim_type="quran_text",
                related_quran=("2:255",),
            ),
        )


def repository() -> QuranRepository:
    return QuranRepository(
        (
            QuranVerse(
                source_id="quranpedia:mushaf:1",
                surah_number=2,
                ayah_number=255,
                text_uthmani=("اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ"),
                text_search=("الله لا اله الا هو الحي القيوم"),
                narration="حفص عن عاصم",
            ),
        )
    )


def quran_plan():
    understanding = BasiraQueryUnderstandingService().understand("ما معنى الآية 2:255؟")

    plan = BasiraRetrievalPlanner().build(understanding)

    quran_target = next(
        target for target in plan.targets if target.domain is EvidenceDomain.QURAN
    )

    constrained = replace(
        quran_target,
        references=("2:255",),
    )

    return replace(
        plan,
        targets=(constrained,),
    )


def test_hard_quran_reference_goes_through_competition_bridge():
    adapter = RecordingQuranAdapter()

    bridge = CompetitionRetrievalBridge(
        evidence_adapters={
            OfficialDomain.QURAN: adapter,
        }
    )

    retriever = CompetitionUnifiedRetriever(
        bridge=bridge,
        quran_repository=repository(),
    )

    result = retriever.retrieve(quran_plan())

    assert adapter.queries == [
        "2:255",
    ]

    assert len(result.evidence) == 1

    node = result.evidence[0]

    assert node.source_id == "quranpedia:mushaf:1"

    assert node.reference == "2:255"

    assert result.unavailable_domains == frozenset()


def test_missing_competition_adapter_fails_closed():
    retriever = CompetitionUnifiedRetriever(
        bridge=CompetitionRetrievalBridge(),
        quran_repository=repository(),
    )

    result = retriever.retrieve(quran_plan())

    assert result.evidence == ()

    assert result.unavailable_domains == frozenset(
        {
            EvidenceDomain.QURAN,
        }
    )


def test_quran_repository_is_visible_to_existing_anchor_resolver():
    expected = repository()

    retriever = CompetitionUnifiedRetriever(
        bridge=CompetitionRetrievalBridge(),
        quran_repository=expected,
    )

    assert _quran_repository(retriever) is expected


def test_unsupported_domain_does_not_fall_back():
    understanding = BasiraQueryUnderstandingService().understand("ما سبب نزول الآية؟")

    plan = BasiraRetrievalPlanner().build(understanding)

    revelation = next(
        target
        for target in plan.targets
        if target.domain is EvidenceDomain.REVELATION_CONTEXT
    )

    plan = replace(
        plan,
        targets=(revelation,),
    )

    retriever = CompetitionUnifiedRetriever(
        bridge=CompetitionRetrievalBridge(),
        quran_repository=repository(),
    )

    result = retriever.retrieve(plan)

    assert result.evidence == ()

    assert result.unavailable_domains == frozenset(
        {
            EvidenceDomain.REVELATION_CONTEXT,
        }
    )


class RecordingTafsirAdapter:
    def __init__(self) -> None:
        self.requests = []

    def retrieve(
        self,
        request,
    ):
        self.requests.append(request)

        return (
            EvidenceNode(
                evidence_id="competition:tafsir:kursi",
                domain=EvidenceDomain.TAFSIR,
                text="معنى الكرسي",
                source_id="dorar-tafsir-v1",
                reference=("https://dorar.net/tafseer/2/43"),
                claim_type="tafsir_general_meaning",
                related_quran=(
                    "2:254",
                    "2:255",
                    "2:256",
                    "2:257",
                ),
            ),
        )


def test_anchored_tafsir_uses_quran_phrase_not_reference():
    quran = RecordingQuranAdapter()
    tafsir = RecordingTafsirAdapter()

    bridge = CompetitionRetrievalBridge(
        evidence_adapters={
            OfficialDomain.QURAN: quran,
            OfficialDomain.TAFSIR: tafsir,
        }
    )

    retriever = CompetitionUnifiedRetriever(
        bridge=bridge,
        quran_repository=QuranRepository(
            (
                QuranVerse(
                    source_id="quranpedia:mushaf:1",
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
        ),
    )

    understanding = BasiraQueryUnderstandingService().understand(
        "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟"
    )

    plan = BasiraRetrievalPlanner().build(understanding)

    targets = tuple(
        replace(
            target,
            references=("2:255",),
        )
        if target.domain is EvidenceDomain.QURAN
        else target
        for target in plan.targets
        if target.domain
        in {
            EvidenceDomain.QURAN,
            EvidenceDomain.TAFSIR,
        }
    )

    plan = replace(
        plan,
        targets=targets,
    )

    retriever.retrieve(
        plan,
        limit_per_domain=5,
    )

    assert len(tafsir.requests) == 1

    request = tafsir.requests[0]

    assert request.query == "وسع كرسيه السماوات والارض"

    assert request.query != "2:255"
    assert request.limit == 1
