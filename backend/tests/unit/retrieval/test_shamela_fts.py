from __future__ import annotations

from pathlib import Path

from basira.models.scholarly import (
    ScholarlyDomain,
)
from basira.retrieval.shamela_fts import (
    ShamelaFtsIndex,
)
from basira.sources.shamela.hierarchy import (
    ShamelaBookHierarchy,
    ShamelaBookSnapshot,
    ShamelaEvidenceSpan,
    ShamelaStructureKind,
    ShamelaStructureNode,
)


def hierarchy(
    *,
    source_id: str,
    book_id: str,
    title: str,
    madhhab: str,
    bab_title: str,
    text: str,
) -> ShamelaBookHierarchy:
    book = ShamelaBookSnapshot(
        corpus_id="fixture",
        source_id=source_id,
        source_version="v1",
        source_snapshot_id=(f"snapshot-{book_id}"),
        source_snapshot_sha256=("a" * 64),
        book_id=book_id,
        work_title=title,
        raw_book_sha256=(("b" if book_id == "1" else "c") * 64),
        domain=ScholarlyDomain.FIQH,
        author_name="مؤلف",
        madhhab=madhhab,
        discipline="fiqh",
        book_family=("classical_fiqh"),
    )

    root = ShamelaStructureNode.create(
        book=book,
        kind=(ShamelaStructureKind.BOOK),
        ordinal=0,
        title=title,
        source_locator="book",
    )

    kitab = ShamelaStructureNode.create(
        book=book,
        kind=(ShamelaStructureKind.KITAB),
        ordinal=1,
        title="كتاب البيوع",
        parent_id=root.node_id,
        source_locator="kitab:1",
    )

    bab = ShamelaStructureNode.create(
        book=book,
        kind=(ShamelaStructureKind.BAB),
        ordinal=1,
        title=bab_title,
        parent_id=kitab.node_id,
        source_locator="bab:1",
    )

    span = ShamelaEvidenceSpan.create(
        book=book,
        parent_id=bab.node_id,
        ordinal=1,
        raw_text=text,
        source_locator="page:1:body:0:100",
        page_start="1",
    )

    return ShamelaBookHierarchy(
        book=book,
        nodes=(
            root,
            kitab,
            bab,
        ),
        spans=(span,),
    )


def build_index(
    tmp_path: Path,
) -> ShamelaFtsIndex:
    hanafi = hierarchy(
        source_id="hanafi-source",
        book_id="1",
        title="كتاب حنفي",
        madhhab="hanafi",
        bab_title="باب الصرف",
        text=("يشترط القبض في بعض صور المعاوضات المالية"),
    )

    maliki = hierarchy(
        source_id="maliki-source",
        book_id="2",
        title="كتاب مالكي",
        madhhab="maliki",
        bab_title="باب الطهارة",
        text=("الماء المطلق طهور في أحكام الطهارة"),
    )

    return ShamelaFtsIndex.build(
        tmp_path / "shamela.sqlite3",
        (
            hanafi,
            maliki,
        ),
        window_size=4,
        window_overlap=1,
    )


def test_search_returns_original_parent_text(
    tmp_path: Path,
) -> None:
    index = build_index(tmp_path)

    hits = index.search(
        "القبض",
        limit=5,
    )

    assert hits

    assert hits[0].passage.text == ("يشترط القبض في بعض صور المعاوضات المالية")


def test_title_path_is_searchable(
    tmp_path: Path,
) -> None:
    index = build_index(tmp_path)

    hits = index.search(
        "الصرف",
        limit=5,
    )

    assert hits

    assert hits[0].passage.work_id == "1"


def test_madhhab_filter_is_structural(
    tmp_path: Path,
) -> None:
    index = build_index(tmp_path)

    hits = index.search(
        "كتاب",
        limit=10,
        madhhabs=("maliki",),
    )

    assert hits

    assert {hit.passage.metadata["madhhab"] for hit in hits} == {"maliki"}


def test_domain_filter_is_structural(
    tmp_path: Path,
) -> None:
    index = build_index(tmp_path)

    hits = index.search(
        "الطهارة",
        domains=(ScholarlyDomain.FIQH,),
    )

    assert hits

    assert all(hit.passage.domain is ScholarlyDomain.FIQH for hit in hits)


def test_retrieval_windows_collapse_to_parent(
    tmp_path: Path,
) -> None:
    item = hierarchy(
        source_id="source",
        book_id="1",
        title="كتاب",
        madhhab="hanafi",
        bab_title="باب",
        text=(
            "البيع المال القبض الصرف البيع المال القبض الصرف البيع المال القبض الصرف"
        ),
    )

    index = ShamelaFtsIndex.build(
        tmp_path / "windows.sqlite3",
        (item,),
        window_size=4,
        window_overlap=2,
    )

    assert index.stats.window_count > index.stats.passage_count

    hits = index.search(
        "الصرف",
        limit=10,
    )

    assert len(hits) == 1


def test_search_normalization_removes_diacritics(
    tmp_path: Path,
) -> None:
    index = build_index(tmp_path)

    hits = index.search(
        "الطَّهَارَة",
    )

    assert hits

    assert hits[0].passage.work_id == "2"


def test_metadata_and_index_fingerprints_exist(
    tmp_path: Path,
) -> None:
    index = build_index(tmp_path)

    stats = index.stats

    assert stats.book_count == 2
    assert stats.passage_count == 2
    assert stats.window_count >= 2

    assert len(stats.corpus_fingerprint) == 64

    assert len(stats.index_fingerprint) == 64


def test_empty_query_returns_no_hits(
    tmp_path: Path,
) -> None:
    index = build_index(tmp_path)

    assert index.search("ما هو؟") == ()


def test_excluded_madhhab_filter_is_structural(
    tmp_path: Path,
) -> None:
    index = build_index(tmp_path)

    hits = index.search(
        "كتاب",
        limit=10,
        excluded_madhhabs=("hanafi",),
    )

    assert hits

    assert all(hit.passage.metadata.get("madhhab") != "hanafi" for hit in hits)
