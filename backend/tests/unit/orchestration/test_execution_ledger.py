from __future__ import annotations

from dataclasses import fields

import pytest

from basira.evidence.bundle import (
    EvidenceBundle,
)
from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionAction,
    EvidenceDecisionReason,
)
from basira.evidence.models import (
    ContextRequirement,
    EvidenceNeed,
)
from basira.evidence.service import (
    EvidenceDecisionOutcome,
)
from basira.orchestration.claim_graph import (
    ClaimGraphPlan,
    ExecutionBudget,
    ExecutionBudgetDimension,
    ExecutionBudgetExceeded,
)
from basira.orchestration.contracts import (
    AgentExecutionResult,
    AgentExecutionStatus,
    ClaimTask,
    DelegationRequest,
)
from basira.orchestration.execution_ledger import (
    AgentRunFinished,
    AgentRunLifecycle,
    AgentRunReserved,
    DelegationAccepted,
    EvidenceDecisionRecorded,
    ExecutionLedger,
    ExecutionLedgerEntry,
    ExecutionTransitionError,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)


def claim(
    task_id: str = "claim:1",
    text: str = "تحقق من الدعوى",
) -> ClaimTask:
    return ClaimTask(
        task_id=task_id,
        claim_text=text,
        frame=(
            ReligiousReasoningFrame(
                frame_id=(
                    f"reasoning:{task_id}"
                ),
                question=text,
                primary_discipline=(
                    ReligiousDiscipline
                    .AQIDAH
                ),
                reasoning_mode=(
                    ReasoningMode
                    .DIRECT_GROUNDING
                ),
            )
        ),
        context_requirement=(
            ContextRequirement()
        ),
    )


def plan(
    *tasks: ClaimTask,
) -> ClaimGraphPlan:
    return ClaimGraphPlan(
        tasks=(
            tasks
            or (
                claim(),
            )
        )
    )


def budget(
    *,
    max_claims: int = 8,
    max_depth: int = 4,
    max_delegations: int = 8,
    max_agents_per_claim: int = 3,
    max_total_agent_runs: int = 12,
) -> ExecutionBudget:
    return ExecutionBudget(
        max_claims=max_claims,
        max_depth=max_depth,
        max_delegations=(
            max_delegations
        ),
        max_agents_per_claim=(
            max_agents_per_claim
        ),
        max_total_agent_runs=(
            max_total_agent_runs
        ),
    )


def ledger(
    *,
    graph: ClaimGraphPlan | None = None,
    execution_budget: (
        ExecutionBudget | None
    ) = None,
) -> ExecutionLedger:
    return ExecutionLedger(
        execution_id="exec:test",
        plan=(
            graph
            or plan()
        ),
        budget=(
            execution_budget
            or budget()
        ),
    )


def delegation(
    delegation_id: str,
    *,
    task_id: str = "claim:1",
) -> DelegationRequest:
    return DelegationRequest(
        delegation_id=delegation_id,
        task_id=task_id,
        reason=(
            "Additional Tafsir capability "
            "is required."
        ),
        requested_evidence_needs=(
            frozenset(
                {
                    EvidenceNeed.TAFSIR,
                }
            )
        ),
    )


def result(
    *,
    task_id: str = "claim:1",
    agent_id: str = "agent:aqidah",
    delegations: tuple[
        DelegationRequest,
        ...,
    ] = (),
) -> AgentExecutionResult:
    return AgentExecutionResult(
        task_id=task_id,
        agent_id=agent_id,
        status=(
            AgentExecutionStatus
            .FINISHED
        ),
        delegations=delegations,
    )


def retrieve_more() -> EvidenceDecision:
    return EvidenceDecision(
        action=(
            EvidenceDecisionAction
            .RETRIEVE_MORE
        ),
        reasons=(
            EvidenceDecisionReason
            .MISSING_REQUIRED_EVIDENCE,
        ),
        unresolved_needs=(
            EvidenceNeed.TAFSIR,
        ),
    )


def answer() -> EvidenceDecision:
    return EvidenceDecision(
        action=(
            EvidenceDecisionAction
            .ANSWER
        ),
        reasons=(
            EvidenceDecisionReason
            .COMPLETE_EVIDENCE,
        ),
    )


def decision_outcome(
    decision: EvidenceDecision,
) -> EvidenceDecisionOutcome:
    """
    Typed test fixture for the ledger boundary.

    Production outcomes are created by
    EvidenceDecisionService.
    """

    return EvidenceDecisionOutcome(
        bundle=EvidenceBundle(
            evidence=(),
            required_assessments=(),
        ),
        decision=decision,
    )


