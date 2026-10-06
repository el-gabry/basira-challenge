from types import SimpleNamespace
from typing import cast

import pytest

from basira.api.public_graph_outcome import (
    PublicGraphOutcomeEvaluator,
)
from basira.evidence.service import (
    EvidenceDecisionOutcome,
)
from basira.orchestration.claim_sufficiency import (
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


class FakeDecisionService:
    def __init__(
        self,
        outcome: EvidenceDecisionOutcome,
    ) -> None:
        self.outcome = outcome

    def evaluate(
        self,
        *,
        retrieval_result: UnifiedRetrievalResult,
        expert_case_id: str,
    ) -> EvidenceDecisionOutcome:
        assert retrieval_result is not None
        assert expert_case_id.startswith(
            "expert-"
        )

        return self.outcome


class FakeExecutor:
    def __init__(
        self,
        *,
        relation: (
            TaskEvidenceRelationAssessment
            | None
        ),
        sufficiency: (
            ClaimSufficiencyAssessment
            | None
        ),
    ) -> None:
        self.relation = relation
        self.sufficiency = sufficiency

    def relation_for_task(
        self,
        task_id: str,
    ) -> TaskEvidenceRelationAssessment | None:
        assert task_id == "claim-1"
        return self.relation

    def sufficiency_for_task(
        self,
        task_id: str,
    ) -> ClaimSufficiencyAssessment | None:
        assert task_id == "claim-1"
        return self.sufficiency


def _task() -> ClaimTask:
    return cast(
        ClaimTask,
        SimpleNamespace(
            task_id="claim-1",
        ),
    )


def _product() -> AgentRunProduct:
    return cast(
        AgentRunProduct,
        SimpleNamespace(
            retrieval_result=(
                cast(
                    UnifiedRetrievalResult,
                    object(),
                )
            ),
        ),
    )


def test_records_only_guarded_public_outcome() -> None:
    raw = cast(
        EvidenceDecisionOutcome,
        object(),
    )

    guarded = cast(
        EvidenceDecisionOutcome,
        object(),
    )

    relation = cast(
        TaskEvidenceRelationAssessment,
        object(),
    )

    sufficiency = cast(
        ClaimSufficiencyAssessment,
        object(),
    )

    calls = []

    def guard(
        *,
        outcome,
        task,
        relation,
        sufficiency,
        dependency,
    ):
        calls.append(
            (
                outcome,
                task,
                relation,
                sufficiency,
                dependency,
            )
        )

        return guarded

    evaluator = PublicGraphOutcomeEvaluator(
        decision_service=(
            FakeDecisionService(raw)
        ),
        executor=FakeExecutor(
            relation=relation,
            sufficiency=sufficiency,
        ),
        retrieval_projector=(
            lambda *, retrieval, relation: retrieval
        ),
        guard=guard,
    )

    result = evaluator.evaluate(
        task=_task(),
        product=_product(),
    )

    assert result is guarded

    assert (
        evaluator.outcome_for_task(
            "claim-1"
        )
        is guarded
    )

    assert len(calls) == 1
    assert calls[0][0] is raw
    assert calls[0][2] is relation
    assert calls[0][3] is sufficiency

    # AgentCoordinator owns graph dependency release.
    assert calls[0][4] is None


@pytest.mark.parametrize(
    (
        "relation_present",
        "sufficiency_present",
    ),
    (
        (False, True),
        (True, False),
        (False, False),
    ),
)
def test_missing_claim_assessment_fails_closed(
    relation_present: bool,
    sufficiency_present: bool,
) -> None:
    raw = cast(
        EvidenceDecisionOutcome,
        object(),
    )

    relation = (
        cast(
            TaskEvidenceRelationAssessment,
            object(),
        )
        if relation_present
        else None
    )

    sufficiency = (
        cast(
            ClaimSufficiencyAssessment,
            object(),
        )
        if sufficiency_present
        else None
    )

    evaluator = PublicGraphOutcomeEvaluator(
        decision_service=(
            FakeDecisionService(raw)
        ),
        executor=FakeExecutor(
            relation=relation,
            sufficiency=sufficiency,
        ),
        retrieval_projector=(
            lambda *, retrieval, relation: retrieval
        ),
        guard=(
            lambda **_: raw
        ),
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "without relation/sufficiency"
        ),
    ):
        evaluator.evaluate(
            task=_task(),
            product=_product(),
        )
