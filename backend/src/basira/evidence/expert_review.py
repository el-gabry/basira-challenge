from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceConflict,
    EvidenceRequirementAssessment,
)
from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionReason,
)
from basira.evidence.models import (
    EvidenceNeed,
    EvidenceNode,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
    RiskTag,
)


class ExpertReviewStatus(StrEnum):
    AWAITING_REVIEW = "awaiting_expert_review"


@dataclass(
    frozen=True,
    slots=True,
)
class ExpertReviewPacket:
    """
    Evidence package prepared for qualified human
    review.

    Basira prepares and organizes evidence but does
    not convert an escalated case into an autonomous
    ruling.
    """

    case_id: str

    status: ExpertReviewStatus

    question: str

    intent: BasiraIntent

    risk_tags: tuple[
        RiskTag,
        ...,
    ]

    escalation_reasons: tuple[
        EvidenceDecisionReason,
        ...,
    ]

    evidence_coverage: float
    resolution_coverage: float

    required_assessments: tuple[
        EvidenceRequirementAssessment,
        ...,
    ]

    unresolved_needs: tuple[
        EvidenceNeed,
        ...,
    ]

    evidence: tuple[
        EvidenceNode,
        ...,
    ]

    conflicts: tuple[
        EvidenceConflict,
        ...,
    ] = ()


class ExpertReviewPacketBuilder:
    """
    Build a review packet only after the decision
    policy explicitly requests expert escalation.
    """

    def build(
        self,
        *,
        case_id: str,
        understanding: BasiraQueryUnderstanding,
        bundle: EvidenceBundle,
        decision: EvidenceDecision,
    ) -> ExpertReviewPacket:
        cleaned_case_id = case_id.strip()

        if not cleaned_case_id:
            raise ValueError(
                "Expert review case_id "
                "cannot be empty."
            )

        if not decision.requires_expert:
            raise ValueError(
                "Expert review packets may only "
                "be created for decisions that "
                "require expert escalation."
            )

        return ExpertReviewPacket(
            case_id=cleaned_case_id,
            status=(
                ExpertReviewStatus
                .AWAITING_REVIEW
            ),
            question=(
                understanding
                .query
                .original_text
            ),
            intent=(
                understanding
                .primary_intent
            ),
            risk_tags=(
                decision.risk_tags
            ),
            escalation_reasons=(
                decision.reasons
            ),
            evidence_coverage=(
                bundle.evidence_coverage
            ),
            resolution_coverage=(
                bundle.resolution_coverage
            ),
            required_assessments=(
                bundle.required_assessments
            ),
            unresolved_needs=(
                decision.unresolved_needs
            ),
            evidence=(
                bundle.evidence
            ),
            conflicts=(
                bundle.conflicts
            ),
        )
