from __future__ import annotations

from dataclasses import (
    fields,
)
from types import SimpleNamespace

import pytest

from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionAction,
)
from basira.evidence.models import (
    ContextRequirement,
    EvidenceNeed,
)
from basira.orchestration.capability_broker import (
    AmbiguousCapabilitySelection,
    CapabilityBroker,
)
from basira.orchestration.claim_graph import (
    ClaimDependency,
    ClaimGraphPlan,
)
from basira.orchestration.contracts import (
    AgentCapability,
    AgentExecutionResult,
    AgentExecutionStatus,
    ClaimTask,
    DelegationRequest,
)
from basira.orchestration.coordinator import (
    AgentCoordinator,
    AgentRunProduct,
    CoordinatorPolicyError,
    CoordinatorRunResult,
    EvidenceDecisionEvaluator,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)


def claim(
    task_id: str,
    *,
    discipline: ReligiousDiscipline,
) -> ClaimTask:
    text = f"Claim {task_id}"

    return ClaimTask(
        task_id=task_id,
        claim_text=text,
        frame=ReligiousReasoningFrame(
            frame_id=f"frame:{task_id}",
            question=text,
            primary_discipline=(
                discipline
            ),
            reasoning_mode=(
                ReasoningMode
                .DIRECT_GROUNDING
            ),
        ),
        context_requirement=(
            ContextRequirement()
        ),
    )


def capability(
    capability_id: str,
    *,
    agent_id: str,
    discipline: ReligiousDiscipline,
    may_delegate: bool = False,
    evidence_needs: frozenset[
        EvidenceNeed
    ] = frozenset(),
) -> AgentCapability:
    return AgentCapability(
        capability_id=capability_id,
        agent_id=agent_id,
        disciplines=frozenset(
            {
                discipline,
            }
        ),
        evidence_needs=(
            evidence_needs
        ),
        may_delegate=may_delegate,
    )


def result(
    task_id: str,
    *,
    agent_id: str,
    delegations: tuple[
        DelegationRequest,
        ...,
    ] = (),
) -> AgentExecutionResult:
    return AgentExecutionResult(
        task_id=task_id,
        agent_id=agent_id,
        status=(
            AgentExecutionStatus.FINISHED
        ),
        delegations=delegations,
    )


class FakeLedger:
    def __init__(
        self,
    ) -> None:
        self.events: list[
            tuple
        ] = []

        self.decisions: dict[
            str,
            EvidenceDecision,
        ] = {}

    def latest_decision(
        self,
        task_id: str,
    ) -> EvidenceDecision | None:
        return self.decisions.get(
            task_id
        )

    def reserve_run(
        self,
        **kwargs: object,
    ) -> None:
        self.events.append(
            (
                "reserve",
                kwargs,
            )
        )

    def start_run(
        self,
        run_id: str,
    ) -> None:
        self.events.append(
            (
                "start",
                run_id,
            )
        )

    def finish_run(
        self,
        *,
        run_id: str,
        result: AgentExecutionResult,
    ) -> None:
        self.events.append(
            (
                "finish",
                run_id,
                result.task_id,
                result.agent_id,
            )
        )

    def fail_run(
        self,
        *,
        run_id: str,
        failure_code: str,
    ) -> None:
        self.events.append(
            (
                "fail",
                run_id,
                failure_code,
            )
        )

    def accept_delegation(
        self,
        delegation_id: str,
    ) -> None:
        self.events.append(
            (
                "accept_delegation",
                delegation_id,
            )
        )

    def record_evidence_outcome(
        self,
        *,
        task_id: str,
        outcome: object,
    ) -> None:
        decision = outcome.decision

        self.decisions[
            task_id
        ] = decision

        self.events.append(
            (
                "decision",
                task_id,
                decision,
            )
        )


class QueueExecutor:
    def __init__(
        self,
        products: list[
            AgentRunProduct
        ],
    ) -> None:
        self.products = list(
            products
        )

        self.calls: list[
            tuple[
                str,
                str,
                str | None,
            ]
        ] = []

    def execute(
        self,
        *,
        task: ClaimTask,
        capability: AgentCapability,
        delegation: (
            DelegationRequest | None
        ),
    ) -> AgentRunProduct:
        self.calls.append(
            (
                task.task_id,
                capability.capability_id,
                (
                    None
                    if delegation is None
                    else delegation.delegation_id
                ),
            )
        )

        if not self.products:
            raise AssertionError(
                "unexpected executor call"
            )

        return self.products.pop(0)


