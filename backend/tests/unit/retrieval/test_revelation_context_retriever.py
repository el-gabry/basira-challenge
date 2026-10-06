from dataclasses import dataclass

from basira.evidence.models import EvidenceDomain
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.retrieval.retrieval_plan import (
    RetrievalStrategy,
    RetrievalTarget,
)
from basira.retrieval.revelation_context_retriever import (
    RevelationContextRetriever,
)
from basira.sources.scholarly.repository import (
    ScholarlyRepository,
)


@dataclass(frozen=True, slots=True)
class FakeEntity:
    entity_type: str
    value: str


@dataclass(frozen=True, slots=True)
class FakeUnderstanding:
    entities: tuple[FakeEntity, ...]


def make_understanding(
    surah: int,
    ayah: int,
) -> FakeUnderstanding:
    return FakeUnderstanding(
        entities=(
            FakeEntity(
                entity_type="surah_number",
                value=str(surah),
            ),
            FakeEntity(
                entity_type="ayah_number",
                value=str(ayah),
            ),
        )
    )


def make_target() -> RetrievalTarget:
    return RetrievalTarget(
        domain=EvidenceDomain.REVELATION_CONTEXT,
        strategies=(
            RetrievalStrategy.EXACT_REFERENCE,
        ),
    )


def test_retrieves_revelation_context_when_attested() -> None:
    repository = ScholarlyRepository(
        (
            ScholarlyPassage(
                passage_id="nozool:58:1",
                source_id="nozool",
                domain=(
                    ScholarlyDomain.REVELATION_CONTEXT
                ),
                work_id="ayat-nozool",
                work_title="صحيح أسباب النزول",
                text="نص سبب النزول.",
                surah_number=58,
                ayah_start=1,
                ayah_end=1,
            ),
            ScholarlyPassage(
                passage_id="tafsir:58:1",
                source_id="tafsir",
                domain=ScholarlyDomain.TAFSIR,
                work_id="tafsir",
                work_title="tafsir",
                text="نص التفسير.",
                surah_number=58,
                ayah_start=1,
                ayah_end=1,
            ),
        )
    )

    retriever = RevelationContextRetriever(
        repository=repository
    )

    evidence = retriever.retrieve(
        understanding=make_understanding(
            58,
            1,
        ),  # type: ignore[arg-type]
        target=make_target(),
    )

    assert len(evidence) == 1

    assert (
        evidence[0].domain
        == EvidenceDomain.REVELATION_CONTEXT
    )

    assert evidence[0].reference == "58:1"


def test_returns_empty_when_no_entry_is_attested() -> None:
    repository = ScholarlyRepository(
        (
            ScholarlyPassage(
                passage_id="nozool:58:1",
                source_id="nozool",
                domain=(
                    ScholarlyDomain.REVELATION_CONTEXT
                ),
                work_id="ayat-nozool",
                work_title="صحيح أسباب النزول",
                text="نص سبب النزول.",
                surah_number=58,
                ayah_start=1,
                ayah_end=1,
            ),
        )
    )

    retriever = RevelationContextRetriever(
        repository=repository
    )

    evidence = retriever.retrieve(
        understanding=make_understanding(
            2,
            255,
        ),  # type: ignore[arg-type]
        target=make_target(),
    )

    assert evidence == ()
