from __future__ import annotations

from basira.competition.retrieval_bridge import (
    CompetitionSourceUnavailable,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.models.quran import QuranVerse
from basira.retrieval.official_quran_retriever import (
    OfficialQuranDomainRetriever,
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


def _verse(
    ayah: int,
) -> QuranVerse:
    text = {
        255: ("الله لا اله الا هو الحي القيوم وسع كرسيه السماوات والارض"),
        256: ("لا اكراه في الدين"),
    }[ayah]

    return QuranVerse(
        source_id="quranpedia:mushaf:1",
        surah_number=2,
        ayah_number=ayah,
        text_uthmani=text,
        text_search=text,
        narration="حفص عن عاصم",
    )


class RecordingAdapter:
    def __init__(self) -> None:
        self.repository = QuranRepository(
            (
                _verse(255),
                _verse(256),
            )
        )

        self.requests = []

    def retrieve(
        self,
        request,
    ):
        self.requests.append(request)

        reference = request.query

        if reference == "2:255":
            verse = self.repository.get(
                2,
                255,
            )
        elif reference == "2:256":
            verse = self.repository.get(
                2,
                256,
            )
        else:
            verse = None

        if verse is None:
            return ()

        return (
            EvidenceNode(
                evidence_id=("quranpedia:mushaf:1:" + reference),
                domain=EvidenceDomain.QURAN,
                text=verse.text_uthmani,
                source_id=("quranpedia:mushaf:1"),
                reference=reference,
                related_quran=(reference,),
                claim_type="quran_text",
            ),
        )


class UnavailableAdapter(RecordingAdapter):
    def retrieve(
        self,
        request,
    ):
        del request

        raise CompetitionSourceUnavailable("quranpedia")


def understanding():
    return BasiraQueryUnderstandingService().understand(
        "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟"
    )


def quran_target(
    references=("2:255",),
):
    return RetrievalTarget(
        domain=EvidenceDomain.QURAN,
        strategies=(RetrievalStrategy.EXACT_REFERENCE,),
        references=references,
    )


def test_exact_hard_reference_executes_as_identity():
    adapter = RecordingAdapter()

    retriever = OfficialQuranDomainRetriever(
        adapter=adapter,
    )

    nodes = retriever.retrieve(
        understanding=understanding(),
        target=quran_target(),
        limit=10,
    )

    assert len(nodes) == 1

    assert adapter.requests[0].query == "2:255"

    assert adapter.requests[0].references == ("2:255",)

    assert nodes[0].source_id == "quranpedia:mushaf:1"


def test_same_surah_range_is_expanded_deterministically():
    adapter = RecordingAdapter()

    retriever = OfficialQuranDomainRetriever(
        adapter=adapter,
    )

    nodes = retriever.retrieve(
        understanding=understanding(),
        target=quran_target(("2:255-256",)),
        limit=10,
    )

    assert [request.query for request in adapter.requests] == [
        "2:255",
        "2:256",
    ]

    assert [node.reference for node in nodes] == [
        "2:255",
        "2:256",
    ]


def test_invalid_hard_reference_never_falls_back():
    adapter = RecordingAdapter()

    retriever = OfficialQuranDomainRetriever(
        adapter=adapter,
    )

    nodes = retriever.retrieve(
        understanding=understanding(),
        target=quran_target(("2:286-3:1",)),
        limit=10,
    )

    assert nodes == ()
    assert adapter.requests == []


def test_repository_is_exposed_for_canonical_resolver():
    adapter = RecordingAdapter()

    retriever = OfficialQuranDomainRetriever(
        adapter=adapter,
    )

    assert retriever.repository is adapter.repository


def test_runs_inside_existing_basira_unified_spine():
    adapter = RecordingAdapter()

    domain = OfficialQuranDomainRetriever(
        adapter=adapter,
    )

    understood = understanding()

    plan = BasiraRetrievalPlan(
        understanding=understood,
        targets=(quran_target(),),
        context_requirement=(understood.context_requirement),
    )

    result = BasiraUnifiedRetriever(
        {
            EvidenceDomain.QURAN: domain,
        }
    ).retrieve(plan)

    assert result.unavailable_domains == frozenset()

    assert len(result.evidence) == 1

    assert result.evidence[0].reference == "2:255"


def test_source_failure_maps_to_domain_unavailable():
    adapter = UnavailableAdapter()

    domain = OfficialQuranDomainRetriever(
        adapter=adapter,
    )

    understood = understanding()

    plan = BasiraRetrievalPlan(
        understanding=understood,
        targets=(quran_target(),),
        context_requirement=(understood.context_requirement),
    )

    result = BasiraUnifiedRetriever(
        {
            EvidenceDomain.QURAN: domain,
        }
    ).retrieve(plan)

    assert result.evidence == ()

    assert result.unavailable_domains == frozenset(
        {
            EvidenceDomain.QURAN,
        }
    )
