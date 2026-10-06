from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import RLock

from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionAction,
)
from basira.evidence.service import (
    EvidenceDecisionOutcome,
)
from basira.orchestration.claim_graph import (
    ClaimGraphPlan,
    ExecutionBudget,
    ExecutionBudgetDimension,
    ExecutionBudgetExceeded,
    ExecutionBudgetViolation,
)
from basira.orchestration.contracts import (
    AgentExecutionResult,
    DelegationRequest,
)


class AgentRunLifecycle(StrEnum):
    """
    Execution lifecycle of one concrete agent run.

    This is deliberately separate from
    AgentExecutionResult.status.

    A process run may finish successfully while the
    religious claim remains unresolved.
    """

    RESERVED = "reserved"

    STARTED = "started"

    FINISHED = "finished"

    FAILED = "failed"

    CANCELLED = "cancelled"


class ExecutionTransitionError(
    RuntimeError
):
    """
    Invalid append-only execution transition.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class AgentRunReserved:
    run_id: str

    task_id: str

    agent_id: str

    capability_id: str

    delegation_id: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class AgentRunStarted:
    run_id: str


@dataclass(
    frozen=True,
    slots=True,
)
class AgentRunFinished:
    run_id: str

    result: AgentExecutionResult


@dataclass(
    frozen=True,
    slots=True,
)
class AgentRunFailed:
    run_id: str

    failure_code: str


@dataclass(
    frozen=True,
    slots=True,
)
class AgentRunCancelled:
    run_id: str

    reason: str


@dataclass(
    frozen=True,
    slots=True,
)
class DelegationAccepted:
    requesting_run_id: str

    request: DelegationRequest


@dataclass(
    frozen=True,
    slots=True,
)
class EvidenceDecisionRecorded:
    """
    Immutable record of an evidence-layer outcome.

    The ledger never accepts hand-supplied evidence
    identifiers as proof. Evidence provenance is derived
    from the EvidenceBundle produced by the deterministic
    evidence pipeline.
    """

    task_id: str

    outcome: EvidenceDecisionOutcome

    @property
    def decision(
        self,
    ) -> EvidenceDecision:
        return self.outcome.decision

    @property
    def evidence_ids(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            node.evidence_id
            for node
            in self.outcome.bundle.evidence
        )


ExecutionEventPayload = (
    AgentRunReserved
    | AgentRunStarted
    | AgentRunFinished
    | AgentRunFailed
    | AgentRunCancelled
    | DelegationAccepted
    | EvidenceDecisionRecorded
)


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionLedgerEntry:
    """
    Immutable ordered execution event envelope.

    Sequence is local to one execution ledger.
    No wall-clock timestamp participates in semantic
    ordering.
    """

    execution_id: str

    sequence: int

    event: ExecutionEventPayload

    @property
    def event_id(
        self,
    ) -> str:
        return (
            f"{self.execution_id}:"
            f"event:{self.sequence}"
        )


class ExecutionLedger:
    """
    Append-only process-local execution ledger.

    The event log is the source of execution truth.
    Run lifecycle, budget consumption, accepted
    delegations, and evidence-decision history are
    projected from immutable entries.

    Reservation is protected by an in-process lock so
    check-and-append is atomic inside one Python
    process. Distributed execution will require a
    transactional persistent event store later.

    The ledger cannot:
    - grant religious authority;
    - bypass source runtime policy;
    - decide evidence sufficiency;
    - generate an answer.
    """

    def __init__(
        self,
        *,
        execution_id: str,
        plan: ClaimGraphPlan,
        budget: ExecutionBudget,
    ) -> None:
        if not execution_id.strip():
            raise ValueError(
                "execution_id must not be blank"
            )

        # Structural limits are validated before any
        # runtime execution can begin.
        budget.require_plan(
            plan
        )

        self.execution_id = (
            execution_id.strip()
        )

        self.plan = plan

        self.budget = budget

        self._entries: list[
            ExecutionLedgerEntry
        ] = []

        self._lock = RLock()

    @property
    def entries(
        self,
    ) -> tuple[
        ExecutionLedgerEntry,
        ...,
    ]:
        with self._lock:
            return tuple(
                self._entries
            )

    def _append(
        self,
        event: ExecutionEventPayload,
    ) -> ExecutionLedgerEntry:
        entry = ExecutionLedgerEntry(
            execution_id=(
                self.execution_id
            ),
            sequence=(
                len(
                    self._entries
                )
                + 1
            ),
            event=event,
        )

        self._entries.append(
            entry
        )

        return entry

    def _require_task(
        self,
        task_id: str,
    ) -> None:
        if not task_id.strip():
            raise ValueError(
                "task_id must not be blank"
            )

        try:
            self.plan.task(
                task_id
            )
        except KeyError as exc:
            raise ValueError(
                "unknown claim task: "
                f"{task_id}"
            ) from exc

    def _reservation(
        self,
        run_id: str,
    ) -> AgentRunReserved:
        for entry in self._entries:
            event = entry.event

            if (
                isinstance(
                    event,
                    AgentRunReserved,
                )
                and event.run_id
                == run_id
            ):
                return event

        raise KeyError(
            run_id
        )

    def run_lifecycle(
        self,
        run_id: str,
    ) -> AgentRunLifecycle:
        self._reservation(
            run_id
        )

        state = (
            AgentRunLifecycle.RESERVED
        )

        for entry in self._entries:
            event = entry.event

            if (
                isinstance(
                    event,
                    AgentRunStarted,
                )
                and event.run_id
                == run_id
            ):
                state = (
                    AgentRunLifecycle.STARTED
                )

            elif (
                isinstance(
                    event,
                    AgentRunFinished,
                )
                and event.run_id
                == run_id
            ):
                state = (
                    AgentRunLifecycle.FINISHED
                )

            elif (
                isinstance(
                    event,
                    AgentRunFailed,
                )
                and event.run_id
                == run_id
            ):
                state = (
                    AgentRunLifecycle.FAILED
                )

            elif (
                isinstance(
                    event,
                    AgentRunCancelled,
                )
                and event.run_id
                == run_id
            ):
                state = (
                    AgentRunLifecycle.CANCELLED
                )

        return state

    def _run_is_active(
        self,
        run_id: str,
    ) -> bool:
        return self.run_lifecycle(
            run_id
        ) in {
            AgentRunLifecycle.RESERVED,
            AgentRunLifecycle.STARTED,
        }

    def reserved_run_count(
        self,
    ) -> int:
        return sum(
            isinstance(
                entry.event,
                AgentRunReserved,
            )
            for entry
            in self._entries
        )

    def accepted_delegation_count(
        self,
    ) -> int:
        return sum(
            isinstance(
                entry.event,
                DelegationAccepted,
            )
            for entry
            in self._entries
        )

    def distinct_agents_for_task(
        self,
        task_id: str,
    ) -> frozenset[
        str
    ]:
        self._require_task(
            task_id
        )

        return frozenset(
            event.agent_id
            for entry
            in self._entries
            if isinstance(
                (
                    event
                    := entry.event
                ),
                AgentRunReserved,
            )
            and event.task_id
            == task_id
        )

    def active_run_ids(
        self,
        task_id: str,
    ) -> tuple[
        str,
        ...,
    ]:
        self._require_task(
            task_id
        )

        run_ids = tuple(
            event.run_id
            for entry
            in self._entries
            if isinstance(
                (
                    event
                    := entry.event
                ),
                AgentRunReserved,
            )
            and event.task_id
            == task_id
        )

        return tuple(
            run_id
            for run_id
            in run_ids
            if self._run_is_active(
                run_id
            )
        )

    def decision_history(
        self,
        task_id: str,
    ) -> tuple[
        EvidenceDecisionRecorded,
        ...,
    ]:
        self._require_task(
            task_id
        )

        return tuple(
            event
            for entry
            in self._entries
            if isinstance(
                (
                    event
                    := entry.event
                ),
                EvidenceDecisionRecorded,
            )
            and event.task_id
            == task_id
        )

    def latest_decision(
        self,
        task_id: str,
    ) -> EvidenceDecision | None:
        history = (
            self.decision_history(
                task_id
            )
        )

        if not history:
            return None

        return history[
            -1
        ].decision

    def autonomously_terminal(
        self,
        task_id: str,
    ) -> bool:
        """
        Whether autonomous orchestration must stop for
        this claim.

        RETRIEVE_MORE is deliberately the only decision
        that permits another autonomous retrieval/run
        cycle.

        This does not claim that ABSTAIN or ESCALATE
        semantically solved the user's religious claim.
        It only closes autonomous execution.
        """

        decision = (
            self.latest_decision(
                task_id
            )
        )

        if decision is None:
            return False

        return (
            decision.action
            is not EvidenceDecisionAction
            .RETRIEVE_MORE
        )

    def _require_autonomous_open(
        self,
        task_id: str,
    ) -> None:
        if self.autonomously_terminal(
            task_id
        ):
            raise ExecutionTransitionError(
                "claim is terminal for "
                "autonomous execution: "
                f"{task_id}"
            )

    def _accepted_delegation(
        self,
        delegation_id: str,
    ) -> DelegationAccepted | None:
        for entry in self._entries:
            event = entry.event

            if (
                isinstance(
                    event,
                    DelegationAccepted,
                )
                and event
                .request
                .delegation_id
                == delegation_id
            ):
                return event

        return None

    def _find_delegation_request(
        self,
        delegation_id: str,
    ) -> tuple[
        str,
        DelegationRequest,
    ]:
        matches: list[
            tuple[
                str,
                DelegationRequest,
            ]
        ] = []

        for entry in self._entries:
            event = entry.event

            if not isinstance(
                event,
                AgentRunFinished,
            ):
                continue

            for request in (
                event
                .result
                .delegations
            ):
                if (
                    request
                    .delegation_id
                    == delegation_id
                ):
                    matches.append(
                        (
                            event.run_id,
                            request,
                        )
                    )

        if not matches:
            raise ValueError(
                "unknown delegation request: "
                f"{delegation_id}"
            )

        if len(
            matches
        ) != 1:
            raise ExecutionTransitionError(
                "delegation id is ambiguous "
                "inside execution ledger: "
                f"{delegation_id}"
            )

        return matches[
            0
        ]

    def reserve_run(
        self,
        *,
        run_id: str,
        task_id: str,
        agent_id: str,
        capability_id: str,
        delegation_id: str | None = None,
    ) -> ExecutionLedgerEntry:
        """
        Atomically reserve runtime budget before an
        agent is allowed to execute.
        """

        with self._lock:
            if not run_id.strip():
                raise ValueError(
                    "run_id must not be blank"
                )

            if not agent_id.strip():
                raise ValueError(
                    "agent_id must not be blank"
                )

            if not capability_id.strip():
                raise ValueError(
                    "capability_id must not "
                    "be blank"
                )

            self._require_task(
                task_id
            )

            self._require_autonomous_open(
                task_id
            )

            try:
                self._reservation(
                    run_id
                )
            except KeyError:
                pass
            else:
                raise ExecutionTransitionError(
                    "run_id already reserved: "
                    f"{run_id}"
                )

            if delegation_id is not None:
                if not delegation_id.strip():
                    raise ValueError(
                        "delegation_id must not "
                        "be blank"
                    )

                accepted = (
                    self._accepted_delegation(
                        delegation_id
                    )
                )

                if accepted is None:
                    raise ExecutionTransitionError(
                        "delegation must be accepted "
                        "before reserving a run: "
                        f"{delegation_id}"
                    )

                if (
                    accepted
                    .request
                    .task_id
                    != task_id
                ):
                    raise ExecutionTransitionError(
                        "delegation task does not "
                        "match run task"
                    )

                for entry in self._entries:
                    event = entry.event

                    if (
                        isinstance(
                            event,
                            AgentRunReserved,
                        )
                        and event.delegation_id
                        == delegation_id
                    ):
                        raise ExecutionTransitionError(
                            "delegation already "
                            "consumed by a run: "
                            f"{delegation_id}"
                        )

            observed_runs = (
                self.reserved_run_count()
                + 1
            )

            if (
                observed_runs
                > self
                .budget
                .max_total_agent_runs
            ):
                raise ExecutionBudgetExceeded(
                    ExecutionBudgetViolation(
                        dimension=(
                            ExecutionBudgetDimension
                            .TOTAL_AGENT_RUNS
                        ),
                        observed=observed_runs,
                        limit=(
                            self
                            .budget
                            .max_total_agent_runs
                        ),
                    )
                )

            distinct_agents = set(
                self.distinct_agents_for_task(
                    task_id
                )
            )

            if (
                agent_id
                not in distinct_agents
            ):
                observed_agents = (
                    len(
                        distinct_agents
                    )
                    + 1
                )

                if (
                    observed_agents
                    > self
                    .budget
                    .max_agents_per_claim
                ):
                    raise (
                        ExecutionBudgetExceeded(
                            ExecutionBudgetViolation(
                                dimension=(
                                    ExecutionBudgetDimension
                                    .AGENTS_PER_CLAIM
                                ),
                                observed=(
                                    observed_agents
                                ),
                                limit=(
                                    self
                                    .budget
                                    .max_agents_per_claim
                                ),
                            )
                        )
                    )

            for entry in self._entries:
                event = entry.event

                if not isinstance(
                    event,
                    AgentRunReserved,
                ):
                    continue

                if (
                    event.task_id
                    == task_id
                    and event.agent_id
                    == agent_id
                    and self._run_is_active(
                        event.run_id
                    )
                ):
                    raise ExecutionTransitionError(
                        "agent already has an "
                        "active run for claim"
                    )

            return self._append(
                AgentRunReserved(
                    run_id=run_id.strip(),
                    task_id=task_id,
                    agent_id=agent_id.strip(),
                    capability_id=(
                        capability_id.strip()
                    ),
                    delegation_id=(
                        delegation_id
                    ),
                )
            )

    def start_run(
        self,
        run_id: str,
    ) -> ExecutionLedgerEntry:
        with self._lock:
            state = (
                self.run_lifecycle(
                    run_id
                )
            )

            if (
                state
                is not AgentRunLifecycle
                .RESERVED
            ):
                raise ExecutionTransitionError(
                    "run can start only from "
                    "RESERVED state"
                )

            return self._append(
                AgentRunStarted(
                    run_id=run_id,
                )
            )

    def finish_run(
        self,
        *,
        run_id: str,
        result: AgentExecutionResult,
    ) -> ExecutionLedgerEntry:
        with self._lock:
            state = (
                self.run_lifecycle(
                    run_id
                )
            )

            if (
                state
                is not AgentRunLifecycle
                .STARTED
            ):
                raise ExecutionTransitionError(
                    "run can finish only from "
                    "STARTED state"
                )

            reservation = (
                self._reservation(
                    run_id
                )
            )

            if (
                result.task_id
                != reservation.task_id
            ):
                raise ExecutionTransitionError(
                    "agent result task_id does not "
                    "match reserved run"
                )

            if (
                result.agent_id
                != reservation.agent_id
            ):
                raise ExecutionTransitionError(
                    "agent result agent_id does not "
                    "match reserved run"
                )

            known_delegation_ids = {
                request.delegation_id
                for entry
                in self._entries
                if isinstance(
                    (
                        event
                        := entry.event
                    ),
                    AgentRunFinished,
                )
                for request
                in event
                .result
                .delegations
            }

            incoming_ids = {
                request.delegation_id
                for request
                in result.delegations
            }

            duplicate_ids = (
                known_delegation_ids
                & incoming_ids
            )

            if duplicate_ids:
                raise ExecutionTransitionError(
                    "delegation ids must be "
                    "unique across execution: "
                    + ", ".join(
                        sorted(
                            duplicate_ids
                        )
                    )
                )

            return self._append(
                AgentRunFinished(
                    run_id=run_id,
                    result=result,
                )
            )

    def fail_run(
        self,
        *,
        run_id: str,
        failure_code: str,
    ) -> ExecutionLedgerEntry:
        with self._lock:
            if not failure_code.strip():
                raise ValueError(
                    "failure_code must not "
                    "be blank"
                )

            state = (
                self.run_lifecycle(
                    run_id
                )
            )

            if (
                state
                is not AgentRunLifecycle
                .STARTED
            ):
                raise ExecutionTransitionError(
                    "run can fail only from "
                    "STARTED state"
                )

            return self._append(
                AgentRunFailed(
                    run_id=run_id,
                    failure_code=(
                        failure_code.strip()
                    ),
                )
            )

    def cancel_run(
        self,
        *,
        run_id: str,
        reason: str,
    ) -> ExecutionLedgerEntry:
        with self._lock:
            if not reason.strip():
                raise ValueError(
                    "cancellation reason must "
                    "not be blank"
                )

            state = (
                self.run_lifecycle(
                    run_id
                )
            )

            if state not in {
                AgentRunLifecycle.RESERVED,
                AgentRunLifecycle.STARTED,
            }:
                raise ExecutionTransitionError(
                    "only active runs may "
                    "be cancelled"
                )

            return self._append(
                AgentRunCancelled(
                    run_id=run_id,
                    reason=reason.strip(),
                )
            )

    def accept_delegation(
        self,
        delegation_id: str,
    ) -> ExecutionLedgerEntry:
        """
        Accept one agent-requested capability
        delegation.

        Merely requesting delegation does not consume
        delegation budget. Acceptance does.
        """

        with self._lock:
            if not delegation_id.strip():
                raise ValueError(
                    "delegation_id must not "
                    "be blank"
                )

            requesting_run_id, request = (
                self._find_delegation_request(
                    delegation_id
                )
            )

            self._require_autonomous_open(
                request.task_id
            )

            if (
                self._accepted_delegation(
                    delegation_id
                )
                is not None
            ):
                raise ExecutionTransitionError(
                    "delegation already accepted: "
                    f"{delegation_id}"
                )

            observed = (
                self
                .accepted_delegation_count()
                + 1
            )

            if (
                observed
                > self
                .budget
                .max_delegations
            ):
                raise ExecutionBudgetExceeded(
                    ExecutionBudgetViolation(
                        dimension=(
                            ExecutionBudgetDimension
                            .DELEGATIONS
                        ),
                        observed=observed,
                        limit=(
                            self
                            .budget
                            .max_delegations
                        ),
                    )
                )

            return self._append(
                DelegationAccepted(
                    requesting_run_id=(
                        requesting_run_id
                    ),
                    request=request,
                )
            )

    def record_evidence_outcome(
        self,
        *,
        task_id: str,
        outcome: EvidenceDecisionOutcome,
    ) -> ExecutionLedgerEntry:
        """
        Record an outcome already produced by Basira's
        deterministic evidence layer.

        The ledger records the complete outcome. It does
        not construct evidence, choose source authority,
        decide sufficiency, or accept hand-supplied
        evidence identifiers.
        """

        with self._lock:
            self._require_task(
                task_id
            )

            if self.active_run_ids(
                task_id
            ):
                raise ExecutionTransitionError(
                    "cannot record evidence outcome "
                    "while claim has active runs"
                )

            if self.autonomously_terminal(
                task_id
            ):
                raise ExecutionTransitionError(
                    "claim already has terminal "
                    "autonomous evidence decision"
                )

            return self._append(
                EvidenceDecisionRecorded(
                    task_id=task_id,
                    outcome=outcome,
                )
            )
