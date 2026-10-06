from __future__ import annotations

from dataclasses import dataclass

from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceBundleBuilder,
)
from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionPolicy,
)
from basira.evidence.expert_review import (
    ExpertReviewPacket,
    ExpertReviewPacketBuilder,
)
from basira.evidence.sufficiency import (
    RetrievalSufficiencyGate,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class EvidenceDecisionOutcome:
    """
    Final evidence-layer outcome before answer
    generation.

    This object is suitable for use by the future API
    and answer-composition layers.
    """

    bundle: EvidenceBundle

    decision: EvidenceDecision

    expert_review: ExpertReviewPacket | None = None


class EvidenceDecisionService:
    """
    Orchestrate evidence assessment, decision policy,
    and optional expert-review preparation.

    Answer generation must happen only after this
    service has produced an explicit decision.
    """

    def __init__(
        self,
        *,
        bundle_builder: (EvidenceBundleBuilder | None) = None,
        decision_policy: (EvidenceDecisionPolicy | None) = None,
        expert_review_builder: (ExpertReviewPacketBuilder | None) = None,
    ) -> None:
        self.bundle_builder = bundle_builder or EvidenceBundleBuilder()

        self.decision_policy = decision_policy or EvidenceDecisionPolicy()

        self.expert_review_builder = (
            expert_review_builder or ExpertReviewPacketBuilder()
        )

    def evaluate(
        self,
        *,
        retrieval_result: (UnifiedRetrievalResult),
        expert_case_id: (str | None) = None,
    ) -> EvidenceDecisionOutcome:
        bundle = self.bundle_builder.build(retrieval_result)

        understanding = retrieval_result.plan.understanding

        sufficiency = RetrievalSufficiencyGate().assess(bundle)

        decision = self.decision_policy.decide(
            understanding=(understanding),
            bundle=bundle,
            sufficiency=sufficiency,
        )

        expert_review = None

        if decision.requires_expert:
            if expert_case_id is None or not expert_case_id.strip():
                raise ValueError(
                    "expert_case_id is required "
                    "when the evidence decision "
                    "requires expert review."
                )

            expert_review = self.expert_review_builder.build(
                case_id=(expert_case_id),
                understanding=(understanding),
                bundle=bundle,
                decision=decision,
            )

        return EvidenceDecisionOutcome(
            bundle=bundle,
            decision=decision,
            expert_review=(expert_review),
        )
