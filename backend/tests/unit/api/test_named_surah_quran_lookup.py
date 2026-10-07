from __future__ import annotations

from basira.api.presenter import (
    present_query,
)
from basira.api.service import (
    build_default_query_service,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
)


def test_named_surah_ayah_lookup_publishes_verified_canonical_text():
    service = build_default_query_service()

    execution = service.execute(
        question="الآية 4 من سورة الملك",
        language="ar",
    )

    response = present_query(
        execution,
        language="ar",
    )

    assert response.action == "answer"
    assert response.has_answer is True

    assert {
        node.reference
        for node in execution.retrieval.evidence
        if node.domain.value == "quran"
    } == {"67:4"}


def test_named_surah_ayah_lookup_relation_is_verified_identity_support():
    service = build_default_query_service()

    governed = (
        service
        .governed_runtime
        .execute(
            question="الآية 4 من سورة الملك",
        )
    )

    assert governed.relation is not None

    record = next(
        item
        for item in governed.relation.records
        if item.evidence_id
        == "quranpedia:mushaf:1:67:4"
    )

    assert (
        record.relation
        is ClaimEvidenceRelation.SUPPORTS
    )


def test_named_surah_lookup_spelling_variants_publish_same_canonical_ayah():
    service = build_default_query_service()

    questions = (
        "الآية 4 من سورة الملك",
        "الاية 4 من سورة الملك",
        "آية 4 من سورة الملك",
        "اية 4 من سورة الملك",
        "آيه 4 من سورة الملك",
        "ايه 4 من سورة الملك",
        "الايه 4 من سورة الملك",
    )

    for question in questions:
        execution = service.execute(
            question=question,
            language="ar",
        )

        assert (
            execution.answer.action.value
            == "answer"
        ), question

        assert execution.answer.has_answer, question

        assert {
            node.reference
            for node in execution.retrieval.evidence
            if node.domain.value == "quran"
        } == {"67:4"}, question
