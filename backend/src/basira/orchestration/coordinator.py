from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Protocol

from basira.evidence.decision import (
    EvidenceDecisionAction,
)
from basira.evidence.service import (
    EvidenceDecisionOutcome,
    EvidenceDecisionService,
)
from basira.orchestration.capability_broker import (
    CapabilityBroker,
)
from basira.orchestration.claim_graph import (
    ClaimGraphPlan,
)
from basira.orchestration.contracts import (
    AgentCapability,
    AgentExecutionResult,
    ClaimTask,
    DelegationRequest,
)
from basira.orchestration.execution_ledger import (
    ExecutionLedger,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)

_RELEASE_DECISIONS = frozenset(
    {
        EvidenceDecisionAction.ANSWER,
        EvidenceDecisionAction.ANSWER_WITH_LIMITATION,
    }
)

_BLOCKING_DECISIONS = frozenset(
    {
        EvidenceDecisionAction.ABSTAIN,
        EvidenceDecisionAction.ESCALATE_TO_EXPERT,
    }
)


class CoordinatorPolicyError(
    RuntimeError
):
    """
    The execution layer attempted behavior outside the
    registered orchestration contract.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class AgentRunProduct:
    """
    Product of one capability execution.

    `result` is the agent execution fact.

    `retrieval_result` must be produced through the
    capability's existing governed retrieval path.
    It is intentionally separate from `result.evidence`:
    raw agent evidence is never promoted by the
    coordinator into trusted evidence.

    For repeated RETRIEVE_MORE passes, the retrieval
    result is expected to represent the complete current
    governed retrieval state for the claim, not merely an
    ungoverned agent-created delta.
    """

    result: AgentExecutionResult

    retrieval_result: UnifiedRetrievalResult


class CapabilityExecutor(
    Protocol
):
    """
    Execute one already-selected capability.

    Source authority remains inside the governed
    retrieval implementation behind the executor.
    """

    def execute(
        self,
        *,
        task: ClaimTask,
        capability: AgentCapability,
        delegation: (
            DelegationRequest | None
        ),
    ) -> AgentRunProduct:
        ...


class OutcomeEvaluator(
    Protocol
):
    """
    Trusted boundary between governed retrieval and
    evidence decision.
    """

    def evaluate(
        self,
        *,
        task: ClaimTask,
        product: AgentRunProduct,
    ) -> EvidenceDecisionOutcome:
        ...


class EvidenceDecisionEvaluator:
    """
    Adapter to Basira's existing deterministic evidence
    decision service.

    The coordinator itself never manufactures an
    EvidenceDecision.
    """

    def __init__(
        self,
        service: (
            EvidenceDecisionService | None
        ) = None,
    ) -> None:
        self._service = (
            service
            or EvidenceDecisionService()
        )

    def evaluate(
        self,
        *,
        task: ClaimTask,
        product: AgentRunProduct,
    ) -> EvidenceDecisionOutcome:
        del task

        return self._service.evaluate(
            retrieval_result=(
                product.retrieval_result
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class CoordinatorRunResult:
    """
    Deterministic execution projection.

    `released_task_ids`
        Claims whose evidence decision is sufficiently
        resolved to release DAG dependents.

    `withheld_task_ids`
        Executed claims that ended in ABSTAIN or
        ESCALATE_TO_EXPERT. These are terminal but are
        deliberately not released as epistemically
        satisfied prerequisites.

    `blocked_task_ids`
        Claims prevented from running because at least
        one prerequisite was withheld.

    `unresolved_task_ids`
        Claims still at RETRIEVE_MORE or waiting on an
        unresolved prerequisite when autonomous work
        could not continue.
    """

    executed_task_ids: tuple[
        str,
        ...,
    ]

    released_task_ids: tuple[
        str,
        ...,
    ]

    withheld_task_ids: tuple[
        str,
        ...,
    ]

    blocked_task_ids: tuple[
        str,
        ...,
    ]

    unresolved_task_ids: tuple[
        str,
        ...,
    ]


class AgentCoordinator:
    """
    Minimal deterministic Agent V1 coordinator.

    Responsibilities:
    - respect ClaimGraphPlan dependency order;
    - route capability demand through CapabilityBroker;
    - reserve/start/finish runs through ExecutionLedger;
    - accept explicit delegations through the ledger;
    - send governed retrieval products to the existing
      evidence-decision boundary;
    - record only complete EvidenceDecisionOutcome
      objects in the ledger.

    Non-responsibilities:
    - selecting sources or books;
    - granting authority;
    - changing retrieval policy;
    - promoting raw agent evidence;
    - deciding sufficiency;
    - overriding the execution budget.
    """

    def __init__(
        self,
        *,
        plan: ClaimGraphPlan,
        ledger: ExecutionLedger,
        broker: CapabilityBroker,
        executor: CapabilityExecutor,
        evaluator: OutcomeEvaluator | None = None,
    ) -> None:
        self.plan = plan
        self.ledger = ledger
        self.broker = broker
        self.executor = executor
        self.evaluator = (
            evaluator
            or EvidenceDecisionEvaluator()
        )

        self._run_sequence = 0

    def _next_run_id(
        self,
        task_id: str,
    ) -> str:
        self._run_sequence += 1

        return (
            f"agent-run:"
            f"{self._run_sequence}:"
            f"{task_id}"
        )

    def _decision(
        self,
        task_id: str,
    ) -> EvidenceDecisionAction | None:
        decision = (
            self.ledger.latest_decision(
                task_id
            )
        )

        if decision is None:
            return None

        return decision.action

    def _prerequisite_state(
        self,
        task_id: str,
    ) -> str:
        """
        Return one of:
        - ready
        - waiting
        - blocked

        Terminal execution is NOT automatically treated
        as a satisfied epistemic prerequisite.
        """

        prerequisites = (
            self.plan.prerequisites(
                task_id
            )
        )

        if not prerequisites:
            return "ready"

        waiting = False

        for prerequisite_id in prerequisites:
            decision = self._decision(
                prerequisite_id
            )

            if decision in _BLOCKING_DECISIONS:
                return "blocked"

            if decision in _RELEASE_DECISIONS:
                continue

            # None and RETRIEVE_MORE both mean the
            # prerequisite is not yet epistemically
            # resolved for dependency release.
            waiting = True

        if waiting:
            return "waiting"

        return "ready"

    def _execute_once(
        self,
        *,
        task: ClaimTask,
        capability: AgentCapability,
        delegation: (
            DelegationRequest | None
        ),
    ) -> tuple[
        AgentRunProduct,
        EvidenceDecisionOutcome,
    ]:
        run_id = self._next_run_id(
            task.task_id
        )

        self.ledger.reserve_run(
            run_id=run_id,
            task_id=task.task_id,
            agent_id=capability.agent_id,
            capability_id=(
                capability.capability_id
            ),
            delegation_id=(
                None
                if delegation is None
                else delegation.delegation_id
            ),
        )

        self.ledger.start_run(
            run_id
        )

        try:
            product = self.executor.execute(
                task=task,
                capability=capability,
                delegation=delegation,
            )

            # ExecutionLedger validates that the returned
            # task/agent match the reservation.
            self.ledger.finish_run(
                run_id=run_id,
                result=product.result,
            )
        except Exception as exc:
            try:
                self.ledger.fail_run(
                    run_id=run_id,
                    failure_code=(
                        type(exc).__name__
                    ),
                )
            except Exception:
                # Preserve the original execution error.
                pass

            raise

        # Critical trust boundary:
        # do NOT derive a decision from
        # product.result.evidence.
        outcome = self.evaluator.evaluate(
            task=task,
            product=product,
        )

        self.ledger.record_evidence_outcome(
            task_id=task.task_id,
            outcome=outcome,
        )

        return (
            product,
            outcome,
        )

    def _run_claim(
        self,
        task: ClaimTask,
    ) -> None:
        """
        Run a claim until:
        - a non-RETRIEVE_MORE evidence decision exists;
        - RETRIEVE_MORE has no admissible delegation;
        - an execution/budget/policy error fails closed.
        """

        capability = (
            self.broker.select_for_task(
                task
            )
        )

        product, outcome = (
            self._execute_once(
                task=task,
                capability=capability,
                delegation=None,
            )
        )

        if (
            outcome.decision.action
            is not EvidenceDecisionAction.RETRIEVE_MORE
        ):
            return

        pending: deque[
            tuple[
                DelegationRequest,
                AgentCapability,
            ]
        ] = deque()

        def enqueue_delegations(
            *,
            source_capability: AgentCapability,
            result: AgentExecutionResult,
        ) -> None:
            delegations = tuple(
                sorted(
                    result.delegations,
                    key=lambda request: (
                        request.delegation_id
                    ),
                )
            )

            if (
                delegations
                and not source_capability.may_delegate
            ):
                raise CoordinatorPolicyError(
                    "capability emitted delegation "
                    "without delegation permission: "
                    f"{source_capability.capability_id}"
                )

            for request in delegations:
                # Selection happens before acceptance:
                # an unroutable/ambiguous request never
                # consumes delegation budget.
                selected = (
                    self.broker
                    .select_for_delegation(
                        request
                    )
                )

                pending.append(
                    (
                        request,
                        selected,
                    )
                )

        enqueue_delegations(
            source_capability=capability,
            result=product.result,
        )

        while (
            outcome.decision.action
            is EvidenceDecisionAction.RETRIEVE_MORE
            and pending
        ):
            request, selected = (
                pending.popleft()
            )

            # Acceptance is a separate governed event.
            # The ledger enforces delegation budget and
            # one-run consumption.
            self.ledger.accept_delegation(
                request.delegation_id
            )

            product, outcome = (
                self._execute_once(
                    task=task,
                    capability=selected,
                    delegation=request,
                )
            )

            if (
                outcome.decision.action
                is not EvidenceDecisionAction.RETRIEVE_MORE
            ):
                break

            enqueue_delegations(
                source_capability=selected,
                result=product.result,
            )

    def run(
        self,
    ) -> CoordinatorRunResult:
        """
        Execute all DAG claims that can be safely released.

        The graph order is deterministic. A blocked or
        unresolved branch does not prevent an unrelated
        root/branch from running.
        """

        executed: list[
            str
        ] = []

        for task_id in (
            self.plan.topological_order()
        ):
            state = (
                self._prerequisite_state(
                    task_id
                )
            )

            if state != "ready":
                continue

            if (
                self._decision(task_id)
                is not None
            ):
                continue

            task = self.plan.task(
                task_id
            )

            self._run_claim(
                task
            )

            executed.append(
                task_id
            )

        released: list[
            str
        ] = []

        withheld: list[
            str
        ] = []

        blocked: list[
            str
        ] = []

        unresolved: list[
            str
        ] = []

        for task_id in (
            self.plan.topological_order()
        ):
            decision = self._decision(
                task_id
            )

            if decision in _RELEASE_DECISIONS:
                released.append(
                    task_id
                )
                continue

            if decision in _BLOCKING_DECISIONS:
                withheld.append(
                    task_id
                )
                continue

            state = (
                self._prerequisite_state(
                    task_id
                )
            )

            if state == "blocked":
                blocked.append(
                    task_id
                )
                continue

            unresolved.append(
                task_id
            )

        return CoordinatorRunResult(
            executed_task_ids=tuple(
                executed
            ),
            released_task_ids=tuple(
                released
            ),
            withheld_task_ids=tuple(
                withheld
            ),
            blocked_task_ids=tuple(
                blocked
            ),
            unresolved_task_ids=tuple(
                unresolved
            ),
        )
