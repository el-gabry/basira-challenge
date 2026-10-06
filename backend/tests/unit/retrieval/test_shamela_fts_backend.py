from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from basira.evidence.models import (
    ContextRequirement,
)
from basira.models.scholarly import (
    ScholarlyDomain,
)
from basira.reasoning.routing import (
    ReligiousReasoningRouter,
)
from basira.retrieval.arabic_query import (
    build_arabic_query,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
)
from basira.retrieval.shamela_fts import (
    ShamelaFtsIndex,
)
from basira.retrieval.shamela_fts_backend import (
    ShamelaFtsBackend,
)
from basira.retrieval.shamela_scout import (
    ShamelaHybridEvidenceScout,
    ShamelaScoutPlanner,
    ShamelaScoutStopReason,
)
from basira.sources.shamela.hierarchy import (
    ShamelaBookHierarchy,
    ShamelaBookSnapshot,
    ShamelaEvidenceSpan,
    ShamelaStructureKind,
    ShamelaStructureNode,
)


def understanding(
    text: str,
) -> BasiraQueryUnderstanding:
    return BasiraQueryUnderstanding(
        query=build_arabic_query(text),
        primary_intent=(BasiraIntent.FIQH_QUESTION),
        risk_tags=frozenset(),
        entities=(),
        context_requirement=(ContextRequirement()),
        confidence=1.0,
    )


def route(
    text: str,
):
    return ReligiousReasoningRouter().route(understanding(text))


def hierarchy(
    *,
    source_id: str,
    book_id: str,
    title: str,
    madhhab: str,
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
        title="باب البيع",
        parent_id=kitab.node_id,
        source_locator="bab:1",
    )

    span = ShamelaEvidenceSpan.create(
        book=book,
        parent_id=bab.node_id,
        ordinal=1,
        raw_text=text,
        source_locator=("page:1:body:0:100"),
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


def build_backend(
    tmp_path: Path,
) -> ShamelaFtsBackend:
    hanafi = hierarchy(
        source_id="hanafi-source",
        book_id="1",
        title="كتاب حنفي",
        madhhab="hanafi",
        text=("البيع في المذهب الحنفي له شروط والقبض معتبر"),
    )

    maliki = hierarchy(
        source_id="maliki-source",
        book_id="2",
        title="كتاب مالكي",
        madhhab="maliki",
        text=("البيع في المذهب المالكي له أحكام وشروط"),
    )

    index = ShamelaFtsIndex.build(
        tmp_path / "shamela.sqlite3",
        (
            hanafi,
            maliki,
        ),
        window_size=8,
        window_overlap=2,
    )

    return ShamelaFtsBackend(index)


def initial_task(
    text: str,
):
    plan = ShamelaScoutPlanner().build(route(text))

    assert plan.initial_tasks

    return plan.initial_tasks[0]


def test_backend_returns_governed_search_hit(
    tmp_path: Path,
) -> None:
    backend = build_backend(tmp_path)

    task = initial_task("ما حكم البيع؟")

    hits = backend.search(
        task,
        limit=5,
    )

    assert hits

    first = hits[0]

    assert first.identity.book_id in {
        "1",
        "2",
    }

    assert first.parent_context == "باب البيع"

    assert first.passage.text in {
        ("البيع في المذهب الحنفي له شروط والقبض معتبر"),
        ("البيع في المذهب المالكي له أحكام وشروط"),
    }


def test_requested_madhhab_is_applied(
    tmp_path: Path,
) -> None:
    backend = build_backend(tmp_path)

    task = initial_task("ما حكم البيع؟")

    task = replace(
        task,
        requested_madhhabs=("maliki",),
        excluded_madhhabs=(),
    )

    hits = backend.search(
        task,
        limit=10,
    )

    assert hits

    assert {hit.identity.madhhab for hit in hits} == {"maliki"}


def test_excluded_madhhab_is_applied_before_ranking(
    tmp_path: Path,
) -> None:
    backend = build_backend(tmp_path)

    task = initial_task("ما حكم البيع؟")

    task = replace(
        task,
        requested_madhhabs=(),
        excluded_madhhabs=("hanafi",),
    )

    hits = backend.search(
        task,
        limit=10,
    )

    assert hits

    assert all(hit.identity.madhhab != "hanafi" for hit in hits)


def test_partial_corpus_never_attests_absence(
    tmp_path: Path,
) -> None:
    backend = build_backend(tmp_path)

    assert backend.attests_complete_absence is False


def test_no_match_becomes_budget_exhausted_not_absence(
    tmp_path: Path,
) -> None:
    backend = build_backend(tmp_path)

    result = ShamelaHybridEvidenceScout(backend=backend).scout(
        route("ما حكم زقندرةفرقد؟")
    )

    assert result.stop_reason is ShamelaScoutStopReason.BUDGET_EXHAUSTED


def test_comparative_scout_uses_real_backend_contract(
    tmp_path: Path,
) -> None:
    backend = build_backend(tmp_path)

    result = ShamelaHybridEvidenceScout(backend=backend).scout(
        route("ما أقوال المذهب الحنفي والمالكي في البيع؟"),
        limit_per_task=5,
    )

    covered = {hit.identity.madhhab for hit in result.hits if hit.identity.madhhab}

    assert covered == {
        "hanafi",
        "maliki",
    }

    assert result.stop_reason is ShamelaScoutStopReason.RETRIEVAL_COVERAGE_MET

    assert result.subqueries_used <= 3

    assert result.passes_used <= 3


def test_expected_index_fingerprint_fails_closed(
    tmp_path: Path,
) -> None:
    backend = build_backend(tmp_path)

    with pytest.raises(
        ValueError,
        match="index fingerprint",
    ):
        ShamelaFtsBackend(
            backend.index,
            expected_index_fingerprint=("0" * 64),
        )


def test_tampered_index_text_fails_closed(
    tmp_path: Path,
) -> None:
    backend = build_backend(tmp_path)

    with sqlite3.connect(backend.index.path) as connection:
        connection.execute(
            """
            UPDATE passages
            SET raw_text = ?
            WHERE work_id = ?
            """,
            (
                "نص تم تغييره",
                "1",
            ),
        )

        connection.commit()

    task = initial_task("ما حكم البيع؟")

    task = replace(
        task,
        requested_madhhabs=("hanafi",),
        excluded_madhhabs=(),
    )

    with pytest.raises(
        ValueError,
        match="text hash",
    ):
        backend.search(
            task,
            limit=5,
        )
