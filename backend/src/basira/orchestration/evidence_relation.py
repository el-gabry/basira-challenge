from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from basira.evidence.models import (
    EvidenceNode,
)
from basira.orchestration.contracts import (
    ClaimTask,
)
from basira.orchestration.evidence_acceptance import (
    TaskEvidenceAcceptanceResult,
)


class ClaimEvidenceRelation(StrEnum):
    """
    Semantic relation of one source-derived EvidenceNode
    to one claim task.

    This is deliberately separate from:
    - source authority,
    - structural anchor validity,
    - evidence sufficiency,
    - religious truth,
    - final answerability.
    """

    SUPPORTS = "supports"
    CONTEXT_ONLY = "context_only"
    PARTIAL = "partial"
    CONTRADICTS = "contradicts"
    IRRELEVANT = "irrelevant"
    UNKNOWN = "unknown"


class RelationOrigin(StrEnum):
    """
    Provenance of the relation judgment itself.

    UNASSESSED is a fail-closed system state, not a
    semantic judgment.
    """

    DETERMINISTIC = "deterministic"
    MODEL = "model"
    HUMAN = "human"
    UNASSESSED = "unassessed"


@dataclass(
    frozen=True,
    slots=True,
)
class ClaimEvidenceRelationRecord:
    task_id: str
    evidence_id: str
    relation: ClaimEvidenceRelation
    origin: RelationOrigin
    confidence: float | None = None
    rationale: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must not be blank")

        if not self.evidence_id.strip():
            raise ValueError("evidence_id must not be blank")

        if (
            self.origin is RelationOrigin.UNASSESSED
            and self.relation is not ClaimEvidenceRelation.UNKNOWN
        ):
            raise ValueError("unassessed relation must be unknown")

        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("confidence must be between 0 and 1")

        if self.rationale is not None:
            cleaned = self.rationale.strip()

            if not cleaned:
                raise ValueError("rationale must not be blank when provided")

            object.__setattr__(
                self,
                "rationale",
                cleaned,
            )


@dataclass(
    frozen=True,
    slots=True,
)
class TaskEvidenceRelationAssessment:
    """
    Claim-scoped semantic relation ledger.

    IMPORTANT:
    This result does not say whether the claim is true
    and does not say whether Basira may answer.

    A later sufficiency/decision layer must decide what
    to do with SUPPORTS, CONTEXT_ONLY, PARTIAL,
    CONTRADICTS, and UNKNOWN.
    """

    task_id: str
    records: tuple[
        ClaimEvidenceRelationRecord,
        ...,
    ]

    @property
    def supporting_evidence_ids(
        self,
    ) -> tuple[str, ...]:
        return self._ids_for(ClaimEvidenceRelation.SUPPORTS)

    @property
    def context_only_evidence_ids(
        self,
    ) -> tuple[str, ...]:
        return self._ids_for(ClaimEvidenceRelation.CONTEXT_ONLY)

    @property
    def partial_evidence_ids(
        self,
    ) -> tuple[str, ...]:
        return self._ids_for(ClaimEvidenceRelation.PARTIAL)

    @property
    def contradicting_evidence_ids(
        self,
    ) -> tuple[str, ...]:
        return self._ids_for(ClaimEvidenceRelation.CONTRADICTS)

    @property
    def irrelevant_evidence_ids(
        self,
    ) -> tuple[str, ...]:
        return self._ids_for(ClaimEvidenceRelation.IRRELEVANT)

    @property
    def unknown_evidence_ids(
        self,
    ) -> tuple[str, ...]:
        return self._ids_for(ClaimEvidenceRelation.UNKNOWN)

    @property
    def has_positive_support(
        self,
    ) -> bool:
        return bool(self.supporting_evidence_ids)

    @property
    def has_contradiction(
        self,
    ) -> bool:
        return bool(self.contradicting_evidence_ids)

    @property
    def has_unresolved_relations(
        self,
    ) -> bool:
        return bool(self.partial_evidence_ids or self.unknown_evidence_ids)

    @property
    def usable_evidence_ids(
        self,
    ) -> tuple[str, ...]:
        """
        Evidence that may continue to later reasoning.

        CONTRADICTS is intentionally retained because a
        conflict-aware layer needs to see it. IRRELEVANT
        and UNKNOWN are excluded. PARTIAL is retained but
        must not satisfy a positive support obligation.
        """

        allowed = {
            ClaimEvidenceRelation.SUPPORTS,
            ClaimEvidenceRelation.CONTEXT_ONLY,
            ClaimEvidenceRelation.PARTIAL,
            ClaimEvidenceRelation.CONTRADICTS,
        }

        return tuple(
            record.evidence_id for record in self.records if record.relation in allowed
        )

    def _ids_for(
        self,
        relation: ClaimEvidenceRelation,
    ) -> tuple[str, ...]:
        return tuple(
            record.evidence_id for record in self.records if record.relation is relation
        )


