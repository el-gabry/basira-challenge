from dataclasses import dataclass

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import (
    RetrievalStrategy,
    RetrievalTarget,
)
from basira.retrieval.tafsir_retriever import (
    TafsirDomainRetriever,
)
from basira.sources.scholarly.repository import (
    ScholarlyRepository,
)


@dataclass(
    frozen=True,
    slots=True,
)
class FakeEntity:
    entity_type: str
    value: str


@dataclass(
    frozen=True,
    slots=True,
)
class FakeUnderstanding:
    entities: tuple[
        FakeEntity,
        ...,
    ]


def make_passage(
    *,
    passage_id: str,
    source_id: str,
    domain: ScholarlyDomain,
) -> ScholarlyPassage:
    return ScholarlyPassage(
        passage_id=passage_id,
        source_id=source_id,
        domain=domain,
        work_id=source_id,
        work_title=source_id,
        text=f"text:{passage_id}",
        surah_number=2,
        ayah_start=255,
        ayah_end=255,
    )


def test_retrieves_only_tafsir_for_exact_anchor() -> None:
    repository = ScholarlyRepository(
        (
            make_passage(
                passage_id="katheer:2:255",
                source_id="katheer",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
            ),
            make_passage(
                passage_id="saadi:2:255",
                source_id="saadi",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
            ),
            make_passage(
                passage_id="mokhtasar:2:255",
                source_id="mokhtasar",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
            ),
            make_passage(
                passage_id="nozool:2:255",
                source_id="nozool",
                domain=(
                    ScholarlyDomain
                    .REVELATION_CONTEXT
                ),
            ),
        )
    )

    retriever = TafsirDomainRetriever(
        repository=repository
    )

    understanding = FakeUnderstanding(
        entities=(
            FakeEntity(
                entity_type="surah_number",
                value="2",
            ),
            FakeEntity(
                entity_type="ayah_number",
                value="255",
            ),
        )
    )

    target = RetrievalTarget(
        domain=EvidenceDomain.TAFSIR,
        strategies=(
            RetrievalStrategy
            .EXACT_REFERENCE,
        ),
    )

    evidence = retriever.retrieve(
        understanding=understanding,  # type: ignore[arg-type]
        target=target,
    )

    assert len(evidence) == 3

    assert all(
        node.domain
        == EvidenceDomain.TAFSIR
        for node in evidence
    )

    assert all(
        node.reference == "2:255"
        for node in evidence
    )


def test_returns_empty_without_quran_anchor() -> None:
    repository = ScholarlyRepository(
        ()
    )

    retriever = TafsirDomainRetriever(
        repository=repository
    )

    understanding = FakeUnderstanding(
        entities=()
    )

    target = RetrievalTarget(
        domain=EvidenceDomain.TAFSIR,
        strategies=(
            RetrievalStrategy
            .EXACT_REFERENCE,
        ),
    )

    evidence = retriever.retrieve(
        understanding=understanding,  # type: ignore[arg-type]
        target=target,
    )

    assert evidence == ()


def test_conceptual_query_uses_lexical_fallback() -> None:
    repository = ScholarlyRepository(
        (
            ScholarlyPassage(
                passage_id="source-a:2:153",
                source_id="source-a",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
                work_id="source-a",
                work_title="source-a",
                text=(
                    "الصبر عند البلاء "
                    "من الأخلاق العظيمة"
                ),
                surah_number=2,
                ayah_start=153,
                ayah_end=153,
            ),
            ScholarlyPassage(
                passage_id="source-b:3:200",
                source_id="source-b",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
                work_id="source-b",
                work_title="source-b",
                text=(
                    "ورد في التفسير "
                    "فضل الصبر والثبات"
                ),
                surah_number=3,
                ayah_start=200,
                ayah_end=200,
            ),
        )
    )

    retriever = TafsirDomainRetriever(
        repository=repository
    )

    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ماذا يقول الإسلام عن الصبر؟"
        )
    )

    target = RetrievalTarget(
        domain=EvidenceDomain.TAFSIR,
        strategies=(
            RetrievalStrategy
            .LEXICAL_FALLBACK,
        ),
    )

    evidence = retriever.retrieve(
        understanding=understanding,
        target=target,
        limit=2,
    )

    assert len(evidence) == 2

    assert {
        node.source_id
        for node in evidence
    } == {
        "source-a",
        "source-b",
    }


