from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.evidence.models import (
    ContextRequirement,
    EvidenceNeed,
    EvidenceNode,
)
from basira.reasoning.contracts import (
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)
from basira.retrieval.query_understanding import (
    RiskTag,
)


class ContextKind(StrEnum):
    """
    Non-evidentiary context that may shape retrieval,
    applicability, delegation, or answer adaptation.

    A ContextArtifact is never positive religious
    evidence merely because it came from a governed
    source.
    """

    AUDIENCE = "audience"
    LANGUAGE = "language"
    GEOGRAPHY = "geography"
    RELIGION = "religion"
    PEOPLE_GROUP = "people_group"
    JURISDICTION = "jurisdiction"
    TEMPORAL = "temporal"
    INSTITUTION = "institution"
    TOPIC = "topic"


class ContextOrigin(StrEnum):
    """
    Provenance class for non-evidentiary context.

    Agent-generated inference is deliberately absent
    from v1. Context must be explicit from the user,
    deterministically extracted from the query, or
    obtained from a governed source.
    """

    USER = "user"
    QUERY_UNDERSTANDING = "query_understanding"
    GOVERNED_SOURCE = "governed_source"


@dataclass(
    frozen=True,
    slots=True,
)
class ContextArtifact:
    """
    Provenanced context that cannot itself satisfy an
    EvidenceNeed or support a user-facing claim.

    Confidence describes confidence in the context
    observation. It never represents religious
    authority.
    """

    context_id: str

    kind: ContextKind

    value: str

    origin: ContextOrigin

    source_id: str | None = None

    source_url: str | None = None

    confidence: float | None = None

    restrictions: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not self.context_id.strip():
            raise ValueError(
                "context_id must not be blank"
            )

        if not self.value.strip():
            raise ValueError(
                "context value must not be blank"
            )

        if (
            self.confidence is not None
            and not (
                0.0
                <= self.confidence
                <= 1.0
            )
        ):
            raise ValueError(
                "context confidence must be "
                "between 0 and 1"
            )

        if (
            self.origin
            is ContextOrigin.GOVERNED_SOURCE
            and not (
                self.source_id
                and self.source_id.strip()
            )
        ):
            raise ValueError(
                "governed-source context requires "
                "source_id"
            )

        if any(
            not restriction.strip()
            for restriction
            in self.restrictions
        ):
            raise ValueError(
                "context restrictions must not "
                "contain blank values"
            )

    @property
    def evidentiary(
        self,
    ) -> bool:
        """
        Context is deliberately non-evidentiary.

        This property is semantic documentation for
        orchestration and tests. It cannot be changed
        by an agent.
        """

        return False