class ClaimEvidenceRelationEvaluator(
    Protocol,
):
    """
    Pluggable semantic evaluator boundary.

    Implementations may be deterministic, model-backed,
    or human-reviewed, but may return only a relation
    judgment. They may not create/modify EvidenceNode,
    grant source authority, grade hadith, or issue a
    religious ruling.
    """

    def evaluate(
        self,
        *,
        task: ClaimTask,
        evidence: EvidenceNode,
    ) -> ClaimEvidenceRelationRecord: ...


class FailClosedRelationEvaluator:
    """
    Safe default when no semantic evaluator is enabled.
    """

    def evaluate(
        self,
        *,
        task: ClaimTask,
        evidence: EvidenceNode,
    ) -> ClaimEvidenceRelationRecord:
        return ClaimEvidenceRelationRecord(
            task_id=task.task_id,
            evidence_id=(evidence.evidence_id),
            relation=(ClaimEvidenceRelation.UNKNOWN),
            origin=(RelationOrigin.UNASSESSED),
        )


class ClaimEvidenceRelationGate:
    """
    Validate and complete one task's relation ledger.

    Missing semantic judgments become UNKNOWN.
    Unknown evidence IDs, wrong task IDs, or duplicate
    judgments fail closed.
    """

    def assess(
        self,
        *,
        task_id: str,
        evidence: Iterable[EvidenceNode],
        records: Iterable[ClaimEvidenceRelationRecord],
    ) -> TaskEvidenceRelationAssessment:
        if not task_id.strip():
            raise ValueError("task_id must not be blank")

        nodes = tuple(evidence)

        evidence_ids = tuple(node.evidence_id for node in nodes)

        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique before relation assessment")

        evidence_id_set = set(evidence_ids)

        by_evidence_id: dict[
            str,
            ClaimEvidenceRelationRecord,
        ] = {}

        for record in records:
            if record.task_id != task_id:
                raise ValueError("relation record belongs to a different task")

            if record.evidence_id not in evidence_id_set:
                raise ValueError("relation record references unknown evidence")

            if record.evidence_id in by_evidence_id:
                raise ValueError("duplicate relation record for the same evidence")

            by_evidence_id[record.evidence_id] = record

        completed = tuple(
            by_evidence_id.get(
                evidence_id,
                ClaimEvidenceRelationRecord(
                    task_id=task_id,
                    evidence_id=evidence_id,
                    relation=(ClaimEvidenceRelation.UNKNOWN),
                    origin=(RelationOrigin.UNASSESSED),
                ),
            )
            for evidence_id in evidence_ids
        )

        return TaskEvidenceRelationAssessment(
            task_id=task_id,
            records=completed,
        )


class TaskEvidenceRelationService:
    """
    Semantic relation runs only after structural
    acceptance.

    The structural gate remains authoritative for
    domain/provenance/anchor constraints. This service
    never evaluates structurally rejected evidence.
    """

    def __init__(
        self,
        *,
        evaluator: (ClaimEvidenceRelationEvaluator | None) = None,
        gate: (ClaimEvidenceRelationGate | None) = None,
    ) -> None:
        self._evaluator = evaluator or FailClosedRelationEvaluator()
        self._gate = gate or ClaimEvidenceRelationGate()

    def evaluate(
        self,
        *,
        task: ClaimTask,
        structural: (TaskEvidenceAcceptanceResult),
    ) -> TaskEvidenceRelationAssessment:
        if structural.task_id != task.task_id:
            raise ValueError("structural assessment belongs to a different task")

        records = tuple(
            self._evaluator.evaluate(
                task=task,
                evidence=node,
            )
            for node in structural.accepted_evidence
        )

        return self._gate.assess(
            task_id=task.task_id,
            evidence=(structural.accepted_evidence),
            records=records,
        )