def reserve_and_start(
    execution: ExecutionLedger,
    *,
    run_id: str = "run:1",
    agent_id: str = "agent:aqidah",
    delegation_id: str | None = None,
) -> None:
    execution.reserve_run(
        run_id=run_id,
        task_id="claim:1",
        agent_id=agent_id,
        capability_id=(
            "capability:aqidah"
        ),
        delegation_id=(
            delegation_id
        ),
    )

    execution.start_run(
        run_id
    )


def test_run_budget_is_reserved_before_execution() -> None:
    execution = ledger()

    entry = execution.reserve_run(
        run_id="run:1",
        task_id="claim:1",
        agent_id="agent:aqidah",
        capability_id=(
            "capability:aqidah"
        ),
    )

    assert isinstance(
        entry.event,
        AgentRunReserved,
    )

    assert (
        execution
        .reserved_run_count()
        == 1
    )

    assert (
        execution.run_lifecycle(
            "run:1"
        )
        is AgentRunLifecycle.RESERVED
    )


def test_event_log_is_ordered_and_append_only_projection() -> None:
    execution = ledger()

    reserve_and_start(
        execution
    )

    execution.finish_run(
        run_id="run:1",
        result=result(),
    )

    entries = execution.entries

    assert tuple(
        entry.sequence
        for entry
        in entries
    ) == (
        1,
        2,
        3,
    )

    assert tuple(
        entry.event_id
        for entry
        in entries
    ) == (
        "exec:test:event:1",
        "exec:test:event:2",
        "exec:test:event:3",
    )

    assert isinstance(
        entries[
            -1
        ].event,
        AgentRunFinished,
    )


def test_finished_agent_run_does_not_resolve_claim() -> None:
    execution = ledger()

    reserve_and_start(
        execution
    )

    execution.finish_run(
        run_id="run:1",
        result=result(),
    )

    assert (
        execution.run_lifecycle(
            "run:1"
        )
        is AgentRunLifecycle.FINISHED
    )

    assert (
        execution.latest_decision(
            "claim:1"
        )
        is None
    )

    assert (
        execution.autonomously_terminal(
            "claim:1"
        )
        is False
    )


def test_run_result_must_match_reserved_task_and_agent() -> None:
    execution = ledger()

    reserve_and_start(
        execution
    )

    with pytest.raises(
        ExecutionTransitionError,
        match=(
            "task_id does not match"
        ),
    ):
        execution.finish_run(
            run_id="run:1",
            result=result(
                task_id="claim:other"
            ),
        )

    with pytest.raises(
        ExecutionTransitionError,
        match=(
            "agent_id does not match"
        ),
    ):
        execution.finish_run(
            run_id="run:1",
            result=result(
                agent_id="agent:other"
            ),
        )


def test_duplicate_active_agent_run_for_claim_is_blocked() -> None:
    execution = ledger()

    execution.reserve_run(
        run_id="run:1",
        task_id="claim:1",
        agent_id="agent:aqidah",
        capability_id="cap:1",
    )

    with pytest.raises(
        ExecutionTransitionError,
        match=(
            "active run for claim"
        ),
    ):
        execution.reserve_run(
            run_id="run:2",
            task_id="claim:1",
            agent_id=(
                "agent:aqidah"
            ),
            capability_id="cap:1",
        )


def test_same_agent_can_run_again_after_previous_run_finishes() -> None:
    execution = ledger()

    reserve_and_start(
        execution
    )

    execution.finish_run(
        run_id="run:1",
        result=result(),
    )

    execution.reserve_run(
        run_id="run:2",
        task_id="claim:1",
        agent_id="agent:aqidah",
        capability_id="cap:1",
    )

    assert (
        execution
        .reserved_run_count()
        == 2
    )


def test_total_agent_run_budget_fails_at_reservation() -> None:
    execution = ledger(
        execution_budget=budget(
            max_total_agent_runs=1
        )
    )

    reserve_and_start(
        execution
    )

    execution.finish_run(
        run_id="run:1",
        result=result(),
    )

    with pytest.raises(
        ExecutionBudgetExceeded
    ) as captured:
        execution.reserve_run(
            run_id="run:2",
            task_id="claim:1",
            agent_id=(
                "agent:aqidah"
            ),
            capability_id="cap:1",
        )

    assert (
        captured
        .value
        .violation
        .dimension
        is ExecutionBudgetDimension
        .TOTAL_AGENT_RUNS
    )


