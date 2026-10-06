from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.retrieval.scholarly_lexical import (
    ScholarlyLexicalIndex,
)


def passage(
    *,
    passage_id: str,
    source_id: str,
    text: str,
) -> ScholarlyPassage:
    return ScholarlyPassage(
        passage_id=passage_id,
        source_id=source_id,
        domain=ScholarlyDomain.TAFSIR,
        work_id=source_id,
        work_title=source_id,
        text=text,
        surah_number=2,
        ayah_start=1,
        ayah_end=1,
    )


def test_lexical_index_returns_relevant_passage() -> None:
    index = ScholarlyLexicalIndex(
        (
            passage(
                passage_id="a:1",
                source_id="source-a",
                text=(
                    "الصبر عند البلاء من "
                    "الأخلاق العظيمة"
                ),
            ),
            passage(
                passage_id="b:1",
                source_id="source-b",
                text=(
                    "أحكام المواريث "
                    "وتقسيم التركة"
                ),
            ),
        )
    )

    hits = index.search(
        "ماذا يقول الإسلام عن الصبر؟"
    )

    assert hits
    assert (
        hits[0].passage.passage_id
        == "a:1"
    )


def test_lexical_index_balances_sources() -> None:
    index = ScholarlyLexicalIndex(
        (
            passage(
                passage_id="a:1",
                source_id="source-a",
                text=(
                    "الصبر الصبر الصبر "
                    "عند البلاء"
                ),
            ),
            passage(
                passage_id="a:2",
                source_id="source-a",
                text=(
                    "الصبر الصبر "
                    "في الشدائد"
                ),
            ),
            passage(
                passage_id="b:1",
                source_id="source-b",
                text=(
                    "الصبر عند الشدة"
                ),
            ),
        )
    )

    hits = index.search(
        "الصبر",
        limit=2,
    )

    assert len(hits) == 2

    assert {
        hit.passage.source_id
        for hit in hits
    } == {
        "source-a",
        "source-b",
    }


def test_lexical_index_returns_empty_without_overlap() -> None:
    index = ScholarlyLexicalIndex(
        (
            passage(
                passage_id="a:1",
                source_id="source-a",
                text="الصبر عند البلاء",
            ),
        )
    )

    assert (
        index.search(
            "المواريث"
        )
        == ()
    )


def test_long_passage_uses_children_but_returns_parent_once() -> None:
    parent_text = " ".join(
        (
            *("تمهيد" for _ in range(12)),
            "الصبر",
            "الثبات",
            *("تفصيل" for _ in range(12)),
            "الصبر",
            "الثبات",
            *("خاتمة" for _ in range(12)),
        )
    )

    parent = passage(
        passage_id="a:long",
        source_id="source-a",
        text=parent_text,
    )

    index = ScholarlyLexicalIndex(
        (parent,),
        child_chunk_size=8,
        child_chunk_overlap=2,
    )

    hits = index.search(
        "الصبر الثبات",
        limit=10,
    )

    assert len(index) == 1
    assert index.child_document_count > 1
    assert len(hits) == 1
    assert hits[0].passage is parent
    assert hits[0].passage.text == parent_text


def test_child_ranking_collapses_before_source_balancing() -> None:
    index = ScholarlyLexicalIndex(
        (
            passage(
                passage_id="a:long",
                source_id="source-a",
                text=" ".join(
                    (
                        *("تمهيد" for _ in range(10)),
                        "الصبر",
                        "الثبات",
                        *("تفصيل" for _ in range(10)),
                        "الصبر",
                        "الثبات",
                    )
                ),
            ),
            passage(
                passage_id="b:short",
                source_id="source-b",
                text="الصبر والثبات",
            ),
        ),
        child_chunk_size=6,
        child_chunk_overlap=2,
    )

    hits = index.search(
        "الصبر الثبات",
        limit=10,
    )

    assert len(hits) == 2
    assert {
        hit.passage.passage_id
        for hit in hits
    } == {
        "a:long",
        "b:short",
    }


def test_child_chunk_configuration_is_validated() -> None:
    parent = passage(
        passage_id="a:1",
        source_id="source-a",
        text="الصبر عند البلاء",
    )

    try:
        ScholarlyLexicalIndex(
            (parent,),
            child_chunk_size=4,
            child_chunk_overlap=4,
        )
    except ValueError as error:
        assert (
            "child_chunk_overlap"
            in str(error)
        )
    else:
        raise AssertionError(
            "Expected invalid child overlap to fail."
        )
