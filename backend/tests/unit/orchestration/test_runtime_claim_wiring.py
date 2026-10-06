from __future__ import annotations

import pytest

from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
    EvidenceNode,
)
from basira.orchestration.capability_executor import (
    CapabilityExecutionError,
    CapabilityRetrievalBinding,
    GovernedCapabilityExecutor,
)
from basira.orchestration.claim_sufficiency import (
    ClaimResolutionState,
    ClaimSufficiencyContract,
    ClaimSufficiencyState,
    SupportRequirement,
)
from basira.orchestration.contracts import (
    AgentCapability,
    ClaimTask,
)
from basira.orchestration.evidence_acceptance import (
    ClaimEvidencePolicySet,
    RetrievalShape,
    TaskEvidenceAcceptanceContract,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
    ClaimEvidenceRelationRecord,
    RelationOrigin,
    TaskEvidenceRelationService,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)


class RecordingRetriever:
    def retrieve(
        self,
        plan,
        *,
        limit_per_domain: int = 10,
    ) -> UnifiedRetrievalResult:
        del limit_per_domain

        return UnifiedRetrievalResult(
            plan=plan,
            evidence=(
                EvidenceNode(
                    evidence_id="fiqh:1",
                    domain=EvidenceDomain.FIQH,
                    text="نص فقهي معتبر.",
                    source_id="source:fiqh",
                    reference="chapter:1",
                ),
            ),
            unavailable_domains=frozenset(),
        )


class SupportsEvaluator:
    def evaluate(
        self,
        *,
        task: ClaimTask,
        evidence: EvidenceNode,
    ) -> ClaimEvidenceRelationRecord:
        return ClaimEvidenceRelationRecord(
            task_id=task.task_id,
            evidence_id=evidence.evidence_id,
            relation=(ClaimEvidenceRelation.SUPPORTS),
            origin=(RelationOrigin.DETERMINISTIC),
        )


def task(
    task_id: str = "claim:fiqh",
) -> ClaimTask:
    text = "ما حكم البيع في هذه المسألة؟"

    return ClaimTask(
        task_id=task_id,
        claim_text=text,
        frame=ReligiousReasoningFrame(
            frame_id=f"frame:{task_id}",
            question=text,
            primary_discipline=(ReligiousDiscipline.FIQH),
            reasoning_mode=(ReasoningMode.LEGAL_RULING),
        ),
        context_requirement=(ContextRequirement()),
    )


def capability() -> AgentCapability:
    return AgentCapability(
        capability_id="cap:fiqh",
        agent_id="agent:fiqh",
        disciplines=frozenset(
            {
                ReligiousDiscipline.FIQH,
            }
        ),
    )


def structural_policy(
    task_id: str = "claim:fiqh",
) -> TaskEvidenceAcceptanceContract:
    return TaskEvidenceAcceptanceContract(
        task_id=task_id,
        retrieval_shape=(RetrievalShape.CONCEPTUAL),
        allowed_domains=frozenset(
            {
                EvidenceDomain.FIQH,
            }
        ),
        required_domains=frozenset(
            {
                EvidenceDomain.FIQH,
            }
        ),
    )


def sufficiency_contract(
    task_id: str = "claim:fiqh",
) -> ClaimSufficiencyContract:
    return ClaimSufficiencyContract(
        task_id=task_id,
        support_requirements=(
            SupportRequirement(
                requirement_id=(f"{task_id}:fiqh-support"),
                domains=frozenset(
                    {
                        EvidenceDomain.FIQH,
                    }
                ),
            ),
        ),
    )


def executor(
    *,
    sufficiency_contracts: tuple[
        ClaimSufficiencyContract,
        ...,
    ]
    | None = None,
) -> GovernedCapabilityExecutor:
    contracts = (
        sufficiency_contracts
        if sufficiency_contracts is not None
        else (sufficiency_contract(),)
    )

    policy_contracts = tuple(
        structural_policy(contract.task_id) for contract in contracts
    )

    return GovernedCapabilityExecutor(
        retriever=RecordingRetriever(),  # type: ignore[arg-type]
        bindings=(
            CapabilityRetrievalBinding(
                capability_id="cap:fiqh",
                domains=frozenset(
                    {
                        EvidenceDomain.FIQH,
                    }
                ),
            ),
        ),
        evidence_policies=(ClaimEvidencePolicySet(contracts=policy_contracts)),
        relation_service=(
            TaskEvidenceRelationService(
                evaluator=(SupportsEvaluator()),
            )
        ),
        sufficiency_contracts=contracts,
    )


def test_executor_runtime_runs_relation_then_sufficiency() -> None:
    runtime = executor()

    runtime.execute(
        task=task(),
        capability=capability(),
        delegation=None,
    )

    relation = runtime.relation_for_task("claim:fiqh")

    assert relation is not None
    assert relation.has_positive_support

    sufficiency = runtime.sufficiency_for_task("claim:fiqh")

    assert sufficiency is not None

    assert sufficiency.state is ClaimSufficiencyState.SUFFICIENT

    resolution = runtime.resolve_claim_dependencies()

    assert resolution.for_task("claim:fiqh").state is ClaimResolutionState.READY


def test_relation_runtime_requires_structural_policies() -> None:
    with pytest.raises(
        ValueError,
        match="structural evidence policies",
    ):
        GovernedCapabilityExecutor(
            retriever=RecordingRetriever(),  # type: ignore[arg-type]
            bindings=(
                CapabilityRetrievalBinding(
                    capability_id="cap:fiqh",
                    domains=frozenset(
                        {
                            EvidenceDomain.FIQH,
                        }
                    ),
                ),
            ),
            relation_service=(
                TaskEvidenceRelationService(
                    evaluator=(SupportsEvaluator()),
                )
            ),
        )


def test_dependency_resolution_fails_closed_until_all_tasks_assessed() -> None:
    runtime = executor(
        sufficiency_contracts=(
            sufficiency_contract("claim:fiqh"),
            sufficiency_contract("claim:second"),
        )
    )

    runtime.execute(
        task=task(),
        capability=capability(),
        delegation=None,
    )

    with pytest.raises(
        CapabilityExecutionError,
        match="missing sufficiency assessment",
    ):
        (runtime.resolve_claim_dependencies())