def test_distinct_agent_fanout_budget_is_enforced() -> None:
    execution = ledger(
        execution_budget=budget(
            max_agents_per_claim=1
        )
    )

    reserve_and_start(
        execution,
        agent_id="agent:first",
    )

    execution.finish_run(
        run_id="run:1",
        result=result(
            agent_id="agent:first"
        ),
    )

    with pytest.raises(
        ExecutionBudgetExceeded
    ) as captured:
        execution.reserve_run(
            run_id="run:2",
            task_id="claim:1",
            agent_id="agent:second",
            capability_id="cap:2",
        )

    assert (
        captured
        .value
        .violation
        .dimension
        is ExecutionBudgetDimension
        .AGENTS_PER_CLAIM
    )


def test_delegation_request_does_not_consume_budget_until_accepted() -> None:
    execution = ledger(
        execution_budget=budget(
            max_delegations=1
        )
    )

    reserve_and_start(
        execution
    )

    request = delegation(
        "delegation:1"
    )

    execution.finish_run(
        run_id="run:1",
        result=result(
            delegations=(
                request,
            )
        ),
    )

    assert (
        execution
        .accepted_delegation_count()
        == 0
    )

    entry = (
        execution
        .accept_delegation(
            "delegation:1"
        )
    )

    assert isinstance(
        entry.event,
        DelegationAccepted,
    )

    assert (
        execution
        .accepted_delegation_count()
        == 1
    )


def test_delegation_budget_is_enforced_on_acceptance() -> None:
    execution = ledger(
        execution_budget=budget(
            max_delegations=1
        )
    )

    reserve_and_start(
        execution
    )

    execution.finish_run(
        run_id="run:1",
        result=result(
            delegations=(
                delegation(
                    "delegation:1"
                ),
                delegation(
                    "delegation:2"
                ),
            )
        ),
    )

    execution.accept_delegation(
        "delegation:1"
    )

    with pytest.raises(
        ExecutionBudgetExceeded
    ) as captured:
        execution.accept_delegation(
            "delegation:2"
        )

    assert (
        captured
        .value
        .violation
        .dimension
        is ExecutionBudgetDimension
        .DELEGATIONS
    )


def test_accepted_delegation_can_be_consumed_by_one_run_only() -> None:
    execution = ledger()

    reserve_and_start(
        execution
    )

    execution.finish_run(
        run_id="run:1",
        result=result(
            delegations=(
                delegation(
                    "delegation:1"
                ),
            )
        ),
    )

    execution.accept_delegation(
        "delegation:1"
    )

    execution.reserve_run(
        run_id="run:2",
        task_id="claim:1",
        agent_id="agent:tafsir",
        capability_id="cap:tafsir",
        delegation_id=(
            "delegation:1"
        ),
    )

    with pytest.raises(
        ExecutionTransitionError,
        match=(
            "already consumed"
        ),
    ):
        execution.reserve_run(
            run_id="run:3",
            task_id="claim:1",
            agent_id="agent:other",
            capability_id="cap:other",
            delegation_id=(
                "delegation:1"
            ),
        )


def test_unaccepted_delegation_cannot_start_downstream_run() -> None:
    execution = ledger()

    reserve_and_start(
        execution
    )

    execution.finish_run(
        run_id="run:1",
        result=result(
            delegations=(
                delegation(
                    "delegation:1"
                ),
            )
        ),
    )

    with pytest.raises(
        ExecutionTransitionError,
        match=(
            "must be accepted"
        ),
    ):
        execution.reserve_run(
            run_id="run:2",
            task_id="claim:1",
            agent_id="agent:tafsir",
            capability_id="cap:tafsir",
            delegation_id=(
                "delegation:1"
            ),
        )


def test_retrieve_more_decision_keeps_autonomous_loop_open() -> None:
    execution = ledger()

    entry = (
        execution
        .record_evidence_outcome(
            task_id="claim:1",
            outcome=(
                decision_outcome(
                    retrieve_more()
                )
            ),
        )
    )

    assert isinstance(
        entry.event,
        EvidenceDecisionRecorded,
    )

    assert (
        execution.autonomously_terminal(
            "claim:1"
        )
        is False
    )

    execution.reserve_run(
        run_id="run:next",
        task_id="claim:1",
        agent_id="agent:tafsir",
        capability_id="cap:tafsir",
    )