class QueueEvaluator:
    def __init__(
        self,
        decisions: list[
            EvidenceDecisionAction
        ],
    ) -> None:
        self.decisions = list(
            decisions
        )

        self.calls = 0

    def evaluate(
        self,
        *,
        task: ClaimTask,
        product: AgentRunProduct,
    ) -> object:
        del task
        del product

        self.calls += 1

        if not self.decisions:
            raise AssertionError(
                "unexpected evaluator call"
            )

        action = (
            self.decisions.pop(0)
        )

        return SimpleNamespace(
            decision=EvidenceDecision(
                action=action,
                reasons=(),
            )
        )


def product(
    *,
    task_id: str,
    agent_id: str,
    delegations: tuple[
        DelegationRequest,
        ...,
    ] = (),
) -> AgentRunProduct:
    return AgentRunProduct(
        result=result(
            task_id,
            agent_id=agent_id,
            delegations=delegations,
        ),
        retrieval_result=object(),  # type: ignore[arg-type]
    )


def test_dependency_releases_only_after_answer() -> None:
    root = claim(
        "root",
        discipline=ReligiousDiscipline.QURAN,
    )

    child = claim(
        "child",
        discipline=ReligiousDiscipline.HADITH,
    )

    plan = ClaimGraphPlan(
        tasks=(
            child,
            root,
        ),
        dependencies=(
            ClaimDependency(
                prerequisite_task_id="root",
                dependent_task_id="child",
                reason="child depends on root",
            ),
        ),
    )

    broker = CapabilityBroker(
        (
            capability(
                "cap:quran",
                agent_id="agent:quran",
                discipline=(
                    ReligiousDiscipline.QURAN
                ),
            ),
            capability(
                "cap:hadith",
                agent_id="agent:hadith",
                discipline=(
                    ReligiousDiscipline.HADITH
                ),
            ),
        )
    )

    executor = QueueExecutor(
        [
            product(
                task_id="root",
                agent_id="agent:quran",
            ),
            product(
                task_id="child",
                agent_id="agent:hadith",
            ),
        ]
    )

    evaluator = QueueEvaluator(
        [
            EvidenceDecisionAction.ANSWER,
            EvidenceDecisionAction.ANSWER,
        ]
    )

    ledger = FakeLedger()

    outcome = AgentCoordinator(
        plan=plan,
        ledger=ledger,  # type: ignore[arg-type]
        broker=broker,
        executor=executor,
        evaluator=evaluator,  # type: ignore[arg-type]
    ).run()

    assert outcome.executed_task_ids == (
        "root",
        "child",
    )

    assert outcome.released_task_ids == (
        "root",
        "child",
    )

    assert outcome.withheld_task_ids == ()

    assert outcome.blocked_task_ids == ()

    assert outcome.unresolved_task_ids == ()


def test_abstain_does_not_release_dependent_claim() -> None:
    root = claim(
        "root",
        discipline=ReligiousDiscipline.QURAN,
    )

    child = claim(
        "child",
        discipline=ReligiousDiscipline.HADITH,
    )

    plan = ClaimGraphPlan(
        tasks=(
            root,
            child,
        ),
        dependencies=(
            ClaimDependency(
                prerequisite_task_id="root",
                dependent_task_id="child",
                reason="requires root",
            ),
        ),
    )

    broker = CapabilityBroker(
        (
            capability(
                "cap:quran",
                agent_id="agent:quran",
                discipline=(
                    ReligiousDiscipline.QURAN
                ),
            ),
            capability(
                "cap:hadith",
                agent_id="agent:hadith",
                discipline=(
                    ReligiousDiscipline.HADITH
                ),
            ),
        )
    )

    executor = QueueExecutor(
        [
            product(
                task_id="root",
                agent_id="agent:quran",
            ),
        ]
    )

    ledger = FakeLedger()

    outcome = AgentCoordinator(
        plan=plan,
        ledger=ledger,  # type: ignore[arg-type]
        broker=broker,
        executor=executor,
        evaluator=QueueEvaluator(
            [
                EvidenceDecisionAction.ABSTAIN,
            ]
        ),  # type: ignore[arg-type]
    ).run()

    assert outcome.executed_task_ids == (
        "root",
    )

    assert outcome.released_task_ids == ()

    assert outcome.withheld_task_ids == (
        "root",
    )

    assert outcome.blocked_task_ids == (
        "child",
    )

    assert outcome.unresolved_task_ids == ()

    assert executor.calls == [
        (
            "root",
            "cap:quran",
            None,
        ),
    ]


