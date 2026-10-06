from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from basira.evidence.models import (
    EvidenceNeed,
)
from basira.orchestration.contracts import (
    AgentCapability,
    ClaimTask,
    ContextKind,
    DelegationRequest,
)
from basira.reasoning.contracts import (
    ReligiousDiscipline,
)


class CapabilityBrokerError(RuntimeError):
    """
    Base error for deterministic capability routing.
    """


class NoMatchingCapability(
    CapabilityBrokerError
):
    """
    No registered capability can satisfy the demand.
    """


class AmbiguousCapabilitySelection(
    CapabilityBrokerError
):
    """
    More than one capability can satisfy the demand.

    V1 fails closed instead of silently preferring one
    agent or allowing a model to choose implicitly.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class CapabilityDemand:
    """
    A source-agnostic request for agent capability.

    Deliberately contains no source IDs, book IDs,
    authority classes, URLs, runtime permissions,
    or retrieval-policy material.
    """

    task_id: str

    disciplines: tuple[
        ReligiousDiscipline,
        ...,
    ] = ()

    evidence_needs: tuple[
        EvidenceNeed,
        ...,
    ] = ()

    context_kinds: tuple[
        ContextKind,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not self.task_id.strip():
            raise ValueError(
                "task_id must not be blank"
            )

        if not (
            self.disciplines
            or self.evidence_needs
            or self.context_kinds
        ):
            raise ValueError(
                "capability demand requires at "
                "least one support dimension"
            )

        if (
            len(set(self.disciplines))
            != len(self.disciplines)
        ):
            raise ValueError(
                "disciplines must be unique"
            )

        if (
            len(set(self.evidence_needs))
            != len(self.evidence_needs)
        ):
            raise ValueError(
                "evidence_needs must be unique"
            )

        if (
            len(set(self.context_kinds))
            != len(self.context_kinds)
        ):
            raise ValueError(
                "context_kinds must be unique"
            )

    @classmethod
    def from_task(
        cls,
        task: ClaimTask,
    ) -> CapabilityDemand:
        """
        Initial claim dispatch uses the claim's PRIMARY
        discipline only.

        Secondary disciplines remain explicit supporting
        work and can be dispatched separately by the
        coordinator / delegation mechanism.

        This avoids treating a multidisciplinary claim as
        permission for one agent to silently absorb all
        disciplines.
        """

        return cls(
            task_id=task.task_id,
            disciplines=(
                task.frame.primary_discipline,
            ),
        )

    @classmethod
    def from_delegation(
        cls,
        request: DelegationRequest,
    ) -> CapabilityDemand:
        """
        Delegation already carries explicit requested
        capability dimensions and no target agent.
        """

        return cls(
            task_id=request.task_id,
            disciplines=tuple(
                request.requested_disciplines
            ),
            evidence_needs=tuple(
                request.requested_evidence_needs
            ),
            context_kinds=tuple(
                request.requested_context_kinds
            ),
        )


class CapabilityBroker:
    """
    Deterministic registry and selector for agent
    capabilities.

    The broker answers only:
        "which registered capability can satisfy this
        capability demand?"

    It does NOT:
    - choose sources;
    - choose books;
    - authorize runtime use;
    - create EvidenceNode objects;
    - widen retrieval policies;
    - decide evidence sufficiency;
    - decide religious authority.
    """

    def __init__(
        self,
        capabilities: Iterable[
            AgentCapability
        ],
    ) -> None:
        ordered = tuple(
            sorted(
                capabilities,
                key=lambda capability: (
                    capability.capability_id
                ),
            )
        )

        by_id: dict[
            str,
            AgentCapability,
        ] = {}

        for capability in ordered:
            capability_id = (
                capability.capability_id
                .strip()
            )

            if capability_id in by_id:
                raise ValueError(
                    "duplicate capability_id: "
                    f"{capability_id}"
                )

            by_id[
                capability_id
            ] = capability

        self._capabilities = ordered

    @property
    def capabilities(
        self,
    ) -> tuple[
        AgentCapability,
        ...,
    ]:
        return self._capabilities

    @staticmethod
    def _matches(
        capability: AgentCapability,
        demand: CapabilityDemand,
    ) -> bool:
        """
        One capability must cover every explicitly
        requested dimension.

        Partial matching is not sufficient in V1.
        """

        capability_disciplines = set(
            capability.disciplines
        )

        capability_evidence = set(
            capability.evidence_needs
        )

        capability_context = set(
            capability.context_kinds
        )

        if (
            demand.disciplines
            and not set(
                demand.disciplines
            ).issubset(
                capability_disciplines
            )
        ):
            return False

        if (
            demand.evidence_needs
            and not set(
                demand.evidence_needs
            ).issubset(
                capability_evidence
            )
        ):
            return False

        if (
            demand.context_kinds
            and not set(
                demand.context_kinds
            ).issubset(
                capability_context
            )
        ):
            return False

        return True

    def candidates(
        self,
        demand: CapabilityDemand,
    ) -> tuple[
        AgentCapability,
        ...,
    ]:
        """
        Return matching capabilities in deterministic
        capability_id order.
        """

        return tuple(
            capability
            for capability
            in self._capabilities
            if self._matches(
                capability,
                demand,
            )
        )

    def select(
        self,
        demand: CapabilityDemand,
    ) -> AgentCapability:
        """
        Select exactly one capability.

        Zero matches and multiple matches both fail
        closed.
        """

        matches = self.candidates(
            demand
        )

        if not matches:
            raise NoMatchingCapability(
                "no registered capability can "
                f"satisfy task {demand.task_id!r}"
            )

        if len(matches) > 1:
            capability_ids = ", ".join(
                capability.capability_id
                for capability in matches
            )

            raise AmbiguousCapabilitySelection(
                "capability demand is ambiguous "
                f"for task {demand.task_id!r}: "
                f"{capability_ids}"
            )

        return matches[0]

    def select_for_task(
        self,
        task: ClaimTask,
    ) -> AgentCapability:
        return self.select(
            CapabilityDemand.from_task(
                task
            )
        )

    def select_for_delegation(
        self,
        request: DelegationRequest,
    ) -> AgentCapability:
        return self.select(
            CapabilityDemand.from_delegation(
                request
            )
        )
