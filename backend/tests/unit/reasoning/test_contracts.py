from __future__ import annotations

import pytest

from basira.reasoning.contracts import (
    AnswerConstraint,
    ClassicalFiqhIssue,
    ContemporaryFiqhContext,
    ContestedClaim,
    EvidenceObligation,
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
    classical_fiqh_comparison_frame,
    contemporary_fiqh_frame,
    contested_claim_frame,
)


def test_shubha_is_reasoning_mode_not_discipline() -> None:
    assert ReasoningMode.CONTESTED_CLAIM.value == "contested_claim"

    assert all(discipline.value != "shubha" for discipline in ReligiousDiscipline)


def test_contested_claim_can_be_about_hadith() -> None:
    frame = contested_claim_frame(
        frame_id="frame-1",
        question=("هل هذا الادعاء عن الحديث صحيح؟"),
        primary_discipline=(ReligiousDiscipline.HADITH),
    )

    assert frame.reasoning_mode is ReasoningMode.CONTESTED_CLAIM

    assert frame.primary_discipline is ReligiousDiscipline.HADITH

    assert AnswerConstraint.DO_NOT_ACCEPT_PREMISE_AS_FACT in frame.constraints


def test_contested_claim_can_cross_disciplines() -> None:
    frame = contested_claim_frame(
        frame_id="frame-2",
        question=("هل يوجد تعارض بين هذا الحديث وتفسير الآية؟"),
        primary_discipline=(ReligiousDiscipline.HADITH),
        secondary_disciplines=(
            ReligiousDiscipline.QURAN,
            ReligiousDiscipline.TAFSIR,
        ),
    )

    assert frame.secondary_disciplines == (
        ReligiousDiscipline.QURAN,
        ReligiousDiscipline.TAFSIR,
    )


def test_classical_fiqh_comparison_preserves_plurality() -> None:
    frame = classical_fiqh_comparison_frame(
        frame_id="fiqh-1",
        question=("ما أقوال المذاهب في المسألة؟"),
    )

    assert frame.primary_discipline is ReligiousDiscipline.FIQH

    assert frame.reasoning_mode is ReasoningMode.COMPARATIVE

    assert EvidenceObligation.MADHHAB_SCOPE in frame.obligations

    assert EvidenceObligation.DOCUMENTED_DISAGREEMENT in frame.obligations

    assert AnswerConstraint.DO_NOT_COLLAPSE_MADHHABS in frame.constraints

    assert AnswerConstraint.DO_NOT_CLAIM_CONSENSUS in frame.constraints


def test_contemporary_fiqh_requires_modern_context() -> None:
    frame = contemporary_fiqh_frame(
        frame_id="modern-1",
        question=("ما حكم هذا المنتج المالي؟"),
    )

    assert frame.primary_discipline is ReligiousDiscipline.CONTEMPORARY_FIQH

    assert EvidenceObligation.CONTEMPORARY_FACTS in frame.obligations

    assert EvidenceObligation.TEMPORAL_CONTEXT in frame.obligations

    assert EvidenceObligation.JURISDICTION_CONTEXT in frame.obligations

    assert EvidenceObligation.INSTITUTION_ATTRIBUTION in frame.obligations


def test_contemporary_context_requires_explicit_facts() -> None:
    with pytest.raises(
        ValueError,
        match="requires explicit facts",
    ):
        ContemporaryFiqhContext(
            issue_id="issue-1",
            facts=(),
        )


def test_primary_discipline_cannot_be_secondary() -> None:
    with pytest.raises(
        ValueError,
        match="must not also be secondary",
    ):
        ReligiousReasoningFrame(
            frame_id="bad-frame",
            question="test",
            primary_discipline=(ReligiousDiscipline.FIQH),
            reasoning_mode=(ReasoningMode.COMPARATIVE),
            secondary_disciplines=(ReligiousDiscipline.FIQH,),
        )


def test_fiqh_issue_does_not_encode_winner() -> None:
    issue = ClassicalFiqhIssue(
        issue_id="issue-1",
        issue_text="مسألة فقهية",
        requested_madhhabs=(
            "hanafi",
            "maliki",
        ),
        compare_positions=True,
    )

    assert issue.compare_positions is True

    assert not hasattr(
        issue,
        "winning_position",
    )


def test_contested_claim_does_not_assume_falsehood() -> None:
    claim = ContestedClaim(
        claim_id="claim-1",
        text="ادعاء يحتاج إلى فحص",
        attribution="example-source",
    )

    assert claim.text
    assert not hasattr(
        claim,
        "is_false",
    )