def test_retrieve_more_without_delegation_stays_unresolved() -> None:
    root = claim(
        "root",
        discipline=ReligiousDiscipline.QURAN,
    )

    child = claim(
        "child",
        discipline=ReligiousDiscipline.HADITH,
    )

    plan = ClaimGraphPlan(
        tasks=(
            root,
            child,
        ),
        dependencies=(
            ClaimDependency(
                prerequisite_task_id="root",
                dependent_task_id="child",
                reason="requires root",
            ),
        ),
    )

    broker = CapabilityBroker(
        (
            capability(
                "cap:quran",
                agent_id="agent:quran",
                discipline=(
                    ReligiousDiscipline.QURAN
                ),
            ),
            capability(
                "cap:hadith",
                agent_id="agent:hadith",
                discipline=(
                    ReligiousDiscipline.HADITH
                ),
            ),
        )
    )

    outcome = AgentCoordinator(
        plan=plan,
        ledger=FakeLedger(),  # type: ignore[arg-type]
        broker=broker,
        executor=QueueExecutor(
            [
                product(
                    task_id="root",
                    agent_id="agent:quran",
                ),
            ]
        ),
        evaluator=QueueEvaluator(
            [
                EvidenceDecisionAction.RETRIEVE_MORE,
            ]
        ),  # type: ignore[arg-type]
    ).run()

    assert outcome.executed_task_ids == (
        "root",
    )

    assert outcome.released_task_ids == ()

    assert outcome.blocked_task_ids == ()

    assert outcome.unresolved_task_ids == (
        "root",
        "child",
    )


def test_retrieve_more_can_use_explicit_delegation() -> None:
    task = claim(
        "claim",
        discipline=ReligiousDiscipline.FIQH,
    )

    delegation = DelegationRequest(
        delegation_id="delegation:hadith",
        task_id="claim",
        reason="Need hadith grading",
        requested_disciplines=frozenset(
            {
                ReligiousDiscipline.HADITH,
            }
        ),
        requested_evidence_needs=frozenset(
            {
                EvidenceNeed.HADITH_GRADE,
            }
        ),
    )

    fiqh = capability(
        "cap:fiqh",
        agent_id="agent:fiqh",
        discipline=ReligiousDiscipline.FIQH,
        may_delegate=True,
    )

    hadith = capability(
        "cap:hadith-grade",
        agent_id="agent:hadith",
        discipline=ReligiousDiscipline.HADITH,
        evidence_needs=frozenset(
            {
                EvidenceNeed.HADITH_GRADE,
            }
        ),
    )

    ledger = FakeLedger()

    executor = QueueExecutor(
        [
            product(
                task_id="claim",
                agent_id="agent:fiqh",
                delegations=(
                    delegation,
                ),
            ),
            product(
                task_id="claim",
                agent_id="agent:hadith",
            ),
        ]
    )

    outcome = AgentCoordinator(
        plan=ClaimGraphPlan(
            tasks=(
                task,
            )
        ),
        ledger=ledger,  # type: ignore[arg-type]
        broker=CapabilityBroker(
            (
                fiqh,
                hadith,
            )
        ),
        executor=executor,
        evaluator=QueueEvaluator(
            [
                EvidenceDecisionAction.RETRIEVE_MORE,
                EvidenceDecisionAction.ANSWER,
            ]
        ),  # type: ignore[arg-type]
    ).run()

    assert outcome.released_task_ids == (
        "claim",
    )

    assert executor.calls == [
        (
            "claim",
            "cap:fiqh",
            None,
        ),
        (
            "claim",
            "cap:hadith-grade",
            "delegation:hadith",
        ),
    ]

    event_names = [
        event[0]
        for event in ledger.events
    ]

    acceptance_index = (
        event_names.index(
            "accept_delegation"
        )
    )

    delegated_reserve_index = (
        [
            index
            for index, event
            in enumerate(
                ledger.events
            )
            if (
                event[0] == "reserve"
                and event[1].get(
                    "delegation_id"
                )
                == "delegation:hadith"
            )
        ][0]
    )

    assert (
        acceptance_index
        < delegated_reserve_index
    )


