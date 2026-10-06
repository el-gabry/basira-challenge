from __future__ import annotations

from dataclasses import fields

import pytest

from basira.evidence.models import (
    ContextRequirement,
)
from basira.orchestration.claim_graph import (
    ClaimDependency,
    ClaimGraphPlan,
    ExecutionBudget,
    ExecutionBudgetDimension,
    ExecutionBudgetExceeded,
)
from basira.orchestration.contracts import (
    ClaimTask,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)


def task(
    task_id: str,
    text: str,
    *,
    discipline: (
        ReligiousDiscipline
    ) = ReligiousDiscipline.AQIDAH,
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
                    discipline
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


def dependency(
    prerequisite: str,
    dependent: str,
) -> ClaimDependency:
    return ClaimDependency(
        prerequisite_task_id=(
            prerequisite
        ),
        dependent_task_id=(
            dependent
        ),
        reason=(
            f"{dependent} requires "
            f"{prerequisite}"
        ),
    )


def diamond_plan() -> ClaimGraphPlan:
    shared = task(
        "claim:shared",
        "تحقق من الدليل الأصلي",
    )

    left = task(
        "claim:left",
        "حلل الدعوى الأولى",
    )

    right = task(
        "claim:right",
        "حلل الدعوى الثانية",
    )

    final = task(
        "claim:final",
        "ركب النتيجة المشتركة",
    )

    return ClaimGraphPlan(
        tasks=(
            final,
            right,
            left,
            shared,
        ),
        dependencies=(
            dependency(
                "claim:shared",
                "claim:left",
            ),
            dependency(
                "claim:shared",
                "claim:right",
            ),
            dependency(
                "claim:left",
                "claim:final",
            ),
            dependency(
                "claim:right",
                "claim:final",
            ),
        ),
    )


def test_claim_graph_supports_shared_subclaim_dag() -> None:
    plan = diamond_plan()

    assert (
        plan.dependents(
            "claim:shared"
        )
        == (
            "claim:left",
            "claim:right",
        )
    )

    assert set(
        plan.prerequisites(
            "claim:final"
        )
    ) == {
        "claim:left",
        "claim:right",
    }

    assert (
        plan.max_depth
        == 2
    )


def test_topological_order_is_deterministic() -> None:
    plan = diamond_plan()

    assert (
        plan.topological_order()
        == (
            "claim:shared",
            "claim:right",
            "claim:left",
            "claim:final",
        )
    )


def test_root_tasks_are_topology_only() -> None:
    plan = diamond_plan()

    assert (
        plan.root_task_ids
        == (
            "claim:shared",
        )
    )


def test_claim_graph_does_not_own_execution_readiness() -> None:
    assert not hasattr(
        ClaimGraphPlan,
        "ready_task_ids",
    )



def test_claim_graph_rejects_cycle() -> None:
    first = task(
        "claim:a",
        "الدعوى الأولى",
    )

    second = task(
        "claim:b",
        "الدعوى الثانية",
    )

    with pytest.raises(
        ValueError,
        match=(
            "claim graph must be acyclic"
        ),
    ):
        ClaimGraphPlan(
            tasks=(
                first,
                second,
            ),
            dependencies=(
                dependency(
                    "claim:a",
                    "claim:b",
                ),
                dependency(
                    "claim:b",
                    "claim:a",
                ),
            ),
        )


def test_dependency_rejects_self_edge() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "cannot reference itself"
        ),
    ):
        dependency(
            "claim:a",
            "claim:a",
        )


def test_claim_graph_rejects_unknown_dependency_endpoint() -> None:
    only = task(
        "claim:a",
        "دعوى",
    )

    with pytest.raises(
        ValueError,
        match=(
            "unknown prerequisite task"
        ),
    ):
        ClaimGraphPlan(
            tasks=(
                only,
            ),
            dependencies=(
                dependency(
                    "claim:missing",
                    "claim:a",
                ),
            ),
        )


def test_claim_graph_rejects_duplicate_task_ids() -> None:
    first = task(
        "claim:same",
        "دعوى أولى",
    )

    second = task(
        "claim:same",
        "دعوى ثانية",
    )

    with pytest.raises(
        ValueError,
        match=(
            "task ids must be unique"
        ),
    ):
        ClaimGraphPlan(
            tasks=(
                first,
                second,
            )
        )


def test_claim_graph_rejects_semantic_duplicate_tasks() -> None:
    first = task(
        "claim:a",
        "نفس الدعوى",
    )

    second = task(
        "claim:b",
        "  نفس   الدعوى  ",
    )

    with pytest.raises(
        ValueError,
        match=(
            "semantic duplicate claim tasks "
            "must share one DAG node"
        ),
    ):
        ClaimGraphPlan(
            tasks=(
                first,
                second,
            )
        )


