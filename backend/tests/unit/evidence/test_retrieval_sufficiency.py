from __future__ import annotations

from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceRequirementAssessment,
    EvidenceRequirementState,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.evidence.sufficiency import (
    RetrievalSufficiencyGate,
    RetrievalSufficiencyState,
)


def _node(
    evidence_id: str = "evidence-1",
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=EvidenceDomain.TAFSIR,
        text="نص تفسيري",
        source_id="surahapp-tafsir-saadi",
        reference="2:153",
    )


def _bundle(
    *,
    state: EvidenceRequirementState,
    evidence: tuple[
        EvidenceNode,
        ...,
    ] = (),
    evidence_ids: tuple[
        str,
        ...,
    ] = (),
    need: EvidenceNeed = EvidenceNeed.TAFSIR,
) -> EvidenceBundle:
    return EvidenceBundle(
        evidence=evidence,
        required_assessments=(
            EvidenceRequirementAssessment(
                need=need,
                state=state,
                evidence_ids=evidence_ids,
            ),
        ),
    )


def test_satisfied_requirement_with_resolved_evidence_is_sufficient() -> None:
    node = _node()

    result = RetrievalSufficiencyGate().assess(
        _bundle(
            state=(EvidenceRequirementState.SATISFIED),
            evidence=(node,),
            evidence_ids=(node.evidence_id,),
        )
    )

    assert result.state is RetrievalSufficiencyState.SUFFICIENT
    assert result.allows_positive_evidence_path
    assert result.blocking_needs == ()


def test_missing_requirement_requests_more_retrieval() -> None:
    result = RetrievalSufficiencyGate().assess(
        _bundle(
            state=(EvidenceRequirementState.MISSING_EVIDENCE),
        )
    )

    assert result.state is RetrievalSufficiencyState.NEEDS_MORE_RETRIEVAL
    assert result.requires_more_retrieval

    assert result.blocking_needs == (EvidenceNeed.TAFSIR,)


def test_unavailable_requirement_is_explicit() -> None:
    result = RetrievalSufficiencyGate().assess(
        _bundle(
            state=(EvidenceRequirementState.UNAVAILABLE_DOMAIN),
        )
    )

    assert result.state is RetrievalSufficiencyState.UNAVAILABLE
    assert result.is_unavailable

    assert result.blocking_needs == (EvidenceNeed.TAFSIR,)


def test_no_attested_entry_is_resolved_but_not_positive_evidence() -> None:
    result = RetrievalSufficiencyGate().assess(
        _bundle(
            state=(EvidenceRequirementState.NO_ATTESTED_ENTRY),
        )
    )

    assert result.state is RetrievalSufficiencyState.RESOLVED_ABSENCE

    assert not (result.allows_positive_evidence_path)

    assert result.resolved_absence_needs == (EvidenceNeed.TAFSIR,)


def test_satisfied_requirement_without_evidence_ids_fails_closed() -> None:
    node = _node()

    result = RetrievalSufficiencyGate().assess(
        _bundle(
            state=(EvidenceRequirementState.SATISFIED),
            evidence=(node,),
            evidence_ids=(),
        )
    )

    assert result.state is RetrievalSufficiencyState.INVALID_EVIDENCE_LINK

    assert result.invalid_link_needs == (EvidenceNeed.TAFSIR,)


def test_orphan_evidence_id_fails_closed() -> None:
    node = _node()

    result = RetrievalSufficiencyGate().assess(
        _bundle(
            state=(EvidenceRequirementState.SATISFIED),
            evidence=(node,),
            evidence_ids=("not-in-bundle",),
        )
    )

    assert result.state is RetrievalSufficiencyState.INVALID_EVIDENCE_LINK


def test_missing_evidence_takes_priority_over_resolved_absence() -> None:
    bundle = EvidenceBundle(
        evidence=(),
        required_assessments=(
            EvidenceRequirementAssessment(
                need=EvidenceNeed.TAFSIR,
                state=(EvidenceRequirementState.NO_ATTESTED_ENTRY),
            ),
            EvidenceRequirementAssessment(
                need=(EvidenceNeed.RELATED_HADITH),
                state=(EvidenceRequirementState.MISSING_EVIDENCE),
            ),
        ),
    )

    result = RetrievalSufficiencyGate().assess(bundle)

    assert result.state is RetrievalSufficiencyState.NEEDS_MORE_RETRIEVAL

    assert result.blocking_needs == (EvidenceNeed.RELATED_HADITH,)

    assert result.resolved_absence_needs == (EvidenceNeed.TAFSIR,)


def test_invalid_evidence_link_blocks_answer_decision() -> None:
    from types import SimpleNamespace
    from typing import cast

    from basira.evidence.decision import (
        EvidenceDecisionAction,
        EvidenceDecisionPolicy,
        EvidenceDecisionReason,
    )
    from basira.retrieval.query_understanding import (
        BasiraQueryUnderstanding,
    )

    node = _node()

    bundle = _bundle(
        state=(EvidenceRequirementState.SATISFIED),
        evidence=(node,),
        evidence_ids=("orphan-id",),
    )

    understanding = cast(
        BasiraQueryUnderstanding,
        SimpleNamespace(
            risk_tags=frozenset(),
        ),
    )

    sufficiency = RetrievalSufficiencyGate().assess(bundle)

    decision = EvidenceDecisionPolicy().decide(
        understanding=understanding,
        bundle=bundle,
        sufficiency=sufficiency,
    )

    assert decision.action is EvidenceDecisionAction.ABSTAIN

    assert decision.reasons == (EvidenceDecisionReason.INVALID_REQUIRED_EVIDENCE_LINK,)

    assert decision.unresolved_needs == (EvidenceNeed.TAFSIR,)
