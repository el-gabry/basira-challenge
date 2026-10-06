import pytest

from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.sources.scholarly.repository import (
    ScholarlyRepository,
)


def make_passage(
    *,
    passage_id: str,
    source_id: str,
    domain: ScholarlyDomain,
    surah: int,
    ayah: int,
) -> ScholarlyPassage:
    return ScholarlyPassage(
        passage_id=passage_id,
        source_id=source_id,
        domain=domain,
        work_id=source_id,
        work_title=source_id,
        text=f"text:{passage_id}",
        surah_number=surah,
        ayah_start=ayah,
        ayah_end=ayah,
    )


def test_find_by_quran_reference_returns_all_roles() -> None:
    repository = ScholarlyRepository(
        (
            make_passage(
                passage_id="katheer:58:1",
                source_id="katheer",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
                surah=58,
                ayah=1,
            ),
            make_passage(
                passage_id="saadi:58:1",
                source_id="saadi",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
                surah=58,
                ayah=1,
            ),
            make_passage(
                passage_id="mokhtasar:58:1",
                source_id="mokhtasar",
                domain=(
                    ScholarlyDomain.TAFSIR
                ),
                surah=58,
                ayah=1,
            ),
            make_passage(
                passage_id="nozool:58:1",
                source_id="nozool",
                domain=(
                    ScholarlyDomain
                    .REVELATION_CONTEXT
                ),
                surah=58,
                ayah=1,
            ),
        )
    )

    passages = (
        repository
        .find_by_quran_reference(
            58,
            1,
        )
    )

    assert len(passages) == 4

    tafsir = (
        repository
        .find_by_quran_reference(
            58,
            1,
            domain=(
                ScholarlyDomain.TAFSIR
            ),
        )
    )

    assert len(tafsir) == 3

    revelation = (
        repository
        .find_by_quran_reference(
            58,
            1,
            domain=(
                ScholarlyDomain
                .REVELATION_CONTEXT
            ),
        )
    )

    assert len(revelation) == 1


def test_duplicate_passage_ids_fail_closed() -> None:
    passage = make_passage(
        passage_id="duplicate",
        source_id="source",
        domain=(
            ScholarlyDomain.TAFSIR
        ),
        surah=2,
        ayah=255,
    )

    with pytest.raises(
        ValueError,
        match="Duplicate scholarly passage",
    ):
        ScholarlyRepository(
            (
                passage,
                passage,
            )
        )