def test_conceptual_index_respects_configured_sources() -> None:
    repository = ScholarlyRepository(
        (
            ScholarlyPassage(
                passage_id="allowed:2:153",
                source_id="allowed",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
                work_id="allowed",
                work_title="allowed",
                text="الصبر عند البلاء",
                surah_number=2,
                ayah_start=153,
                ayah_end=153,
            ),
            ScholarlyPassage(
                passage_id="denied:3:200",
                source_id="denied",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
                work_id="denied",
                work_title="denied",
                text="الصبر عند البلاء",
                surah_number=3,
                ayah_start=200,
                ayah_end=200,
            ),
        )
    )

    retriever = TafsirDomainRetriever(
        repository=repository,
        source_ids=("allowed",),
    )

    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ماذا يقول الإسلام عن الصبر؟"
        )
    )

    target = RetrievalTarget(
        domain=EvidenceDomain.TAFSIR,
        strategies=(
            RetrievalStrategy
            .LEXICAL_FALLBACK,
        ),
    )

    evidence = retriever.retrieve(
        understanding=understanding,
        target=target,
    )

    assert len(evidence) == 1
    assert evidence[0].source_id == "allowed"


def test_exact_anchor_precedes_lexical_fallback() -> None:
    repository = ScholarlyRepository(
        (
            ScholarlyPassage(
                passage_id="anchor:2:255",
                source_id="anchor",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
                work_id="anchor",
                work_title="anchor",
                text="تفسير آية الكرسي",
                surah_number=2,
                ayah_start=255,
                ayah_end=255,
            ),
            ScholarlyPassage(
                passage_id="other:3:1",
                source_id="other",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
                work_id="other",
                work_title="other",
                text=(
                    "تفسير آية الكرسي "
                    "نص آخر"
                ),
                surah_number=3,
                ayah_start=1,
                ayah_end=1,
            ),
        )
    )

    retriever = TafsirDomainRetriever(
        repository=repository
    )

    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما معنى الآية 2:255؟"
        )
    )

    target = RetrievalTarget(
        domain=EvidenceDomain.TAFSIR,
        strategies=(
            RetrievalStrategy
            .EXACT_REFERENCE,
            RetrievalStrategy
            .LEXICAL_FALLBACK,
        ),
    )

    evidence = retriever.retrieve(
        understanding=understanding,
        target=target,
    )

    assert len(evidence) == 1
    assert (
        evidence[0].evidence_id
        == "anchor:2:255"
    )


def test_conceptual_child_hit_returns_full_parent_evidence() -> None:
    parent_text = " ".join(
        (
            *("مقدمة" for _ in range(190)),
            "الصبر",
            "عند",
            "البلاء",
            *("تفصيل" for _ in range(30)),
        )
    )

    repository = ScholarlyRepository(
        (
            ScholarlyPassage(
                passage_id="source-a:2:153",
                source_id="source-a",
                domain=ScholarlyDomain.TAFSIR,
                work_id="source-a",
                work_title="source-a",
                text=parent_text,
                surah_number=2,
                ayah_start=153,
                ayah_end=153,
            ),
        )
    )

    retriever = TafsirDomainRetriever(
        repository=repository
    )

    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ماذا يقول الإسلام عن الصبر؟"
        )
    )

    target = RetrievalTarget(
        domain=EvidenceDomain.TAFSIR,
        strategies=(
            RetrievalStrategy
            .LEXICAL_FALLBACK,
        ),
    )

    evidence = retriever.retrieve(
        understanding=understanding,
        target=target,
    )

    assert len(evidence) == 1
    assert (
        evidence[0].evidence_id
        == "source-a:2:153"
    )
    assert evidence[0].text == parent_text
