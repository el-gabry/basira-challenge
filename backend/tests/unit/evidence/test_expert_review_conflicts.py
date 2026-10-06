from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceConflict,
    EvidenceConflictType,
)
from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionAction,
    EvidenceDecisionReason,
)
from basira.evidence.expert_review import (
    ExpertReviewPacketBuilder,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)


def test_expert_review_packet_preserves_conflicts() -> None:
    understanding = BasiraQueryUnderstandingService().understand("ما درجة هذا الحديث؟")

    conflict = EvidenceConflict(
        conflict_type=(EvidenceConflictType.HADITH_GRADE),
        group_id="hadeethenc:5457",
        evidence_ids=(
            "source-a:5457:grade",
            "source-b:5457:grade",
        ),
    )

    bundle = EvidenceBundle(
        evidence=(),
        required_assessments=(),
        conflicts=(conflict,),
    )

    decision = EvidenceDecision(
        action=(EvidenceDecisionAction.ESCALATE_TO_EXPERT),
        reasons=(EvidenceDecisionReason.EVIDENCE_CONFLICT,),
    )

    packet = ExpertReviewPacketBuilder().build(
        case_id="hadith-conflict-5457",
        understanding=understanding,
        bundle=bundle,
        decision=decision,
    )

    assert packet.conflicts == (conflict,)

    assert packet.escalation_reasons == (EvidenceDecisionReason.EVIDENCE_CONFLICT,)
