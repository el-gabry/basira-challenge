from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from basira.evidence.service import (
    EvidenceDecisionOutcome,
)
from basira.orchestration.claim_sufficiency import (
    ClaimResolution,
    ClaimSufficiencyAssessment,
)
from basira.orchestration.contracts import (
    ClaimTask,
)
from basira.orchestration.coordinator import (
    AgentRunProduct,
)
from basira.orchestration.evidence_relation import (
    TaskEvidenceRelationAssessment,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)


class PublicDecisionService(Protocol):
    def evaluate(
        self,
        *,
        retrieval_result: UnifiedRetrievalResult,
        expert_case_id: str,
    ) -> EvidenceDecisionOutcome: ...


class PublicGraphExecutorView(Protocol):
    def relation_for_task(
        self,
        task_id: str,
    ) -> TaskEvidenceRelationAssessment | None: ...

    def sufficiency_for_task(
        self,
        task_id: str,
    ) -> ClaimSufficiencyAssessment | None: ...


class PublicSemanticRetrievalProjector(Protocol):
    def __call__(
        self,
        *,
        retrieval: UnifiedRetrievalResult,
        relation: TaskEvidenceRelationAssessment,
    ) -> UnifiedRetrievalResult: ...


class PublicOutcomeGuard(Protocol):
    def __call__(
        self,
        *,
        outcome: EvidenceDecisionOutcome,
        task: ClaimTask,
        relation: TaskEvidenceRelationAssessment,
        sufficiency: ClaimSufficiencyAssessment,
        dependency: ClaimResolution | None,
    ) -> EvidenceDecisionOutcome: ...


class PublicGraphOutcomeEvaluator:
    """
    Public ClaimGraph decision boundary.

    The coordinator must never release a claim from the
    raw query-level evidence decision alone.

    Each executed claim first passes the existing:
    - claim/evidence relation gate;
    - per-claim sufficiency gate;
    - public outcome guard.

    DAG dependency release itself remains owned by
    AgentCoordinator, so this evaluator deliberately
    passes dependency=None to the public guard.
    """

    def __init__(
        self,
        *,
        decision_service: PublicDecisionService,
        executor: PublicGraphExecutorView,
        retrieval_projector: PublicSemanticRetrievalProjector,
        guard: PublicOutcomeGuard,
    ) -> None:
        self._decision_service = decision_service
        self._executor = executor
        self._retrieval_projector = retrieval_projector
        self._guard = guard

        self._outcomes: dict[
            str,
            EvidenceDecisionOutcome,
        ] = {}

        self._retrievals: dict[
            str,
            UnifiedRetrievalResult,
        ] = {}

    def evaluate(
        self,
        *,
        task: ClaimTask,
        product: AgentRunProduct,
    ) -> EvidenceDecisionOutcome:
        relation = self._executor.relation_for_task(
            task.task_id
        )

        sufficiency = (
            self._executor
            .sufficiency_for_task(
                task.task_id
            )
        )

        if (
            relation is None
            or sufficiency is None
        ):
            raise RuntimeError(
                "public graph claim completed without "
                "relation/sufficiency assessment"
            )

        retrieval = self._retrieval_projector(
            retrieval=product.retrieval_result,
            relation=relation,
        )

        self._retrievals[
            task.task_id
        ] = retrieval

        raw = self._decision_service.evaluate(
            retrieval_result=retrieval,
            expert_case_id=(
                f"expert-{uuid4()}"
            ),
        )

        guarded = self._guard(
            outcome=raw,
            task=task,
            relation=relation,
            sufficiency=sufficiency,
            dependency=None,
        )

        self._outcomes[
            task.task_id
        ] = guarded

        return guarded

    def outcome_for_task(
        self,
        task_id: str,
    ) -> EvidenceDecisionOutcome | None:
        return self._outcomes.get(
            task_id
        )

    def retrieval_for_task(
        self,
        task_id: str,
    ) -> UnifiedRetrievalResult | None:
        """
        Return only the semantic retrieval projection
        actually presented to the decision layer.
        """

        return self._retrievals.get(
            task_id
        )
