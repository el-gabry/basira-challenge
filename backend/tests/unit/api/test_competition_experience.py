from __future__ import annotations

from types import SimpleNamespace

from basira.api.experience import (
    ExperienceState,
    TraceStepStatus,
    build_competition_experience,
)
from basira.api.schemas import (
    QueryResponse,
)


def node(
    evidence_id: str = "evidence:1",
    source_id: str = "source:1",
):
    return SimpleNamespace(
        evidence_id=evidence_id,
        source_id=source_id,
    )


def requirement(
    state: str,
    evidence_ids=(),
):
    return SimpleNamespace(
        state=SimpleNamespace(
            value=state,
        ),
        evidence_ids=tuple(evidence_ids),
    )


def conflict(
    *evidence_ids: str,
):
    return SimpleNamespace(
        evidence_ids=evidence_ids,
    )


def build(
    *,
    action: str = "answer",
    has_answer: bool = True,
    semantic: str = "pass",
    evidence=None,
    used=("evidence:1",),
    requirements=None,
    conflicts=(),
    limitations=(),
    unavailable=frozenset(),
    issues=(),
):
    if evidence is None:
        evidence = (node(),)

    if requirements is None:
        requirements = (
            requirement(
                "satisfied",
                ("evidence:1",),
            ),
        )

    return build_competition_experience(
        action=action,
        has_answer=has_answer,
        intent="tafsir_question",
        confidence=0.94,
        evidence=tuple(evidence),
        used_evidence_ids=tuple(used),
        requirements=tuple(requirements),
        conflicts=tuple(conflicts),
        limitations=tuple(limitations),
        unavailable_domains=frozenset(unavailable),
        semantic_claim_verification=(semantic),
        semantic_verification_issues=tuple(issues),
    )


def test_semantic_pass_becomes_verified_ui_state() -> None:
    result = build()

    assert result.state is ExperienceState.VERIFIED
    assert result.can_publish is True
    assert result.label == "إجابة موثقة"


def test_semantic_not_enabled_never_claims_verified() -> None:
    result = build(semantic="not_enabled")

    assert result.state is ExperienceState.GROUNDED
    assert result.can_publish is True


def test_conflict_is_visible_and_not_collapsed() -> None:
    result = build(
        conflicts=(
            conflict(
                "grade:a",
                "grade:b",
            ),
        )
    )

    assert result.state is ExperienceState.CONFLICT

    conflict_step = next(step for step in result.trace if step.key == "conflicts")

    assert conflict_step.status is TraceStepStatus.WARNING

    assert set(conflict_step.evidence_ids) == {
        "grade:a",
        "grade:b",
    }


def test_retrieve_more_is_not_publishable() -> None:
    result = build(
        action="retrieve_more",
        has_answer=False,
        semantic="not_enabled",
        evidence=(),
        used=(),
        requirements=(requirement("missing_evidence"),),
    )

    assert result.state is ExperienceState.NEEDS_MORE_EVIDENCE
    assert result.can_publish is False


def test_semantic_regenerate_is_not_publishable() -> None:
    result = build(
        has_answer=False,
        semantic="regenerate",
        used=(),
        issues=("partial_support",),
    )

    assert result.state is ExperienceState.REGENERATE
    assert result.can_publish is False

    publication = next(step for step in result.trace if step.key == "publication")

    assert "partial_support" in publication.summary


def test_semantic_block_is_not_publishable() -> None:
    result = build(
        has_answer=False,
        semantic="block",
        used=(),
        issues=("contradicted_by_citation",),
    )

    assert result.state is ExperienceState.BLOCKED
    assert result.can_publish is False


def test_resolved_absence_counts_as_resolved_requirement() -> None:
    result = build(requirements=(requirement("no_attested_entry"),))

    step = next(step for step in result.trace if step.key == "requirements")

    assert step.status is TraceStepStatus.COMPLETE


def test_unavailable_domain_is_visible_in_evidence_trace() -> None:
    unavailable = "tafsir"

    result = build(
        action="retrieve_more",
        has_answer=False,
        semantic="not_enabled",
        evidence=(),
        used=(),
        requirements=(requirement("unavailable_domain"),),
        unavailable=frozenset(
            {
                unavailable,
            }
        ),
    )

    step = next(step for step in result.trace if step.key == "evidence")

    assert step.status is TraceStepStatus.WARNING
    assert "tafsir" in step.summary


def test_query_response_exposes_experience_contract() -> None:
    schema = QueryResponse.model_json_schema()

    assert "experience" in schema["properties"]
