from __future__ import annotations

from dataclasses import fields

import pytest

from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.orchestration.contracts import (
    AgentCapability,
    AgentExecutionResult,
    AgentExecutionStatus,
    ClaimTask,
    ContextArtifact,
    ContextKind,
    ContextOrigin,
    DelegationRequest,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
)
from basira.retrieval.query_understanding import (
    RiskTag,
)


def frame() -> ReligiousReasoningFrame:
    return ReligiousReasoningFrame(
        frame_id="reasoning:test",
        question="هل هذه الدعوى صحيحة؟",
        primary_discipline=(
            ReligiousDiscipline.AQIDAH
        ),
        reasoning_mode=(
            ReasoningMode.DIRECT_GROUNDING
        ),
    )


def test_context_artifact_is_explicitly_non_evidentiary() -> None:
    artifact = ContextArtifact(
        context_id="ctx:religion:44",
        kind=ContextKind.RELIGION,
        value="البوذية",
        origin=(
            ContextOrigin.GOVERNED_SOURCE
        ),
        source_id="dawa-center-test",
        source_url=(
            "https://dawa.center/"
            "religion/44"
        ),
        confidence=1.0,
    )

    assert (
        artifact.evidentiary
        is False
    )

    names = {
        item.name
        for item in fields(
            ContextArtifact
        )
    }

    assert "evidence_id" not in names
    assert "authority" not in names
    assert "authority_level" not in names
    assert "authority_scope" not in names


def test_governed_context_requires_source_identity() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "governed-source context "
            "requires source_id"
        ),
    ):
        ContextArtifact(
            context_id="ctx:1",
            kind=ContextKind.LANGUAGE,
            value="fr",
            origin=(
                ContextOrigin.GOVERNED_SOURCE
            ),
        )


@pytest.mark.parametrize(
    "confidence",
    [
        -0.01,
        1.01,
    ],
)
def test_context_confidence_is_bounded(
    confidence: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        ContextArtifact(
            context_id="ctx:1",
            kind=ContextKind.AUDIENCE,
            value="new_muslim",
            origin=ContextOrigin.USER,
            confidence=confidence,
        )


def test_claim_task_reuses_existing_reasoning_and_risk_contracts() -> None:
    task = ClaimTask(
        task_id="claim:1",
        claim_text=(
            "هل هذه الدعوى صحيحة؟"
        ),
        frame=frame(),
        context_requirement=(
            ContextRequirement(
                required=frozenset(
                    {
                        EvidenceNeed
                        .SOURCE_PROVENANCE,
                    }
                )
            )
        ),
        risk_tags=frozenset(
            {
                RiskTag.TAKFIR,
            }
        ),
        context_ids=(
            "ctx:religion:44",
        ),
    )

    assert (
        task.frame.primary_discipline
        is ReligiousDiscipline.AQIDAH
    )

    assert (
        EvidenceNeed.SOURCE_PROVENANCE
        in task.context_requirement.required
    )

    assert (
        RiskTag.TAKFIR
        in task.risk_tags
    )


def test_claim_task_does_not_own_graph_topology() -> None:
    names = {
        item.name
        for item in fields(
            ClaimTask
        )
    }

    assert "parent_task_id" not in names
    assert "parent_task_ids" not in names
    assert "depth" not in names
    assert "children" not in names
    assert "dependencies" not in names


def test_claim_task_frame_must_belong_to_same_claim() -> None:
    mismatched = ReligiousReasoningFrame(
        frame_id="reasoning:other",
        question="سؤال مختلف",
        primary_discipline=(
            ReligiousDiscipline.AQIDAH
        ),
        reasoning_mode=(
            ReasoningMode.DIRECT_GROUNDING
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "reasoning frame must belong "
            "to the same claim text"
        ),
    ):
        ClaimTask(
            task_id="claim:1",
            claim_text=(
                "هل هذه الدعوى صحيحة؟"
            ),
            frame=mismatched,
            context_requirement=(
                ContextRequirement()
            ),
        )


def test_agent_capability_does_not_grant_authority_or_source_access() -> None:
    capability = AgentCapability(
        capability_id="dawah:context",
        agent_id="dawah-agent",
        disciplines=frozenset(
            {
                ReligiousDiscipline
                .CROSS_DISCIPLINARY,
            }
        ),
        context_kinds=frozenset(
            {
                ContextKind.AUDIENCE,
                ContextKind.LANGUAGE,
                ContextKind.RELIGION,
            }
        ),
        may_delegate=True,
    )

    assert capability.may_delegate

    names = {
        item.name
        for item in fields(
            AgentCapability
        )
    }

    assert "authority" not in names
    assert "authority_level" not in names
    assert "authority_scope" not in names
    assert "source_id" not in names
    assert "source_ids" not in names
    assert "runtime_use" not in names


def test_empty_agent_capability_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "at least one supported "
            "dimension"
        ),
    ):
        AgentCapability(
            capability_id="empty",
            agent_id="agent",
        )


