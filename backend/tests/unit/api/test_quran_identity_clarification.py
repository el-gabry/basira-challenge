from __future__ import annotations

from basira.api.presenter import (
    present_query,
)
from basira.api.schemas import (
    QueryResponse,
)
from basira.api.service import (
    build_default_query_service,
)


def response_for(
    question: str,
):
    service = (
        build_default_query_service()
    )

    execution = service.execute(
        question=question
    )

    return present_query(
        execution
    )


def assert_clarification(
    question: str,
):
    response = response_for(
        question
    )

    assert response.action == "clarify"
    assert response.has_answer is False
    assert response.answer is None

    assert response.clarification is not None
    assert (
        response.clarification.kind
        == "quran_identity"
    )

    assert response.requirements == []
    assert response.evidence == []
    assert response.citations == []
    assert response.claims == []

    assert response.general_material is None
    assert response.quran_verification is None

    assert response.experience is not None
    assert (
        response.experience.state
        == "needs_clarification"
    )
    assert (
        response.experience.can_publish
        is False
    )

    combined = " ".join(
        (
            *response.limitations,
            response.experience.label,
            response.experience.headline,
            response.experience.detail,
        )
    )

    assert (
        "الأدلة غير كافية"
        not in combined
    )

    return response


def test_repeated_quran_text_is_clarification_not_missing_evidence():
    response = assert_clarification(
        "ما معنى إن الله غفور رحيم؟"
    )

    assert len(
        response
        .clarification
        .candidate_references
    ) > 1


def test_two_token_quran_fragment_is_bounded_clarification():
    response = assert_clarification(
        "ما معنى قل هو؟"
    )

    assert (
        response
        .clarification
        .candidate_references
    )

    assert len(
        response
        .clarification
        .candidate_references
    ) <= 12


def test_three_token_quran_fragment_is_clarification():
    response = assert_clarification(
        "ما تفسير والله غفور رحيم؟"
    )

    assert (
        response
        .clarification
        .candidate_references
    )


def test_multi_claim_ambiguity_stops_before_religious_retrieval():
    response = assert_clarification(
        "ما معنى قل هو؟ "
        "وهل حديث إنما الأعمال بالنيات صحيح؟"
    )

    assert (
        response
        .clarification
        .candidate_references
    )


def test_query_response_schema_exposes_clarification():
    schema = (
        QueryResponse
        .model_json_schema()
    )

    assert (
        "clarification"
        in schema["properties"]
    )


def test_clarification_is_terminal_before_promoted_language_guards(
    monkeypatch,
):
    def fail_if_called(**_kwargs):
        raise AssertionError(
            "promoted language guard must not run "
            "after Quran identity became clarification"
        )

    monkeypatch.setattr(
        "basira.api.service."
        "_enforce_promoted_language_constraints",
        fail_if_called,
    )

    service = build_default_query_service()

    execution = service.execute(
        question="ما معنى قل هو؟",
        language="ar",
    )

    response = present_query(
        execution,
        language="ar",
    )

    assert response.action == "clarify"
    assert response.has_answer is False
    assert response.clarification is not None
    assert response.requirements == []
    assert response.evidence == []
