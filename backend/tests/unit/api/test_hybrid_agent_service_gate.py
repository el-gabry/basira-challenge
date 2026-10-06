from __future__ import annotations

import inspect

from basira.api.service import (
    BasiraQueryService,
    _hybrid_preflight_error,
    _material_only_result_is_safe,
    build_default_query_service,
)
from basira.orchestration.hybrid_agent import (
    HybridResolverAgent,
)


def test_public_builder_enables_hybrid_agent() -> None:
    source = inspect.getsource(build_default_query_service)

    assert "hybrid_agent=HybridResolverAgent()" in source


def test_service_executes_agent_before_governed_core() -> None:
    source = inspect.getsource(BasiraQueryService.execute)

    plan_pos = source.index("self.hybrid_agent.plan")

    core_pos = source.index("self.governed_runtime.execute")

    assert plan_pos < core_pos


def test_phase_two_is_blocked_before_core() -> None:
    plan = HybridResolverAgent().plan(
        question="ما معنى التوحيد؟",
        language="ar",
    )

    reason = _hybrid_preflight_error(plan)

    assert reason is not None

    assert "phase_2_capability_not_admitted" in reason


def test_personalized_fiqh_is_handed_to_existing_core() -> None:
    plan = HybridResolverAgent().plan(
        question=("أنا في دولة كذا هل يجوز لي فعل هذا في زواجي؟"),
        language="ar",
    )

    # Agent records the obligation but does not
    # replace the existing governed Fiqh decision.
    assert plan.requires_expert_referral

    assert _hybrid_preflight_error(plan) is None


def test_core_hadith_is_not_blocked() -> None:
    plan = HybridResolverAgent().plan(
        question="ما صحة حديث 65065؟",
        language="ar",
    )

    assert _hybrid_preflight_error(plan) is None


def test_material_only_clean_shell_is_allowed() -> None:
    assert _material_only_result_is_safe(
        has_answer=False,
        used_evidence_ids=(),
        evidence_count=0,
        action="retrieve_more",
    )


def test_material_only_cannot_publish_answer() -> None:
    assert not _material_only_result_is_safe(
        has_answer=True,
        used_evidence_ids=("e1",),
        evidence_count=1,
        action="answer",
    )


def test_material_only_cannot_even_receive_religious_evidence() -> None:
    assert not _material_only_result_is_safe(
        has_answer=False,
        used_evidence_ids=(),
        evidence_count=1,
        action="retrieve_more",
    )


def test_agent_language_is_question_resolution_not_ui_presentation() -> None:
    plan = HybridResolverAgent().plan(
        question=("Translate tawhid into English"),
    )

    assert plan.language == "en"
