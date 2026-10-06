from __future__ import annotations

from basira.api.service import (
    build_default_retriever,
)
from basira.evidence.decision import (
    EvidenceDecisionAction,
)
from basira.evidence.models import (
    EvidenceDomain,
)
from basira.orchestration.capability_broker import (
    CapabilityBroker,
)
from basira.orchestration.capability_executor import (
    CapabilityRetrievalBinding,
    GovernedCapabilityExecutor,
)
from basira.orchestration.claim_graph import (
    ClaimGraphPlan,
    ExecutionBudget,
)
from basira.orchestration.contracts import (
    AgentCapability,
    ClaimTask,
)
from basira.orchestration.coordinator import (
    AgentCoordinator,
)
from basira.orchestration.execution_ledger import (
    ExecutionLedger,
)
from basira.reasoning.routing import (
    ReligiousReasoningRouter,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)

QUESTION = "ما نص الآية 2:255؟"

TASK_ID = "claim:quran:2:255"

CAPABILITY_ID = "cap:quran:canonical"


def main() -> None:
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            QUESTION
        )
    )

    route = (
        ReligiousReasoningRouter()
        .route(
            understanding
        )
    )

    task = ClaimTask(
        task_id=TASK_ID,
        claim_text=QUESTION,
        frame=route.frame,
        context_requirement=(
            route.context_requirement
        ),
        risk_tags=(
            understanding.risk_tags
        ),
    )

    capability = AgentCapability(
        capability_id=CAPABILITY_ID,
        agent_id="agent:quran",
        disciplines=frozenset(
            {
                route
                .frame
                .primary_discipline,
            }
        ),
    )

    plan = ClaimGraphPlan(
        tasks=(
            task,
        )
    )

    budget = ExecutionBudget(
        max_claims=1,
        max_depth=1,
        max_delegations=1,
        max_agents_per_claim=1,
        max_total_agent_runs=1,
    )

    ledger = ExecutionLedger(
        execution_id=(
            "smoke:agent-v1:quran"
        ),
        plan=plan,
        budget=budget,
    )

    retriever = (
        build_default_retriever()
    )

    executor = (
        GovernedCapabilityExecutor(
            retriever=retriever,
            bindings=(
                CapabilityRetrievalBinding(
                    capability_id=(
                        CAPABILITY_ID
                    ),
                    domains=frozenset(
                        {
                            EvidenceDomain
                            .QURAN,
                        }
                    ),
                ),
            ),
        )
    )

    coordinator = AgentCoordinator(
        plan=plan,
        ledger=ledger,
        broker=CapabilityBroker(
            (
                capability,
            )
        ),
        executor=executor,
    )

    result = coordinator.run()

    retrieval = (
        executor.latest_retrieval(
            TASK_ID
        )
    )

    if retrieval is None:
        raise RuntimeError(
            "executor produced no retrieval state"
        )

    decision = ledger.latest_decision(
        TASK_ID
    )

    if decision is None:
        raise RuntimeError(
            "coordinator recorded no "
            "evidence decision"
        )

    if (
        TASK_ID
        not in result.released_task_ids
    ):
        raise RuntimeError(
            "real governed claim was not released; "
            f"action={decision.action.value}"
        )

    if (
        decision.action
        not in {
            EvidenceDecisionAction.ANSWER,
            EvidenceDecisionAction
            .ANSWER_WITH_LIMITATION,
        }
    ):
        raise RuntimeError(
            "unexpected released decision: "
            f"{decision.action.value}"
        )

    quran_nodes = tuple(
        node
        for node
        in retrieval.evidence
        if (
            node.domain
            is EvidenceDomain.QURAN
        )
    )

    if not quran_nodes:
        raise RuntimeError(
            "no governed Quran evidence retrieved"
        )

    if (
        EvidenceDomain.QURAN
        in retrieval.unavailable_domains
    ):
        raise RuntimeError(
            "Quran domain marked unavailable"
        )

    print(
        "QUESTION =",
        QUESTION,
    )

    print(
        "DISCIPLINE =",
        route
        .frame
        .primary_discipline
        .value,
    )

    print(
        "ACTION =",
        decision.action.value,
    )

    print(
        "EXECUTED =",
        result.executed_task_ids,
    )

    print(
        "RELEASED =",
        result.released_task_ids,
    )

    print(
        "RETRIEVAL DOMAINS =",
        tuple(
            target.domain.value
            for target
            in retrieval.plan.targets
        ),
    )

    print(
        "EVIDENCE COUNT =",
        len(
            retrieval.evidence
        ),
    )

    print(
        "QURAN EVIDENCE IDS =",
        tuple(
            node.evidence_id
            for node
            in quran_nodes
        ),
    )

    print()
    print(
        "✅ REAL AGENT V1 CLAIM EXECUTED"
    )
    print(
        "✅ CAPABILITY NARROWED EXISTING PLAN"
    )
    print(
        "✅ GOVERNED UNIFIED RETRIEVER USED"
    )
    print(
        "✅ RAW AGENT EVIDENCE NOT TRUSTED"
    )
    print(
        "✅ EVIDENCE DECISION RECORDED BY LEDGER"
    )
    print(
        "✅ CLAIM RELEASED FROM TRUSTED ACTION"
    )


if __name__ == "__main__":
    main()