@pytest.mark.parametrize(
    "decision",
    [
        answer(),
        EvidenceDecision(
            action=(
                EvidenceDecisionAction
                .ANSWER_WITH_LIMITATION
            ),
            reasons=(
                EvidenceDecisionReason
                .RESOLVED_ABSENCE,
            ),
        ),
        EvidenceDecision(
            action=(
                EvidenceDecisionAction
                .ABSTAIN
            ),
            reasons=(
                EvidenceDecisionReason
                .UNAVAILABLE_REQUIRED_DOMAIN,
            ),
        ),
        EvidenceDecision(
            action=(
                EvidenceDecisionAction
                .ESCALATE_TO_EXPERT
            ),
            reasons=(
                EvidenceDecisionReason
                .HIGH_RISK_QUERY,
            ),
        ),
    ],
)
def test_non_retrieve_more_decisions_stop_autonomous_work(
    decision: EvidenceDecision,
) -> None:
    execution = ledger()

    execution.record_evidence_outcome(
        task_id="claim:1",
        outcome=(
            decision_outcome(
                decision
            )
        ),
    )

    assert (
        execution.autonomously_terminal(
            "claim:1"
        )
        is True
    )

    with pytest.raises(
        ExecutionTransitionError,
        match=(
            "terminal for autonomous"
        ),
    ):
        execution.reserve_run(
            run_id="run:1",
            task_id="claim:1",
            agent_id="agent:aqidah",
            capability_id="cap:1",
        )


def test_terminal_decision_cannot_be_overwritten() -> None:
    execution = ledger()

    execution.record_evidence_outcome(
        task_id="claim:1",
        outcome=(
            decision_outcome(
                answer()
            )
        ),
    )

    with pytest.raises(
        ExecutionTransitionError,
        match=(
            "terminal autonomous "
            "evidence decision"
        ),
    ):
        execution.record_evidence_outcome(
            task_id="claim:1",
            outcome=(
            decision_outcome(
                answer()
            )
        ),
        )


def test_decision_cannot_be_recorded_while_run_active() -> None:
    execution = ledger()

    execution.reserve_run(
        run_id="run:1",
        task_id="claim:1",
        agent_id="agent:aqidah",
        capability_id="cap:1",
    )

    with pytest.raises(
        ExecutionTransitionError,
        match=(
            "active runs"
        ),
    ):
        execution.record_evidence_outcome(
            task_id="claim:1",
            outcome=(
            decision_outcome(
                answer()
            )
        ),
        )


def test_agent_failure_and_cancellation_are_execution_facts_only() -> None:
    failed = ledger()

    reserve_and_start(
        failed
    )

    failed.fail_run(
        run_id="run:1",
        failure_code="provider_timeout",
    )

    assert (
        failed.run_lifecycle(
            "run:1"
        )
        is AgentRunLifecycle.FAILED
    )

    assert (
        failed.latest_decision(
            "claim:1"
        )
        is None
    )

    cancelled = ledger()

    cancelled.reserve_run(
        run_id="run:1",
        task_id="claim:1",
        agent_id="agent:aqidah",
        capability_id="cap:1",
    )

    cancelled.cancel_run(
        run_id="run:1",
        reason="scheduler_cancelled",
    )

    assert (
        cancelled.run_lifecycle(
            "run:1"
        )
        is AgentRunLifecycle.CANCELLED
    )

    assert (
        cancelled.latest_decision(
            "claim:1"
        )
        is None
    )


def test_duplicate_delegation_ids_across_runs_fail_closed() -> None:
    execution = ledger()

    reserve_and_start(
        execution,
        run_id="run:1",
        agent_id="agent:first",
    )

    execution.finish_run(
        run_id="run:1",
        result=result(
            agent_id="agent:first",
            delegations=(
                delegation(
                    "delegation:same"
                ),
            ),
        ),
    )

    reserve_and_start(
        execution,
        run_id="run:2",
        agent_id="agent:second",
    )

    with pytest.raises(
        ExecutionTransitionError,
        match=(
            "unique across execution"
        ),
    ):
        execution.finish_run(
            run_id="run:2",
            result=result(
                agent_id="agent:second",
                delegations=(
                    delegation(
                        "delegation:same"
                    ),
                ),
            ),
        )


def test_ledger_does_not_contain_authority_or_answer_controls() -> None:
    names = {
        item.name
        for item in fields(
            ExecutionLedgerEntry
        )
    }

    for forbidden in (
        "authority",
        "authority_level",
        "authority_scope",
        "runtime_use",
        "answer",
        "final_answer",
    ):
        assert (
            forbidden
            not in names
        )


def test_ledger_recording_api_cannot_accept_manual_evidence_ids() -> None:
    from inspect import signature

    parameters = signature(
        ExecutionLedger
        .record_evidence_outcome
    ).parameters

    assert "outcome" in parameters

    assert "decision" not in parameters

    assert "evidence" not in parameters

    assert "evidence_ids" not in parameters


def test_agent_result_cannot_create_evidence_decision() -> None:
    execution = ledger()

    reserve_and_start(
        execution
    )

    execution.finish_run(
        run_id="run:1",
        result=result(),
    )

    # Agent completion is only an execution fact.
    assert (
        execution.latest_decision(
            "claim:1"
        )
        is None
    )

    assert (
        execution.decision_history(
            "claim:1"
        )
        == ()
    )
