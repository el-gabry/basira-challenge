from __future__ import annotations

import pytest

from basira.models.scholarly import (
    ScholarlyDomain,
)
from basira.sources.shamela.hierarchy import (
    ShamelaBookHierarchy,
    ShamelaBookSnapshot,
    ShamelaEvidenceSpan,
    ShamelaStructureKind,
    ShamelaStructureNode,
)

SNAPSHOT_HASH = "a" * 64
BOOK_HASH = "b" * 64


def book() -> ShamelaBookSnapshot:
    return ShamelaBookSnapshot(
        corpus_id="fixture-corpus",
        source_id="shamela-source",
        source_version="v1",
        source_snapshot_id=("fixture-snapshot-v1"),
        source_snapshot_sha256=(SNAPSHOT_HASH),
        book_id="book-1",
        work_title="كتاب البيوع",
        raw_book_sha256=BOOK_HASH,
        domain=ScholarlyDomain.FIQH,
        author_name="مؤلف",
        edition="edition-1",
        madhhab="hanafi",
        era="classical",
        discipline="fiqh",
        book_family=("classical_fiqh"),
    )


def structure(
    item: ShamelaBookSnapshot,
):
    root = ShamelaStructureNode.create(
        book=item,
        kind=(ShamelaStructureKind.BOOK),
        ordinal=0,
        title=item.work_title,
        source_locator="book",
    )

    kitab = ShamelaStructureNode.create(
        book=item,
        kind=(ShamelaStructureKind.KITAB),
        ordinal=1,
        title="كتاب البيوع",
        parent_id=root.node_id,
        source_locator=("kitab:buyu"),
    )

    bab = ShamelaStructureNode.create(
        book=item,
        kind=(ShamelaStructureKind.BAB),
        ordinal=1,
        title="باب الصرف",
        parent_id=kitab.node_id,
        source_locator=("bab:sarf"),
    )

    return root, kitab, bab


def test_structure_ids_are_deterministic() -> None:
    item = book()

    first = ShamelaStructureNode.create(
        book=item,
        kind=(ShamelaStructureKind.BAB),
        ordinal=1,
        title="باب الصرف",
        parent_id="parent",
        source_locator="bab:1",
    )

    second = ShamelaStructureNode.create(
        book=item,
        kind=(ShamelaStructureKind.BAB),
        ordinal=1,
        title="باب الصرف",
        parent_id="parent",
        source_locator="bab:1",
    )

    assert first.node_id == second.node_id


def test_span_id_binds_text_and_location() -> None:
    item = book()
    root, kitab, bab = structure(item)

    one = ShamelaEvidenceSpan.create(
        book=item,
        parent_id=bab.node_id,
        ordinal=1,
        raw_text="نص فقهي",
        source_locator="page:10:span:1",
        page_start="10",
    )

    same = ShamelaEvidenceSpan.create(
        book=item,
        parent_id=bab.node_id,
        ordinal=1,
        raw_text="نص فقهي",
        source_locator="page:10:span:1",
        page_start="10",
    )

    moved = ShamelaEvidenceSpan.create(
        book=item,
        parent_id=bab.node_id,
        ordinal=1,
        raw_text="نص فقهي",
        source_locator=("page:11:span:1"),
        page_start="11",
    )

    changed = ShamelaEvidenceSpan.create(
        book=item,
        parent_id=bab.node_id,
        ordinal=1,
        raw_text="نص فقهي مختلف",
        source_locator=("page:10:span:1"),
        page_start="10",
    )

    assert one.span_id == same.span_id
    assert one.span_id != moved.span_id
    assert one.span_id != changed.span_id


def test_exact_raw_text_is_preserved() -> None:
    item = book()
    _, _, bab = structure(item)

    raw = "النص  كما هو\nمن المصدر"

    span = ShamelaEvidenceSpan.create(
        book=item,
        parent_id=bab.node_id,
        ordinal=1,
        raw_text=raw,
        source_locator="p:1",
    )

    assert span.raw_text == raw


def test_missing_parent_fails_closed() -> None:
    item = book()
    root, _, _ = structure(item)

    span = ShamelaEvidenceSpan.create(
        book=item,
        parent_id="missing-parent",
        ordinal=1,
        raw_text="نص",
        source_locator="p:1",
    )

    with pytest.raises(
        ValueError,
        match="missing structural parent",
    ):
        ShamelaBookHierarchy(
            book=item,
            nodes=(root,),
            spans=(span,),
        )


def test_hierarchy_builds_context_envelope() -> None:
    item = book()
    root, kitab, bab = structure(item)

    first = ShamelaEvidenceSpan.create(
        book=item,
        parent_id=bab.node_id,
        ordinal=1,
        raw_text="النص الأول",
        source_locator="p:10:1",
        page_start="10",
    )

    second_seed = ShamelaEvidenceSpan.create(
        book=item,
        parent_id=bab.node_id,
        ordinal=2,
        raw_text="النص الثاني",
        source_locator="p:10:2",
        page_start="10",
        previous_span_id=(first.span_id),
    )

    first_linked = ShamelaEvidenceSpan(
        span_id=first.span_id,
        book_id=first.book_id,
        parent_id=first.parent_id,
        ordinal=first.ordinal,
        raw_text=first.raw_text,
        raw_text_sha256=(first.raw_text_sha256),
        source_locator=(first.source_locator),
        page_start=(first.page_start),
        page_end=first.page_end,
        next_span_id=(second_seed.span_id),
    )

    hierarchy = ShamelaBookHierarchy(
        book=item,
        nodes=(
            root,
            kitab,
            bab,
        ),
        spans=(
            first_linked,
            second_seed,
        ),
    )

    envelope = hierarchy.context_envelope(first_linked.span_id)

    assert envelope.ancestor_titles == (
        "كتاب البيوع",
        "كتاب البيوع",
        "باب الصرف",
    )

    assert envelope.next_span_id == second_seed.span_id


def test_span_becomes_attributed_scholarly_passage() -> None:
    item = book()
    root, kitab, bab = structure(item)

    span = ShamelaEvidenceSpan.create(
        book=item,
        parent_id=bab.node_id,
        ordinal=1,
        raw_text=("يشترط التقابض في مسائل الصرف"),
        source_locator="p:212:1",
        page_start="212",
    )

    hierarchy = ShamelaBookHierarchy(
        book=item,
        nodes=(
            root,
            kitab,
            bab,
        ),
        spans=(span,),
    )

    passage = hierarchy.to_scholarly_passage(span.span_id)

    assert passage.text == ("يشترط التقابض في مسائل الصرف")

    assert passage.work_title == "كتاب البيوع"

    assert passage.author_name == "مؤلف"

    assert passage.chapter_title == "باب الصرف"

    assert passage.page == "212"

    assert passage.metadata["raw_book_sha256"] == BOOK_HASH

    assert passage.metadata["raw_text_sha256"] == span.raw_text_sha256

    assert passage.metadata["structural_parent_id"] == bab.node_id


def test_invalid_raw_text_hash_fails() -> None:
    item = book()
    _, _, bab = structure(item)

    with pytest.raises(
        ValueError,
        match="raw_text_sha256",
    ):
        ShamelaEvidenceSpan(
            span_id="span",
            book_id=item.book_id,
            parent_id=bab.node_id,
            ordinal=0,
            raw_text="النص",
            raw_text_sha256=("0" * 64),
            source_locator="p:1",
        )


def test_book_and_source_snapshot_hashes_are_distinct() -> None:
    item = book()

    assert item.raw_book_sha256 != item.source_snapshot_sha256