def test_same_text_with_different_discipline_is_not_duplicate() -> None:
    aqidah = task(
        "claim:aqidah",
        "حلل هذه المسألة",
        discipline=(
            ReligiousDiscipline.AQIDAH
        ),
    )

    hadith = task(
        "claim:hadith",
        "حلل هذه المسألة",
        discipline=(
            ReligiousDiscipline.HADITH
        ),
    )

    plan = ClaimGraphPlan(
        tasks=(
            aqidah,
            hadith,
        )
    )

    assert len(
        plan.tasks
    ) == 2


def test_claim_graph_rejects_duplicate_dependency_pair() -> None:
    first = task(
        "claim:a",
        "أ",
    )

    second = task(
        "claim:b",
        "ب",
    )

    with pytest.raises(
        ValueError,
        match=(
            "duplicate dependency"
        ),
    ):
        ClaimGraphPlan(
            tasks=(
                first,
                second,
            ),
            dependencies=(
                ClaimDependency(
                    prerequisite_task_id=(
                        "claim:a"
                    ),
                    dependent_task_id=(
                        "claim:b"
                    ),
                    reason="سبب أول",
                ),
                ClaimDependency(
                    prerequisite_task_id=(
                        "claim:a"
                    ),
                    dependent_task_id=(
                        "claim:b"
                    ),
                    reason="سبب ثان",
                ),
            ),
        )


def test_depth_is_computed_not_stored_on_task() -> None:
    plan = diamond_plan()

    depths = (
        plan.depth_by_task_id()
    )

    assert depths[
        "claim:shared"
    ] == 0

    assert depths[
        "claim:left"
    ] == 1

    assert depths[
        "claim:right"
    ] == 1

    assert depths[
        "claim:final"
    ] == 2

    task_fields = {
        item.name
        for item in fields(
            ClaimTask
        )
    }

    assert (
        "depth"
        not in task_fields
    )


def budget(
    *,
    max_claims: int = 8,
    max_depth: int = 4,
) -> ExecutionBudget:
    return ExecutionBudget(
        max_claims=max_claims,
        max_depth=max_depth,
        max_delegations=16,
        max_agents_per_claim=3,
        max_total_agent_runs=24,
    )


def test_execution_budget_accepts_diamond_plan() -> None:
    budget().require_plan(
        diamond_plan()
    )


def test_execution_budget_rejects_claim_explosion() -> None:
    plan = diamond_plan()

    with pytest.raises(
        ExecutionBudgetExceeded
    ) as captured:
        budget(
            max_claims=3
        ).require_plan(
            plan
        )

    assert (
        captured
        .value
        .violation
        .dimension
        is ExecutionBudgetDimension.CLAIMS
    )

    assert (
        captured
        .value
        .violation
        .observed
        == 4
    )

    assert (
        captured
        .value
        .violation
        .limit
        == 3
    )


def test_execution_budget_rejects_excessive_depth() -> None:
    plan = diamond_plan()

    with pytest.raises(
        ExecutionBudgetExceeded
    ) as captured:
        budget(
            max_depth=1
        ).require_plan(
            plan
        )

    assert (
        captured
        .value
        .violation
        .dimension
        is ExecutionBudgetDimension.DEPTH
    )

    assert (
        captured
        .value
        .violation
        .observed
        == 2
    )


@pytest.mark.parametrize(
    (
        "field_name",
        "value",
        "message",
    ),
    [
        (
            "max_claims",
            0,
            "max_claims must be at least 1",
        ),
        (
            "max_depth",
            -1,
            "max_depth must not be negative",
        ),
        (
            "max_delegations",
            -1,
            "max_delegations must not be negative",
        ),
        (
            "max_agents_per_claim",
            0,
            "max_agents_per_claim must be at least 1",
        ),
        (
            "max_total_agent_runs",
            0,
            "max_total_agent_runs must be at least 1",
        ),
    ],
)
def test_execution_budget_rejects_invalid_limits(
    field_name: str,
    value: int,
    message: str,
) -> None:
    values = {
        "max_claims": 8,
        "max_depth": 4,
        "max_delegations": 16,
        "max_agents_per_claim": 3,
        "max_total_agent_runs": 24,
    }

    values[
        field_name
    ] = value

    with pytest.raises(
        ValueError,
        match=message,
    ):
        ExecutionBudget(
            **values
        )


def test_execution_budget_cannot_grant_authority_or_source_access() -> None:
    names = {
        item.name
        for item in fields(
            ExecutionBudget
        )
    }

    for forbidden in (
        "authority",
        "authority_level",
        "authority_scope",
        "source_id",
        "source_ids",
        "runtime_use",
        "agent_id",
    ):
        assert (
            forbidden
            not in names
        )
