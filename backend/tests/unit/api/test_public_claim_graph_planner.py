from types import SimpleNamespace
from typing import cast

from basira.api.claim_graph_planner import (
    PublicClaimGraphPlanner,
)
from basira.orchestration.contracts import (
    ClaimTask,
)


def _task_factory():
    sequence = 0

    def build(
        claim_text: str,
    ) -> ClaimTask:
        nonlocal sequence

        sequence += 1

        # ClaimGraphPlan needs the semantic work fields
        # only. Routing itself is tested separately and
        # will be supplied by the public runtime wiring.
        frame = SimpleNamespace(
            primary_discipline=(
                SimpleNamespace(
                    value="test-discipline"
                )
            ),
            secondary_disciplines=frozenset(),
            reasoning_mode=(
                SimpleNamespace(
                    value="test-mode"
                )
            ),
            obligations=frozenset(),
            constraints=frozenset(),
        )

        context_requirement = (
            SimpleNamespace(
                required=frozenset(),
                optional=frozenset(),
            )
        )

        return cast(
            ClaimTask,
            SimpleNamespace(
                task_id=f"claim-{sequence}",
                claim_text=claim_text,
                frame=frame,
                context_requirement=(
                    context_requirement
                ),
                risk_tags=frozenset(),
                context_ids=(),
            ),
        )

    return build


def test_simple_question_remains_single_claim() -> None:
    plan = PublicClaimGraphPlanner().plan(
        question=(
            "ما معنى الكرسي في "
            "وسع كرسيه السماوات والأرض؟"
        ),
        task_factory=_task_factory(),
    )

    assert len(plan.tasks) == 1
    assert plan.dependencies == ()

    assert plan.tasks[0].claim_text == (
        "ما معنى الكرسي في "
        "وسع كرسيه السماوات والأرض"
    )


def test_quran_hadith_question_becomes_parallel_claims() -> None:
    plan = PublicClaimGraphPlanner().plan(
        question=(
            "القرآن أمر بالوضوء، "
            "فهل ورد حديث صحيح في فضله؟"
        ),
        task_factory=_task_factory(),
    )

    assert tuple(
        task.claim_text
        for task in plan.tasks
    ) == (
        "القرآن أمر بالوضوء",
        "فهل ورد حديث صحيح في فضله",
    )

    # These are separate authority obligations.
    # The Hadith claim does not epistemically depend
    # on proving the Quran claim first.
    assert plan.dependencies == ()


def test_explicit_legal_followup_creates_dependency() -> None:
    plan = PublicClaimGraphPlanner().plan(
        question=(
            "هل ثبت أن النبي قال كذا يوم بدر؟ "
            "وما أثره في الحكم؟"
        ),
        task_factory=_task_factory(),
    )

    assert len(plan.tasks) == 2
    assert len(plan.dependencies) == 1

    dependency = plan.dependencies[0]

    assert (
        dependency.prerequisite_task_id
        == plan.tasks[0].task_id
    )

    assert (
        dependency.dependent_task_id
        == plan.tasks[1].task_id
    )


def test_ordinary_comma_does_not_force_decomposition() -> None:
    plan = PublicClaimGraphPlanner().plan(
        question=(
            "ما معنى الكرسي، وما المقصود "
            "به في هذا السياق؟"
        ),
        task_factory=_task_factory(),
    )

    assert len(plan.tasks) == 1
    assert plan.dependencies == ()


def test_runtime_prepares_multi_claims_independently() -> None:
    """
    Integration contract:

    The public runtime must not route the whole compound
    question once and then reuse that frame for all graph
    nodes.

    Each decomposed claim is prepared independently.
    """

    import inspect

    from basira.api.governed_runtime import (
        PublicGovernedQueryRuntime,
    )

    assert hasattr(
        PublicGovernedQueryRuntime,
        "_prepare_public_claim",
    )

    assert hasattr(
        PublicGovernedQueryRuntime,
        "_plan_public_claim_graph",
    )

    source = inspect.getsource(
        PublicGovernedQueryRuntime
        ._prepare_public_claim
    )

    assert (
        "understanding_service" in source
    )
    assert (
        "_canonical_resolution" in source
    )
    assert "route_proposer" in source
    assert "route_governor" in source
    assert "self.router.route" in source