@dataclass(
    frozen=True,
    slots=True,
)
class ClaimTask:
    """
    One bounded work unit in the future Basira claim
    graph.

    Existing reasoning, evidence-requirement, and risk
    contracts are reused rather than duplicated.

    A task describes one semantic claim to examine.
    It does not grant authority, choose a source, or
    declare that evidence is sufficient.

    Graph topology is deliberately NOT stored here.
    Parents, dependencies, execution depth, and shared
    subclaims belong to ClaimGraphPlan so the planner
    can represent a DAG rather than forcing a tree.
    """

    task_id: str

    claim_text: str

    frame: ReligiousReasoningFrame

    context_requirement: ContextRequirement

    risk_tags: frozenset[
        RiskTag
    ] = frozenset()

    context_ids: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not self.task_id.strip():
            raise ValueError(
                "task_id must not be blank"
            )

        if not self.claim_text.strip():
            raise ValueError(
                "claim_text must not be blank"
            )

        normalized_claim = " ".join(
            self.claim_text.split()
        )

        normalized_frame_question = " ".join(
            self.frame.question.split()
        )

        if (
            normalized_frame_question
            != normalized_claim
        ):
            raise ValueError(
                "ClaimTask reasoning frame must "
                "belong to the same claim text"
            )

        if any(
            not context_id.strip()
            for context_id
            in self.context_ids
        ):
            raise ValueError(
                "context_ids must not contain "
                "blank values"
            )

        if (
            len(
                set(
                    self.context_ids
                )
            )
            != len(
                self.context_ids
            )
        ):
            raise ValueError(
                "context_ids must be unique"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AgentCapability:
    """
    Declarative capability exposed to a future
    CapabilityBroker.

    Capability is not authority.

    This contract intentionally contains neither
    source permissions nor an authority level.
    Source access remains governed by Basira's
    existing fail-closed runtime.
    """

    capability_id: str

    agent_id: str

    disciplines: frozenset[
        ReligiousDiscipline
    ] = frozenset()

    evidence_needs: frozenset[
        EvidenceNeed
    ] = frozenset()

    context_kinds: frozenset[
        ContextKind
    ] = frozenset()

    may_delegate: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not self.capability_id.strip():
            raise ValueError(
                "capability_id must not be blank"
            )

        if not self.agent_id.strip():
            raise ValueError(
                "agent_id must not be blank"
            )

        if not (
            self.disciplines
            or self.evidence_needs
            or self.context_kinds
        ):
            raise ValueError(
                "capability must declare at least "
                "one supported dimension"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class DelegationRequest:
    """
    Request for missing capability.

    Agents request capabilities, never a concrete
    target agent. A future broker owns target
    selection and execution policy.
    """

    delegation_id: str

    task_id: str

    reason: str

    requested_disciplines: frozenset[
        ReligiousDiscipline
    ] = frozenset()

    requested_evidence_needs: frozenset[
        EvidenceNeed
    ] = frozenset()

    requested_context_kinds: frozenset[
        ContextKind
    ] = frozenset()

    def __post_init__(
        self,
    ) -> None:
        if not self.delegation_id.strip():
            raise ValueError(
                "delegation_id must not be blank"
            )

        if not self.task_id.strip():
            raise ValueError(
                "delegation task_id must not "
                "be blank"
            )

        if not self.reason.strip():
            raise ValueError(
                "delegation reason must not "
                "be blank"
            )

        if not (
            self.requested_disciplines
            or self.requested_evidence_needs
            or self.requested_context_kinds
        ):
            raise ValueError(
                "delegation must request at least "
                "one capability"
            )


class AgentExecutionStatus(StrEnum):
    """
    Execution status only.

    FINISHED never means that religious evidence is
    sufficient. Sufficiency remains owned by the
    deterministic evidence decision pipeline.
    """

    FINISHED = "finished"
    PARTIAL = "partial"
    BLOCKED = "blocked"


@dataclass(
    frozen=True,
    slots=True,
)
class AgentExecutionResult:
    """
    Typed output boundary for one specialist-agent run.

    Evidence, context, and delegation are kept
    structurally separate.

    This result contains no answer, evidence-sufficiency
    decision, source authority grant, or final religious
    judgment.
    """

    task_id: str

    agent_id: str

    status: AgentExecutionStatus

    evidence: tuple[
        EvidenceNode,
        ...,
    ] = ()

    context: tuple[
        ContextArtifact,
        ...,
    ] = ()

    delegations: tuple[
        DelegationRequest,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not self.task_id.strip():
            raise ValueError(
                "result task_id must not be blank"
            )

        if not self.agent_id.strip():
            raise ValueError(
                "result agent_id must not be blank"
            )

        evidence_ids = [
            node.evidence_id
            for node
            in self.evidence
        ]

        if (
            len(
                set(
                    evidence_ids
                )
            )
            != len(
                evidence_ids
            )
        ):
            raise ValueError(
                "agent result evidence ids "
                "must be unique"
            )

        context_ids = [
            artifact.context_id
            for artifact
            in self.context
        ]

        if (
            len(
                set(
                    context_ids
                )
            )
            != len(
                context_ids
            )
        ):
            raise ValueError(
                "agent result context ids "
                "must be unique"
            )

        delegation_ids = [
            request.delegation_id
            for request
            in self.delegations
        ]

        if (
            len(
                set(
                    delegation_ids
                )
            )
            != len(
                delegation_ids
            )
        ):
            raise ValueError(
                "agent result delegation ids "
                "must be unique"
            )

        if any(
            request.task_id
            != self.task_id
            for request
            in self.delegations
        ):
            raise ValueError(
                "delegations must belong to "
                "the result task"
            )
