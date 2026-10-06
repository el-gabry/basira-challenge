from dataclasses import replace

import pytest

from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceRequirementAssessment,
    EvidenceRequirementState,
)
from basira.evidence.decision import (
    EvidenceDecisionAction,
    EvidenceDecisionPolicy,
)
from basira.evidence.expert_review import (
    ExpertReviewPacketBuilder,
    ExpertReviewStatus,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
    RiskTag,
)


def make_bundle() -> EvidenceBundle:
    return EvidenceBundle(
        evidence=(
            EvidenceNode(
                evidence_id="quran:2:256",
                domain=EvidenceDomain.QURAN,
                text="لا إكراه في الدين",
                source_id="test-quran",
                reference="2:256",
            ),
            EvidenceNode(
                evidence_id="tafsir:2:256",
                domain=EvidenceDomain.TAFSIR,
                text="نص التفسير.",
                source_id="test-tafsir",
                reference="2:256",
            ),
        ),
        required_assessments=(
            EvidenceRequirementAssessment(
                need=(
                    EvidenceNeed
                    .CANONICAL_TEXT
                ),
                state=(
                    EvidenceRequirementState
                    .SATISFIED
                ),
                evidence_ids=(
                    "quran:2:256",
                ),
            ),
            EvidenceRequirementAssessment(
                need=EvidenceNeed.TAFSIR,
                state=(
                    EvidenceRequirementState
                    .SATISFIED
                ),
                evidence_ids=(
                    "tafsir:2:256",
                ),
            ),
        ),
    )


def test_escalated_case_builds_expert_review_packet() -> None:
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما تفسير الآية 2:256؟"
        )
    )

    understanding = replace(
        understanding,
        risk_tags=frozenset(
            {
                RiskTag.TAKFIR,
                RiskTag.CONTEXT_SENSITIVE,
            }
        ),
    )

    bundle = make_bundle()

    decision = (
        EvidenceDecisionPolicy()
        .decide(
            understanding=understanding,
            bundle=bundle,
        )
    )

    assert (
        decision.action
        == EvidenceDecisionAction
        .ESCALATE_TO_EXPERT
    )

    packet = (
        ExpertReviewPacketBuilder()
        .build(
            case_id="BASIRA-001",
            understanding=understanding,
            bundle=bundle,
            decision=decision,
        )
    )

    assert (
        packet.status
        == ExpertReviewStatus
        .AWAITING_REVIEW
    )

    assert packet.case_id == "BASIRA-001"

    assert packet.question == (
        "ما تفسير الآية 2:256؟"
    )

    assert packet.risk_tags == (
        RiskTag.TAKFIR,
    )

    assert packet.evidence_coverage == 1.0
    assert packet.resolution_coverage == 1.0

    assert len(packet.evidence) == 2


def test_non_escalated_case_cannot_create_expert_packet() -> None:
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما تفسير الآية 2:256؟"
        )
    )

    bundle = make_bundle()

    decision = (
        EvidenceDecisionPolicy()
        .decide(
            understanding=understanding,
            bundle=bundle,
        )
    )

    assert (
        decision.action
        == EvidenceDecisionAction.ANSWER
    )

    with pytest.raises(
        ValueError,
        match=(
            "require expert escalation"
        ),
    ):
        (
            ExpertReviewPacketBuilder()
            .build(
                case_id="BASIRA-002",
                understanding=understanding,
                bundle=bundle,
                decision=decision,
            )
        )