def test_delegation_requests_capability_not_target_agent() -> None:
    request = DelegationRequest(
        delegation_id="delegate:1",
        task_id="claim:1",
        reason=(
            "Primary Aqidah evidence "
            "is required."
        ),
        requested_disciplines=(
            frozenset(
                {
                    ReligiousDiscipline
                    .AQIDAH,
                }
            )
        ),
        requested_evidence_needs=(
            frozenset(
                {
                    EvidenceNeed
                    .SOURCE_PROVENANCE,
                }
            )
        ),
    )

    assert (
        ReligiousDiscipline.AQIDAH
        in request.requested_disciplines
    )

    names = {
        item.name
        for item in fields(
            DelegationRequest
        )
    }

    assert "target_agent_id" not in names
    assert "agent_id" not in names
    assert "authority" not in names


def test_empty_delegation_request_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "must request at least "
            "one capability"
        ),
    ):
        DelegationRequest(
            delegation_id="delegate:1",
            task_id="claim:1",
            reason="Need help",
        )


def test_agent_result_separates_evidence_context_and_delegation() -> None:
    evidence = EvidenceNode(
        evidence_id="ev:1",
        domain=EvidenceDomain.GENERAL,
        text="نص",
        source_id="governed-test",
    )

    context = ContextArtifact(
        context_id="ctx:1",
        kind=ContextKind.LANGUAGE,
        value="fr",
        origin=(
            ContextOrigin
            .QUERY_UNDERSTANDING
        ),
    )

    delegation = DelegationRequest(
        delegation_id="delegate:1",
        task_id="claim:1",
        reason="Need Hadith text",
        requested_evidence_needs=(
            frozenset(
                {
                    EvidenceNeed.HADITH_TEXT,
                }
            )
        ),
    )

    result = AgentExecutionResult(
        task_id="claim:1",
        agent_id="dawah-agent",
        status=(
            AgentExecutionStatus.PARTIAL
        ),
        evidence=(evidence,),
        context=(context,),
        delegations=(delegation,),
    )

    assert result.evidence == (
        evidence,
    )

    assert result.context == (
        context,
    )

    assert result.delegations == (
        delegation,
    )


def test_finished_agent_execution_does_not_mean_evidence_sufficient() -> None:
    result = AgentExecutionResult(
        task_id="claim:1",
        agent_id="agent",
        status=(
            AgentExecutionStatus.FINISHED
        ),
    )

    assert (
        result.status
        is AgentExecutionStatus.FINISHED
    )

    names = {
        item.name
        for item in fields(
            AgentExecutionResult
        )
    }

    assert "answer" not in names
    assert "final_answer" not in names
    assert "evidence_sufficient" not in names
    assert "authority" not in names
    assert "authority_level" not in names


def test_agent_result_rejects_duplicate_artifact_ids() -> None:
    first = ContextArtifact(
        context_id="ctx:1",
        kind=ContextKind.LANGUAGE,
        value="fr",
        origin=ContextOrigin.USER,
    )

    second = ContextArtifact(
        context_id="ctx:1",
        kind=ContextKind.LANGUAGE,
        value="en",
        origin=ContextOrigin.USER,
    )

    with pytest.raises(
        ValueError,
        match=(
            "context ids must be unique"
        ),
    ):
        AgentExecutionResult(
            task_id="claim:1",
            agent_id="agent",
            status=(
                AgentExecutionStatus
                .FINISHED
            ),
            context=(
                first,
                second,
            ),
        )


def test_delegation_must_belong_to_result_task() -> None:
    delegation = DelegationRequest(
        delegation_id="delegate:1",
        task_id="claim:other",
        reason="Need Tafsir",
        requested_evidence_needs=(
            frozenset(
                {
                    EvidenceNeed.TAFSIR,
                }
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "delegations must belong "
            "to the result task"
        ),
    ):
        AgentExecutionResult(
            task_id="claim:1",
            agent_id="agent",
            status=(
                AgentExecutionStatus
                .PARTIAL
            ),
            delegations=(
                delegation,
            ),
        )
