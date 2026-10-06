from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum

from basira.orchestration.contracts import (
    ClaimTask,
)


def _normalized_text(
    value: str,
) -> str:
    return " ".join(
        value.split()
    )


def _claim_semantic_key(
    task: ClaimTask,
) -> tuple[object, ...]:
    """
    Deterministic semantic identity for orchestration
    deduplication.

    task_id is intentionally excluded. Two differently
    named tasks with the same semantic work contract
    should be represented once in the DAG and shared by
    all dependents.
    """

    frame = task.frame

    return (
        _normalized_text(
            task.claim_text
        ),
        frame.primary_discipline.value,
        tuple(
            sorted(
                discipline.value
                for discipline
                in frame.secondary_disciplines
            )
        ),
        frame.reasoning_mode.value,
        tuple(
            sorted(
                obligation.value
                for obligation
                in frame.obligations
            )
        ),
        tuple(
            sorted(
                constraint.value
                for constraint
                in frame.constraints
            )
        ),
        tuple(
            sorted(
                need.value
                for need
                in task
                .context_requirement
                .required
            )
        ),
        tuple(
            sorted(
                need.value
                for need
                in task
                .context_requirement
                .optional
            )
        ),
        tuple(
            sorted(
                risk.value
                for risk
                in task.risk_tags
            )
        ),
        tuple(
            sorted(
                task.context_ids
            )
        ),
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ClaimDependency:
    """
    One blocking epistemic dependency.

    prerequisite_task_id must be resolved before the
    dependent task becomes schedulable.

    Delegation is deliberately not represented here.
    Delegation is an execution event, while this edge is
    part of the stable claim structure.
    """

    prerequisite_task_id: str

    dependent_task_id: str

    reason: str

    def __post_init__(
        self,
    ) -> None:
        if not (
            self.prerequisite_task_id.strip()
        ):
            raise ValueError(
                "prerequisite_task_id "
                "must not be blank"
            )

        if not (
            self.dependent_task_id.strip()
        ):
            raise ValueError(
                "dependent_task_id "
                "must not be blank"
            )

        if (
            self.prerequisite_task_id
            == self.dependent_task_id
        ):
            raise ValueError(
                "claim dependency cannot "
                "reference itself"
            )

        if not self.reason.strip():
            raise ValueError(
                "claim dependency reason "
                "must not be blank"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ClaimGraphPlan:
    """
    Deterministic claim DAG.

    The graph owns topology. ClaimTask remains a
    topology-free semantic work unit.

    Multiple dependent claims may point to the same
    prerequisite task. This is the canonical mechanism
    for shared subclaims and prevents duplicate agent
    work.
    """

    tasks: tuple[
        ClaimTask,
        ...,
    ]

    dependencies: tuple[
        ClaimDependency,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not self.tasks:
            raise ValueError(
                "claim graph requires "
                "at least one task"
            )

        task_ids = [
            task.task_id
            for task
            in self.tasks
        ]

        if (
            len(
                set(
                    task_ids
                )
            )
            != len(
                task_ids
            )
        ):
            raise ValueError(
                "claim graph task ids "
                "must be unique"
            )

        semantic_keys: dict[
            tuple[object, ...],
            str,
        ] = {}

        for task in self.tasks:
            key = _claim_semantic_key(
                task
            )

            existing = (
                semantic_keys.get(
                    key
                )
            )

            if existing is not None:
                raise ValueError(
                    "semantic duplicate claim tasks "
                    "must share one DAG node: "
                    f"{existing}, {task.task_id}"
                )

            semantic_keys[
                key
            ] = task.task_id

        known = set(
            task_ids
        )

        dependency_pairs: set[
            tuple[
                str,
                str,
            ]
        ] = set()

        for dependency in (
            self.dependencies
        ):
            if (
                dependency
                .prerequisite_task_id
                not in known
            ):
                raise ValueError(
                    "claim dependency references "
                    "unknown prerequisite task: "
                    f"{dependency.prerequisite_task_id}"
                )

            if (
                dependency
                .dependent_task_id
                not in known
            ):
                raise ValueError(
                    "claim dependency references "
                    "unknown dependent task: "
                    f"{dependency.dependent_task_id}"
                )

            pair = (
                dependency
                .prerequisite_task_id,
                dependency
                .dependent_task_id,
            )

            if pair in dependency_pairs:
                raise ValueError(
                    "claim graph contains "
                    "duplicate dependency: "
                    f"{pair[0]} -> {pair[1]}"
                )

            dependency_pairs.add(
                pair
            )

        # Construction itself is fail-closed.
        # A cyclic plan can never exist as a valid
        # ClaimGraphPlan instance.
        self.topological_order()

    @property
    def task_ids(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            task.task_id
            for task
            in self.tasks
        )

    def task(
        self,
        task_id: str,
    ) -> ClaimTask:
        for task in self.tasks:
            if task.task_id == task_id:
                return task

        raise KeyError(
            task_id
        )

    def prerequisites(
        self,
        task_id: str,
    ) -> tuple[
        str,
        ...,
    ]:
        self.task(
            task_id
        )

        return tuple(
            dependency
            .prerequisite_task_id
            for dependency
            in self.dependencies
            if (
                dependency
                .dependent_task_id
                == task_id
            )
        )

    def dependents(
        self,
        task_id: str,
    ) -> tuple[
        str,
        ...,
    ]:
        self.task(
            task_id
        )

        return tuple(
            dependency
            .dependent_task_id
            for dependency
            in self.dependencies
            if (
                dependency
                .prerequisite_task_id
                == task_id
            )
        )

    def topological_order(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Deterministic Kahn topological ordering.

        Original task declaration order is used as the
        stable tie-breaker between simultaneously ready
        tasks.
        """

        task_ids = self.task_ids

        indegree = {
            task_id: 0
            for task_id
            in task_ids
        }

        downstream: dict[
            str,
            list[
                str
            ],
        ] = {
            task_id: []
            for task_id
            in task_ids
        }

        for dependency in (
            self.dependencies
        ):
            prerequisite = (
                dependency
                .prerequisite_task_id
            )

            dependent = (
                dependency
                .dependent_task_id
            )

            indegree[
                dependent
            ] += 1

            downstream[
                prerequisite
            ].append(
                dependent
            )

        declared_index = {
            task_id: index
            for index, task_id
            in enumerate(
                task_ids
            )
        }

        ready = deque(
            task_id
            for task_id
            in task_ids
            if indegree[
                task_id
            ] == 0
        )

        ordered: list[
            str
        ] = []

        while ready:
            task_id = (
                ready.popleft()
            )

            ordered.append(
                task_id
            )

            newly_ready: list[
                str
            ] = []

            for dependent in (
                downstream[
                    task_id
                ]
            ):
                indegree[
                    dependent
                ] -= 1

                if (
                    indegree[
                        dependent
                    ]
                    == 0
                ):
                    newly_ready.append(
                        dependent
                    )

            for dependent in sorted(
                newly_ready,
                key=(
                    declared_index
                    .__getitem__
                ),
            ):
                ready.append(
                    dependent
                )

        if len(
            ordered
        ) != len(
            task_ids
        ):
            raise ValueError(
                "claim graph must be acyclic"
            )

        return tuple(
            ordered
        )

    def depth_by_task_id(
        self,
    ) -> dict[
        str,
        int,
    ]:
        """
        Compute depth from graph topology.

        Tasks without prerequisites have depth zero.
        Depth is never stored inside ClaimTask.
        """

        depths = {
            task_id: 0
            for task_id
            in self.task_ids
        }

        for task_id in (
            self.topological_order()
        ):
            for dependent in (
                self.dependents(
                    task_id
                )
            ):
                depths[
                    dependent
                ] = max(
                    depths[
                        dependent
                    ],
                    depths[
                        task_id
                    ] + 1,
                )

        return depths

    @property
    def max_depth(
        self,
    ) -> int:
        return max(
            self
            .depth_by_task_id()
            .values()
        )

    @property
    def root_task_ids(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Tasks with no epistemic prerequisites.

        This is pure graph topology. Whether a task is
        runnable belongs to the future execution ledger
        and scheduler, not to ClaimGraphPlan.
        """

        return tuple(
            task_id
            for task_id
            in self.task_ids
            if not self.prerequisites(
                task_id
            )
        )


class ExecutionBudgetDimension(
    StrEnum
):
    CLAIMS = "claims"

    DEPTH = "depth"

    DELEGATIONS = "delegations"

    AGENTS_PER_CLAIM = (
        "agents_per_claim"
    )

    TOTAL_AGENT_RUNS = (
        "total_agent_runs"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionBudgetViolation:
    dimension: ExecutionBudgetDimension

    observed: int

    limit: int


class ExecutionBudgetExceeded(
    RuntimeError
):
    """
    Deterministic structural/runtime budget violation.

    v1 validates claim-count and DAG-depth limits.
    Delegation and agent-run counters are enforced by
    the future execution ledger.
    """

    def __init__(
        self,
        violation: (
            ExecutionBudgetViolation
        ),
    ) -> None:
        self.violation = violation

        super().__init__(
            "execution budget exceeded: "
            f"{violation.dimension.value} "
            f"observed={violation.observed} "
            f"limit={violation.limit}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionBudget:
    """
    Execution-wide deterministic bounds.

    Budgets belong to orchestration, never to an Agent.

    No field grants source access, religious authority,
    or permission to bypass existing trust policy.
    """

    max_claims: int

    max_depth: int

    max_delegations: int

    max_agents_per_claim: int

    max_total_agent_runs: int

    def __post_init__(
        self,
    ) -> None:
        if self.max_claims < 1:
            raise ValueError(
                "max_claims must be at least 1"
            )

        if self.max_depth < 0:
            raise ValueError(
                "max_depth must not be negative"
            )

        if self.max_delegations < 0:
            raise ValueError(
                "max_delegations must not "
                "be negative"
            )

        if (
            self.max_agents_per_claim
            < 1
        ):
            raise ValueError(
                "max_agents_per_claim must "
                "be at least 1"
            )

        if (
            self.max_total_agent_runs
            < 1
        ):
            raise ValueError(
                "max_total_agent_runs must "
                "be at least 1"
            )

    def require_plan(
        self,
        plan: ClaimGraphPlan,
    ) -> None:
        claim_count = len(
            plan.tasks
        )

        if (
            claim_count
            > self.max_claims
        ):
            raise (
                ExecutionBudgetExceeded(
                    ExecutionBudgetViolation(
                        dimension=(
                            ExecutionBudgetDimension
                            .CLAIMS
                        ),
                        observed=claim_count,
                        limit=self.max_claims,
                    )
                )
            )

        if (
            plan.max_depth
            > self.max_depth
        ):
            raise (
                ExecutionBudgetExceeded(
                    ExecutionBudgetViolation(
                        dimension=(
                            ExecutionBudgetDimension
                            .DEPTH
                        ),
                        observed=(
                            plan.max_depth
                        ),
                        limit=self.max_depth,
                    )
                )
            )