def test_capability_without_permission_cannot_delegate() -> None:
    task = claim(
        "claim",
        discipline=ReligiousDiscipline.FIQH,
    )

    delegation = DelegationRequest(
        delegation_id="delegation:1",
        task_id="claim",
        reason="Need support",
        requested_disciplines=frozenset(
            {
                ReligiousDiscipline.HADITH,
            }
        ),
    )

    broker = CapabilityBroker(
        (
            capability(
                "cap:fiqh",
                agent_id="agent:fiqh",
                discipline=(
                    ReligiousDiscipline.FIQH
                ),
                may_delegate=False,
            ),
            capability(
                "cap:hadith",
                agent_id="agent:hadith",
                discipline=(
                    ReligiousDiscipline.HADITH
                ),
            ),
        )
    )

    ledger = FakeLedger()

    coordinator = AgentCoordinator(
        plan=ClaimGraphPlan(
            tasks=(task,)
        ),
        ledger=ledger,  # type: ignore[arg-type]
        broker=broker,
        executor=QueueExecutor(
            [
                product(
                    task_id="claim",
                    agent_id="agent:fiqh",
                    delegations=(
                        delegation,
                    ),
                ),
            ]
        ),
        evaluator=QueueEvaluator(
            [
                EvidenceDecisionAction.RETRIEVE_MORE,
            ]
        ),  # type: ignore[arg-type]
    )

    with pytest.raises(
        CoordinatorPolicyError,
        match="without delegation permission",
    ):
        coordinator.run()

    assert not any(
        event[0]
        == "accept_delegation"
        for event in ledger.events
    )


def test_ambiguous_capability_fails_before_run_reservation() -> None:
    task = claim(
        "claim",
        discipline=ReligiousDiscipline.FIQH,
    )

    broker = CapabilityBroker(
        (
            capability(
                "cap:a",
                agent_id="agent:a",
                discipline=(
                    ReligiousDiscipline.FIQH
                ),
            ),
            capability(
                "cap:b",
                agent_id="agent:b",
                discipline=(
                    ReligiousDiscipline.FIQH
                ),
            ),
        )
    )

    ledger = FakeLedger()

    coordinator = AgentCoordinator(
        plan=ClaimGraphPlan(
            tasks=(task,)
        ),
        ledger=ledger,  # type: ignore[arg-type]
        broker=broker,
        executor=QueueExecutor([]),
        evaluator=QueueEvaluator([]),  # type: ignore[arg-type]
    )

    with pytest.raises(
        AmbiguousCapabilitySelection
    ):
        coordinator.run()

    assert ledger.events == []


class FailingExecutor:
    def execute(
        self,
        *,
        task: ClaimTask,
        capability: AgentCapability,
        delegation: (
            DelegationRequest | None
        ),
    ) -> AgentRunProduct:
        del task
        del capability
        del delegation

        raise RuntimeError(
            "executor exploded"
        )


def test_executor_failure_is_recorded_as_execution_fact() -> None:
    task = claim(
        "claim",
        discipline=ReligiousDiscipline.QURAN,
    )

    ledger = FakeLedger()

    coordinator = AgentCoordinator(
        plan=ClaimGraphPlan(
            tasks=(task,)
        ),
        ledger=ledger,  # type: ignore[arg-type]
        broker=CapabilityBroker(
            (
                capability(
                    "cap:quran",
                    agent_id="agent:quran",
                    discipline=(
                        ReligiousDiscipline.QURAN
                    ),
                ),
            )
        ),
        executor=FailingExecutor(),
        evaluator=QueueEvaluator([]),  # type: ignore[arg-type]
    )

    with pytest.raises(
        RuntimeError,
        match="executor exploded",
    ):
        coordinator.run()

    assert any(
        (
            event[0] == "fail"
            and event[2] == "RuntimeError"
        )
        for event in ledger.events
    )

    assert not any(
        event[0] == "decision"
        for event in ledger.events
    )


