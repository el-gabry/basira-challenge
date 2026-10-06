from __future__ import annotations

import pytest

from basira.answer.composer import (
    GroundedAnswerComposer,
)
from basira.answer.integrity import (
    ClaimIntegrityError,
    ClaimIntegrityIssueType,
    ClaimSourceIntegrityVerifier,
)
from basira.answer.models import (
    StructuredClaim,
)
from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceRequirementAssessment,
    EvidenceRequirementState,
)
from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionAction,
    EvidenceDecisionReason,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.evidence.service import (
    EvidenceDecisionOutcome,
)


def _node(
    *,
    evidence_id: str = "evidence-1",
    text: str = ("هذا نص تفسيري أصلي مأخوذ من المصدر."),
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=EvidenceDomain.TAFSIR,
        text=text,
        source_id=("surahapp-tafsir-saadi"),
        reference="2:153",
    )


def _claim(
    *,
    text: str,
    evidence_id: str = "evidence-1",
    claim_id: str = "claim-1",
) -> StructuredClaim:
    return StructuredClaim(
        axis_id="tafsir",
        claim_id=claim_id,
        text=text,
        evidence_ids=(evidence_id,),
    )


def test_exact_literal_claim_passes() -> None:
    node = _node()

    report = ClaimSourceIntegrityVerifier().verify(
        claims=(
            _claim(
                text=node.text,
            ),
        ),
        evidence=(node,),
    )

    assert report.passed
    assert report.issues == ()


def test_whitespace_normalized_literal_passes() -> None:
    node = _node(text=("هذا   نص\nتفسيري من المصدر."))

    report = ClaimSourceIntegrityVerifier().verify(
        claims=(
            _claim(
                text=("هذا نص تفسيري من المصدر."),
            ),
        ),
        evidence=(node,),
    )

    assert report.passed


def test_safe_truncated_excerpt_with_ellipsis_passes() -> None:
    node = _node(text=("هذا نص طويل من المصدر ويستمر بعد الجزء المنشور."))

    report = ClaimSourceIntegrityVerifier().verify(
        claims=(
            _claim(
                text=("هذا نص طويل من المصدر…"),
            ),
        ),
        evidence=(node,),
    )

    assert report.passed


def test_unknown_evidence_id_fails_closed() -> None:
    node = _node()

    report = ClaimSourceIntegrityVerifier().verify(
        claims=(
            _claim(
                text=node.text,
                evidence_id=("missing-evidence"),
            ),
        ),
        evidence=(node,),
    )

    assert not report.passed

    assert ClaimIntegrityIssueType.UNKNOWN_EVIDENCE_ID in {
        issue.issue_type for issue in report.issues
    }


def test_non_literal_claim_text_fails_closed() -> None:
    node = _node()

    report = ClaimSourceIntegrityVerifier().verify(
        claims=(
            _claim(
                text=("هذا استنتاج جديد غير موجود في المصدر."),
            ),
        ),
        evidence=(node,),
    )

    assert not report.passed

    assert ClaimIntegrityIssueType.NON_LITERAL_CLAIM_TEXT in {
        issue.issue_type for issue in report.issues
    }


def test_duplicate_claim_id_is_rejected() -> None:
    node = _node()

    report = ClaimSourceIntegrityVerifier().verify(
        claims=(
            _claim(
                text=node.text,
            ),
            _claim(
                text=node.text,
            ),
        ),
        evidence=(node,),
    )

    assert not report.passed

    assert ClaimIntegrityIssueType.DUPLICATE_CLAIM_ID in {
        issue.issue_type for issue in report.issues
    }


class _TamperingComposer(
    GroundedAnswerComposer,
):
    def _structured_claims(
        self,
        *,
        primary_need,
        nodes,
    ):
        return (
            StructuredClaim(
                axis_id="tafsir",
                claim_id="claim-1",
                text=("نص لم يرد في الدليل إطلاقًا."),
                evidence_ids=(nodes[0].evidence_id,),
            ),
        )


def test_composer_refuses_tampered_claim_before_publication() -> None:
    node = _node()

    bundle = EvidenceBundle(
        evidence=(node,),
        required_assessments=(
            EvidenceRequirementAssessment(
                need=EvidenceNeed.TAFSIR,
                state=(EvidenceRequirementState.SATISFIED),
                evidence_ids=(node.evidence_id,),
            ),
        ),
    )

    outcome = EvidenceDecisionOutcome(
        bundle=bundle,
        decision=EvidenceDecision(
            action=(EvidenceDecisionAction.ANSWER),
            reasons=(EvidenceDecisionReason.COMPLETE_EVIDENCE,),
        ),
        expert_review=None,
    )

    with pytest.raises(ClaimIntegrityError):
        _TamperingComposer().compose(
            question=("ماذا يقول التفسير؟"),
            outcome=outcome,
        )