def test_multi_claim_plan_does_not_forward_one_explicit_quran_anchor() -> None:
    """
    One caller-supplied Quran reference must never be
    silently attached to every node in a compound graph.
    """

    import inspect

    from basira.api.governed_runtime import (
        PublicGovernedQueryRuntime,
    )

    source = inspect.getsource(
        PublicGovernedQueryRuntime
        ._plan_public_claim_graph
    )

    assert "single_claim" in source
    assert "if single_claim" in source


def test_runtime_has_real_graph_execution_boundary() -> None:
    import inspect

    from basira.api.governed_runtime import (
        PublicGovernedQueryRuntime,
    )

    source = inspect.getsource(
        PublicGovernedQueryRuntime
        ._execute_public_claim_graph
    )

    assert "AgentCoordinator" in source
    assert "ExecutionLedger" in source
    assert "ExecutionBudget" in source
    assert "GovernedCapabilityExecutor" in source
    assert "PublicGraphOutcomeEvaluator" in source
    assert "ClaimEvidencePolicySet" in source


def test_graph_execution_uses_task_mapped_understanding() -> None:
    import inspect

    from basira.api.governed_runtime import (
        ClaimMappedUnderstandingService,
        PublicGovernedQueryRuntime,
    )

    service_source = inspect.getsource(
        ClaimMappedUnderstandingService
    )

    execution_source = inspect.getsource(
        PublicGovernedQueryRuntime
        ._execute_public_claim_graph
    )

    assert "_by_claim_text" in service_source

    assert (
        "ClaimMappedUnderstandingService"
        in execution_source
    )

    assert (
        "FrozenUnderstandingService("
        not in execution_source
    )


def test_graph_execution_budget_is_bounded() -> None:
    import inspect

    from basira.api.governed_runtime import (
        PublicGovernedQueryRuntime,
    )

    source = inspect.getsource(
        PublicGovernedQueryRuntime
        ._execute_public_claim_graph
    )

    assert "max_delegations=0" in source
    assert "max_agents_per_claim=1" in source
    assert "max_total_agent_runs=(" in source


def test_public_execute_switches_only_multi_claim_questions() -> None:
    import inspect

    from basira.api.governed_runtime import (
        PublicGovernedQueryRuntime,
    )

    source = inspect.getsource(
        PublicGovernedQueryRuntime.execute
    )

    assert (
        "self.claim_graph_planner"
        in source
    )

    assert "len(claim_texts) > 1" in source

    assert (
        "_execute_multi_claim_public"
        in source
    )


def test_graph_publication_requires_complete_release() -> None:
    import inspect

    from basira.api.governed_runtime import (
        PublicGovernedQueryRuntime,
    )

    source = inspect.getsource(
        PublicGovernedQueryRuntime
        ._aggregate_public_claim_graph
    )

    assert (
        "released_task_ids != all_task_ids"
        in source
    )

    assert "run.withheld_task_ids" in source
    assert "run.blocked_task_ids" in source
    assert "run.unresolved_task_ids" in source


def test_graph_publication_recomposes_every_claim_independently() -> None:
    import inspect

    from basira.api.governed_runtime import (
        PublicGovernedQueryRuntime,
    )

    source = inspect.getsource(
        PublicGovernedQueryRuntime
        ._aggregate_public_claim_graph
    )

    assert (
        "question=task.claim_text"
        in source
    )

    assert (
        "semantic_claim_verification"
        in source
    )

    assert (
        '!= "pass"'
        in source
    )


def test_graph_publication_uses_aggregate_semantic_evidence() -> None:
    import inspect

    from basira.api.governed_runtime import (
        PublicGovernedQueryRuntime,
    )

    source = inspect.getsource(
        PublicGovernedQueryRuntime
        ._aggregate_public_claim_graph
    )

    assert (
        "retrieval_for_task"
        in source
    )

    assert (
        "self.decision_service"
        in source
    )

    assert (
        "UnifiedRetrievalResult"
        in source
    )



def test_graph_aggregation_namespaces_published_claim_ids() -> None:
    import inspect

    from basira.api.governed_runtime import (
        PublicGovernedQueryRuntime,
    )

    source = inspect.getsource(
        PublicGovernedQueryRuntime
        ._aggregate_public_claim_graph
    )

    assert (
        'f"graph-{index}-"'
        in source
    )

    assert (
        "replace("
        in source
    )

    assert (
        "claim_id=("
        in source
    )
