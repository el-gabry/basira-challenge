from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.orchestration.evidence_acceptance import (
    TaskEvidenceAcceptanceResult,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
    TaskEvidenceRelationAssessment,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SupportRequirement:
    """
    One positive-support obligation for a claim.

    Structural presence is NOT semantic support.
    A requirement is satisfied only by evidence whose
    claim relation is SUPPORTS and whose domain is one
    of the explicitly allowed support domains.
    """

    requirement_id: str
    domains: frozenset[EvidenceDomain]
    min_supporting_evidence: int = 1

    def __post_init__(
        self,
    ) -> None:
        if not self.requirement_id.strip():
            raise ValueError("requirement_id must not be blank")

        if not self.domains:
            raise ValueError("support requirement must name at least one domain")

        if self.min_supporting_evidence < 1:
            raise ValueError("min_supporting_evidence must be positive")


@dataclass(
    frozen=True,
    slots=True,
)
class ClaimSufficiencyContract:
    """
    Claim-level semantic sufficiency contract.

    Dependencies live beside the claim rather than in
    ClaimTask so ClaimTask remains semantic-only.
    """

    task_id: str
    support_requirements: tuple[
        SupportRequirement,
        ...,
    ]
    dependency_task_ids: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must not be blank")

        if not self.support_requirements:
            raise ValueError(
                "claim sufficiency requires at least one explicit support requirement"
            )

        requirement_ids = tuple(
            requirement.requirement_id for requirement in self.support_requirements
        )

        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("support requirement IDs must be unique")

        if self.task_id in self.dependency_task_ids:
            raise ValueError("claim cannot depend on itself")

        if len(self.dependency_task_ids) != len(set(self.dependency_task_ids)):
            raise ValueError("dependency task IDs must be unique")


class ClaimSufficiencyState(StrEnum):
    SUFFICIENT = "sufficient"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    CONFLICT = "conflict"


class ClaimSufficiencyReason(StrEnum):
    SUFFICIENT = "sufficient"
    STRUCTURAL_CONTRACT_UNSATISFIED = "structural_contract_unsatisfied"
    MISSING_REQUIRED_SUPPORT = "missing_required_support"
    EVIDENCE_CONTRADICTION = "evidence_contradiction"


@dataclass(
    frozen=True,
    slots=True,
)
class ClaimSufficiencyAssessment:
    task_id: str
    state: ClaimSufficiencyState
    reasons: tuple[
        ClaimSufficiencyReason,
        ...,
    ]
    satisfied_requirement_ids: tuple[
        str,
        ...,
    ]
    missing_requirement_ids: tuple[
        str,
        ...,
    ]
    supporting_evidence_ids: tuple[
        str,
        ...,
    ]
    contradicting_evidence_ids: tuple[
        str,
        ...,
    ]
    unresolved_evidence_ids: tuple[
        str,
        ...,
    ]

    @property
    def sufficient(
        self,
    ) -> bool:
        return self.state is ClaimSufficiencyState.SUFFICIENT


class ClaimSufficiencyEvaluator:
    """
    Deterministic claim-level sufficiency.

    Order of truth:
      structural validity
      -> claim/evidence relation
      -> support requirements
      -> sufficiency

    It never decides the religious truth of the claim
    and never converts CONTEXT_ONLY/PARTIAL/UNKNOWN into
    positive support.
    """

    def assess(
        self,
        *,
        contract: ClaimSufficiencyContract,
        structural: (TaskEvidenceAcceptanceResult),
        relations: (TaskEvidenceRelationAssessment),
    ) -> ClaimSufficiencyAssessment:
        if structural.task_id != contract.task_id:
            raise ValueError("structural assessment belongs to a different task")

        if relations.task_id != contract.task_id:
            raise ValueError("relation assessment belongs to a different task")

        accepted = tuple(structural.accepted_evidence)

        by_id: dict[
            str,
            EvidenceNode,
        ] = {node.evidence_id: node for node in accepted}

        accepted_ids = tuple(node.evidence_id for node in accepted)

        relation_ids = tuple(record.evidence_id for record in relations.records)

        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("relation assessment contains duplicate evidence IDs")

        if set(relation_ids) != set(accepted_ids):
            raise ValueError(
                "relation assessment must cover exactly structurally accepted evidence"
            )

        supporting_ids = tuple(
            record.evidence_id
            for record in relations.records
            if (record.relation is ClaimEvidenceRelation.SUPPORTS)
        )

        contradicting_ids = tuple(
            record.evidence_id
            for record in relations.records
            if (record.relation is ClaimEvidenceRelation.CONTRADICTS)
        )

        unresolved_ids = tuple(
            record.evidence_id
            for record in relations.records
            if (
                record.relation
                in {
                    ClaimEvidenceRelation.PARTIAL,
                    ClaimEvidenceRelation.UNKNOWN,
                }
            )
        )

        satisfied: list[str] = []
        missing: list[str] = []

        supporting_id_set = set(supporting_ids)

        for requirement in contract.support_requirements:
            matching = tuple(
                evidence_id
                for evidence_id in supporting_ids
                if (by_id[evidence_id].domain in requirement.domains)
            )

            if len(matching) >= requirement.min_supporting_evidence:
                satisfied.append(requirement.requirement_id)
            else:
                missing.append(requirement.requirement_id)

        reasons: list[ClaimSufficiencyReason] = []

        if contradicting_ids:
            reasons.append(ClaimSufficiencyReason.EVIDENCE_CONTRADICTION)

        if not (structural.structural_contract_satisfied):
            reasons.append(ClaimSufficiencyReason.STRUCTURAL_CONTRACT_UNSATISFIED)

        if missing:
            reasons.append(ClaimSufficiencyReason.MISSING_REQUIRED_SUPPORT)

        if contradicting_ids:
            state = ClaimSufficiencyState.CONFLICT
        elif not structural.structural_contract_satisfied or missing:
            state = ClaimSufficiencyState.NEEDS_MORE_EVIDENCE
        else:
            state = ClaimSufficiencyState.SUFFICIENT
            reasons.append(ClaimSufficiencyReason.SUFFICIENT)

        # Defensive invariant: a SUPPORTS ID must refer
        # to structurally accepted evidence.
        if not supporting_id_set.issubset(by_id):
            raise AssertionError("support escaped structural gate")

        return ClaimSufficiencyAssessment(
            task_id=contract.task_id,
            state=state,
            reasons=tuple(reasons),
            satisfied_requirement_ids=(tuple(satisfied)),
            missing_requirement_ids=(tuple(missing)),
            supporting_evidence_ids=(supporting_ids),
            contradicting_evidence_ids=(contradicting_ids),
            unresolved_evidence_ids=(unresolved_ids),
        )


class ClaimResolutionState(StrEnum):
    READY = "ready"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    CONFLICT = "conflict"
    BLOCKED_BY_DEPENDENCY = "blocked_by_dependency"


@dataclass(
    frozen=True,
    slots=True,
)
class ClaimResolution:
    task_id: str
    state: ClaimResolutionState
    local_sufficiency: ClaimSufficiencyState
    blocking_task_ids: tuple[
        str,
        ...,
    ] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class ClaimResolutionResult:
    resolutions: tuple[
        ClaimResolution,
        ...,
    ]

    def for_task(
        self,
        task_id: str,
    ) -> ClaimResolution:
        for resolution in self.resolutions:
            if resolution.task_id == task_id:
                return resolution

        raise KeyError(f"no resolution for task: {task_id}")


class ClaimDependencyResolver:
    """
    Resolve claim readiness without source voting.

    A claim that is locally sufficient may still be
    blocked until its prerequisite claims are READY.

    Example:
      authenticity claim -> legal-effect claim

    The legal-effect claim does not get permission to
    proceed merely because it has Fiqh evidence while
    authenticity is unresolved.
    """

    def resolve(
        self,
        *,
        contracts: Iterable[ClaimSufficiencyContract],
        assessments: Iterable[ClaimSufficiencyAssessment],
    ) -> ClaimResolutionResult:
        contract_items = tuple(contracts)

        assessment_items = tuple(assessments)

        by_contract = self._contracts_by_id(contract_items)

        by_assessment = self._assessments_by_id(assessment_items)

        if set(by_contract) != set(by_assessment):
            raise ValueError(
                "dependency resolution requires exactly one assessment per contract"
            )

        order = self._topological_order(by_contract)

        resolved: dict[
            str,
            ClaimResolution,
        ] = {}

        for task_id in order:
            contract = by_contract[task_id]

            assessment = by_assessment[task_id]

            if assessment.state is ClaimSufficiencyState.CONFLICT:
                resolution = ClaimResolution(
                    task_id=task_id,
                    state=(ClaimResolutionState.CONFLICT),
                    local_sufficiency=(assessment.state),
                )
                resolved[task_id] = resolution
                continue

            if assessment.state is ClaimSufficiencyState.NEEDS_MORE_EVIDENCE:
                resolution = ClaimResolution(
                    task_id=task_id,
                    state=(ClaimResolutionState.NEEDS_MORE_EVIDENCE),
                    local_sufficiency=(assessment.state),
                )
                resolved[task_id] = resolution
                continue

            blocking = tuple(
                dependency_id
                for dependency_id in contract.dependency_task_ids
                if (resolved[dependency_id].state is not (ClaimResolutionState.READY))
            )

            if blocking:
                state = ClaimResolutionState.BLOCKED_BY_DEPENDENCY
            else:
                state = ClaimResolutionState.READY

            resolved[task_id] = ClaimResolution(
                task_id=task_id,
                state=state,
                local_sufficiency=(assessment.state),
                blocking_task_ids=blocking,
            )

        return ClaimResolutionResult(
            resolutions=tuple(resolved[task_id] for task_id in order)
        )

    @staticmethod
    def _contracts_by_id(
        contracts: tuple[
            ClaimSufficiencyContract,
            ...,
        ],
    ) -> dict[
        str,
        ClaimSufficiencyContract,
    ]:
        by_id: dict[
            str,
            ClaimSufficiencyContract,
        ] = {}

        for contract in contracts:
            if contract.task_id in by_id:
                raise ValueError(
                    "claim sufficiency contracts must have unique task IDs"
                )

            by_id[contract.task_id] = contract

        known = set(by_id)

        for contract in contracts:
            missing = set(contract.dependency_task_ids) - known

            if missing:
                raise ValueError(
                    "unknown dependency task ID: " + ", ".join(sorted(missing))
                )

        return by_id

    @staticmethod
    def _assessments_by_id(
        assessments: tuple[
            ClaimSufficiencyAssessment,
            ...,
        ],
    ) -> dict[
        str,
        ClaimSufficiencyAssessment,
    ]:
        by_id: dict[
            str,
            ClaimSufficiencyAssessment,
        ] = {}

        for assessment in assessments:
            if assessment.task_id in by_id:
                raise ValueError(
                    "claim sufficiency assessments must have unique task IDs"
                )

            by_id[assessment.task_id] = assessment

        return by_id

    @staticmethod
    def _topological_order(
        contracts: dict[
            str,
            ClaimSufficiencyContract,
        ],
    ) -> tuple[str, ...]:
        visiting: set[str] = set()
        visited: set[str] = set()
        order: list[str] = []

        def visit(
            task_id: str,
        ) -> None:
            if task_id in visited:
                return

            if task_id in visiting:
                raise ValueError("claim dependency cycle detected")

            visiting.add(task_id)

            for dependency_id in contracts[task_id].dependency_task_ids:
                visit(dependency_id)

            visiting.remove(task_id)
            visited.add(task_id)
            order.append(task_id)

        for task_id in contracts:
            visit(task_id)

        return tuple(order)
