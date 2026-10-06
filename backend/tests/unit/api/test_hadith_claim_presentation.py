from __future__ import annotations

from types import SimpleNamespace

from basira.api import presenter


def node(
    *,
    claim_type: str,
    text: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        domain=SimpleNamespace(
            value="hadith"
        ),
        claim_type=claim_type,
        source_id=(
            "hadeethenc-official"
        ),
        text=text,
    )


def test_publishable_hadith_grade_exposes_claim_value(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        presenter,
        "_may_display_supporting_text",
        lambda **kwargs: True,
    )

    result = presenter._public_claim_value(
        node(
            claim_type="hadith_grade",
            text="  ضعيف  ",
        )
    )

    assert result == "ضعيف"


def test_hadith_text_is_not_exposed_as_claim_value(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        presenter,
        "_may_display_supporting_text",
        lambda **kwargs: True,
    )

    result = presenter._public_claim_value(
        node(
            claim_type="hadith_text",
            text="نص الحديث",
        )
    )

    assert result is None


def test_hadith_grade_fails_closed_when_policy_denies(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        presenter,
        "_may_display_supporting_text",
        lambda **kwargs: False,
    )

    result = presenter._public_claim_value(
        node(
            claim_type="hadith_grade",
            text="صحيح",
        )
    )

    assert result is None



def test_hadith_grade_public_response_preserves_related_matn_id():
    from basira.api.presenter import (
        present_query,
    )
    from basira.api.service import (
        build_default_query_service,
    )

    execution = build_default_query_service().execute(
        question="هل حديث إنما الأعمال بالنيات صحيح؟"
    )

    response = present_query(execution)

    matn = [
        item
        for item in response.evidence
        if item.domain == "hadith"
        and item.claim_type == "hadith_text"
    ]

    grades = [
        item
        for item in response.evidence
        if item.domain == "hadith"
        and item.claim_type == "hadith_grade"
    ]

    assert len(matn) == 1
    assert grades

    canonical_id = matn[0].evidence_id

    assert all(
        canonical_id in item.related_hadith
        for item in grades
    )

    # Only grades actually selected for the public answer
    # must expose the short structured claim_value. Other
    # admitted grades may remain provenance-only evidence.
    used_grades = [
        item
        for item in grades
        if item.used_in_answer
    ]

    assert used_grades

    assert all(
        item.claim_value
        for item in used_grades
    )