def test_finished_agent_result_does_not_imply_answer() -> None:
    task = claim(
        "claim",
        discipline=ReligiousDiscipline.QURAN,
    )

    coordinator = AgentCoordinator(
        plan=ClaimGraphPlan(
            tasks=(task,)
        ),
        ledger=FakeLedger(),  # type: ignore[arg-type]
        broker=CapabilityBroker(
            (
                capability(
                    "cap:quran",
                    agent_id="agent:quran",
                    discipline=(
                        ReligiousDiscipline.QURAN
                    ),
                ),
            )
        ),
        executor=QueueExecutor(
            [
                product(
                    task_id="claim",
                    agent_id="agent:quran",
                ),
            ]
        ),
        evaluator=QueueEvaluator(
            [
                EvidenceDecisionAction.RETRIEVE_MORE,
            ]
        ),  # type: ignore[arg-type]
    )

    outcome = coordinator.run()

    assert outcome.released_task_ids == ()

    assert outcome.unresolved_task_ids == (
        "claim",
    )


class RecordingDecisionService:
    def __init__(
        self,
        returned: object,
    ) -> None:
        self.returned = returned
        self.received = None

    def evaluate(
        self,
        *,
        retrieval_result: object,
        expert_case_id: str | None = None,
    ) -> object:
        assert expert_case_id is None

        self.received = (
            retrieval_result
        )

        return self.returned


def test_evidence_evaluator_uses_retrieval_not_raw_agent_evidence() -> None:
    retrieval = object()

    expected = SimpleNamespace(
        decision=EvidenceDecision(
            action=(
                EvidenceDecisionAction.ANSWER
            ),
            reasons=(),
        )
    )

    service = RecordingDecisionService(
        expected
    )

    evaluator = EvidenceDecisionEvaluator(
        service=service,  # type: ignore[arg-type]
    )

    product_value = AgentRunProduct(
        result=result(
            "claim",
            agent_id="agent:quran",
        ),
        retrieval_result=retrieval,  # type: ignore[arg-type]
    )

    actual = evaluator.evaluate(
        task=claim(
            "claim",
            discipline=(
                ReligiousDiscipline.QURAN
            ),
        ),
        product=product_value,
    )

    assert actual is expected

    assert service.received is retrieval


def test_coordinator_result_contains_no_authority_controls() -> None:
    names = {
        field.name
        for field in fields(
            CoordinatorRunResult
        )
    }

    forbidden = (
        "source",
        "authority",
        "book",
        "work",
        "url",
        "policy",
        "answer_text",
    )

    assert not any(
        token in name
        for name in names
        for token in forbidden
    )


def test_expert_escalation_is_withheld_not_unresolved() -> None:
    root = claim(
        "root:expert",
        discipline=ReligiousDiscipline.HADITH,
    )

    child = claim(
        "child:expert",
        discipline=ReligiousDiscipline.FIQH,
    )

    plan = ClaimGraphPlan(
        tasks=(
            root,
            child,
        ),
        dependencies=(
            ClaimDependency(
                prerequisite_task_id="root:expert",
                dependent_task_id="child:expert",
                reason="requires reviewed evidence",
            ),
        ),
    )

    broker = CapabilityBroker(
        (
            capability(
                "cap:hadith:expert",
                agent_id="agent:hadith",
                discipline=(
                    ReligiousDiscipline.HADITH
                ),
            ),
            capability(
                "cap:fiqh:expert",
                agent_id="agent:fiqh",
                discipline=(
                    ReligiousDiscipline.FIQH
                ),
            ),
        )
    )

    outcome = AgentCoordinator(
        plan=plan,
        ledger=FakeLedger(),  # type: ignore[arg-type]
        broker=broker,
        executor=QueueExecutor(
            [
                product(
                    task_id="root:expert",
                    agent_id="agent:hadith",
                ),
            ]
        ),
        evaluator=QueueEvaluator(
            [
                (
                    EvidenceDecisionAction
                    .ESCALATE_TO_EXPERT
                ),
            ]
        ),  # type: ignore[arg-type]
    ).run()

    assert outcome.executed_task_ids == (
        "root:expert",
    )

    assert outcome.released_task_ids == ()

    assert outcome.withheld_task_ids == (
        "root:expert",
    )

    assert outcome.blocked_task_ids == (
        "child:expert",
    )

    assert outcome.unresolved_task_ids == ()
