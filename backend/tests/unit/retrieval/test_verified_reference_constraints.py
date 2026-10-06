from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.models.quran import (
    QuranVerse,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.quran_reference import (
    expand_quran_reference,
)
from basira.retrieval.quran_retriever import (
    QuranDomainRetriever,
)
from basira.retrieval.retrieval_plan import (
    RetrievalStrategy,
    RetrievalTarget,
)
from basira.retrieval.revelation_context_retriever import (
    RevelationContextRetriever,
)
from basira.retrieval.tafsir_retriever import (
    TafsirDomainRetriever,
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
        runtime_use,
    ) -> bool:
        del source_id
        del runtime_use
        return True


def quran_repository() -> QuranRepository:
    return QuranRepository(
        (
            QuranVerse(
                source_id="quran",
                surah_number=2,
                ayah_number=43,
                text_uthmani=("وَأَقِيمُوا الصَّلَاةَ"),
                text_search=("واقيموا الصلاة"),
            ),
            QuranVerse(
                source_id="quran",
                surah_number=2,
                ayah_number=255,
                text_uthmani=("وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالْأَرْضَ"),
                text_search=("وسع كرسيه السماوات والارض"),
            ),
        )
    )


def passage(
    *,
    passage_id: str,
    source_id: str,
    domain: ScholarlyDomain,
    surah: int,
    ayah: int,
    text: str,
) -> ScholarlyPassage:
    return ScholarlyPassage(
        passage_id=passage_id,
        source_id=source_id,
        domain=domain,
        work_id=source_id,
        work_title=source_id,
        text=text,
        surah_number=surah,
        ayah_start=ayah,
        ayah_end=ayah,
    )


def test_execution_reference_parser_normalizes_and_bounds() -> None:
    assert expand_quran_reference("٢/٢٥٥") == ((2, 255),)

    assert expand_quran_reference("2:255-257") == (
        (2, 255),
        (2, 256),
        (2, 257),
    )

    assert expand_quran_reference("2:286-3:1") is None


def test_quran_verified_reference_beats_conflicting_query() -> None:
    understanding = BasiraQueryUnderstandingService().understand("ما معنى الآية 2:43؟")

    target = RetrievalTarget(
        domain=EvidenceDomain.QURAN,
        strategies=(RetrievalStrategy.EXACT_REFERENCE,),
        references=("2:255",),
    )

    evidence = QuranDomainRetriever(
        repository=quran_repository(),
        runtime=AllowAllRuntime(),  # type: ignore[arg-type]
    ).retrieve(
        understanding=understanding,
        target=target,
    )

    assert len(evidence) == 1
    assert evidence[0].reference == "2:255"


def test_tafsir_verified_reference_excludes_wrong_verse_before_ranking() -> None:
    repository = ScholarlyRepository(
        (
            passage(
                passage_id="a:2:255",
                source_id="a",
                domain=(ScholarlyDomain.TAFSIR),
                surah=2,
                ayah=255,
                text=("الكرسي في هذه الآية له بيان في التفسير"),
            ),
            passage(
                passage_id="b:2:255",
                source_id="b",
                domain=(ScholarlyDomain.TAFSIR),
                surah=2,
                ayah=255,
                text=("بيان معنى الآية وسياقها"),
            ),
            passage(
                passage_id="wrong:2:43",
                source_id="wrong",
                domain=(ScholarlyDomain.TAFSIR),
                surah=2,
                ayah=43,
                text=("الكرسي الكرسي الكرسي نص شديد التطابق"),
            ),
        )
    )

    understanding = BasiraQueryUnderstandingService().understand("ما معنى الكرسي؟")

    target = RetrievalTarget(
        domain=EvidenceDomain.TAFSIR,
        strategies=(
            RetrievalStrategy.EXACT_REFERENCE,
            RetrievalStrategy.LEXICAL_FALLBACK,
        ),
        references=("2:255",),
    )

    evidence = TafsirDomainRetriever(repository=repository).retrieve(
        understanding=understanding,
        target=target,
    )

    assert evidence

    assert all(node.reference == "2:255" for node in evidence)

    assert evidence[0].evidence_id == "a:2:255"

    assert {node.evidence_id for node in evidence} == {
        "a:2:255",
        "b:2:255",
    }


def test_tafsir_invalid_execution_reference_never_falls_back_to_query() -> None:
    repository = ScholarlyRepository(
        (
            passage(
                passage_id="wrong:2:43",
                source_id="wrong",
                domain=(ScholarlyDomain.TAFSIR),
                surah=2,
                ayah=43,
                text="تفسير 2:43",
            ),
        )
    )

    understanding = BasiraQueryUnderstandingService().understand("ما معنى الآية 2:43؟")

    target = RetrievalTarget(
        domain=EvidenceDomain.TAFSIR,
        strategies=(RetrievalStrategy.EXACT_REFERENCE,),
        references=("not-a-quran-reference",),
    )

    evidence = TafsirDomainRetriever(repository=repository).retrieve(
        understanding=understanding,
        target=target,
    )

    assert evidence == ()


def test_revelation_context_verified_reference_beats_conflicting_query() -> None:
    repository = ScholarlyRepository(
        (
            passage(
                passage_id="context:2:255",
                source_id="context",
                domain=(ScholarlyDomain.REVELATION_CONTEXT),
                surah=2,
                ayah=255,
                text="record for 2:255",
            ),
            passage(
                passage_id="context:58:1",
                source_id="context",
                domain=(ScholarlyDomain.REVELATION_CONTEXT),
                surah=58,
                ayah=1,
                text="record for 58:1",
            ),
        )
    )

    understanding = BasiraQueryUnderstandingService().understand(
        "ما سبب نزول الآية 58:1؟"
    )

    target = RetrievalTarget(
        domain=(EvidenceDomain.REVELATION_CONTEXT),
        strategies=(RetrievalStrategy.EXACT_REFERENCE,),
        references=("2:255",),
    )

    evidence = RevelationContextRetriever(repository=repository).retrieve(
        understanding=understanding,
        target=target,
    )

    assert len(evidence) == 1
    assert evidence[0].evidence_id == "context:2:255"
    assert evidence[0].reference == "2:255"


def test_revelation_invalid_execution_reference_fails_closed() -> None:
    repository = ScholarlyRepository(
        (
            passage(
                passage_id="context:58:1",
                source_id="context",
                domain=(ScholarlyDomain.REVELATION_CONTEXT),
                surah=58,
                ayah=1,
                text="record for 58:1",
            ),
        )
    )

    understanding = BasiraQueryUnderstandingService().understand(
        "ما سبب نزول الآية 58:1؟"
    )

    target = RetrievalTarget(
        domain=(EvidenceDomain.REVELATION_CONTEXT),
        strategies=(RetrievalStrategy.EXACT_REFERENCE,),
        references=("bad-reference",),
    )

    evidence = RevelationContextRetriever(repository=repository).retrieve(
        understanding=understanding,
        target=target,
    )

    assert evidence == ()
