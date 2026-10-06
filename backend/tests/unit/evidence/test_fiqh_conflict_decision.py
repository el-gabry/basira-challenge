from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceConflict,
    EvidenceConflictType,
)
from basira.evidence.decision import (
    EvidenceDecisionAction,
    EvidenceDecisionPolicy,
    EvidenceDecisionReason,
)
from basira.evidence.models import (
    EvidenceNeed,
)
from basira.evidence.sufficiency import (
    RetrievalSufficiencyAssessment,
    RetrievalSufficiencyState,
)
from tests.unit.evidence.test_evidence_decision import (
    make_understanding,
)


def _conflict(
    conflict_type: EvidenceConflictType,
) -> EvidenceConflict:
    return EvidenceConflict(
        conflict_type=conflict_type,
        group_id="test:conflict",
        evidence_ids=(
            "evidence:a",
            "evidence:b",
        ),
    )


def _bundle(
    *conflicts: EvidenceConflict,
) -> EvidenceBundle:
    return EvidenceBundle(
        evidence=(),
        required_assessments=(),
        conflicts=conflicts,
    )


def test_sufficient_fiqh_disagreement_answers_with_limitation():
    decision = EvidenceDecisionPolicy().decide(
        understanding=make_understanding(),
        bundle=_bundle(
            _conflict(
                EvidenceConflictType
                .FIQH_POSITION
            )
        ),
        sufficiency=(
            RetrievalSufficiencyAssessment(
                state=(
                    RetrievalSufficiencyState
                    .SUFFICIENT
                )
            )
        ),
    )

    assert (
        decision.action
        is EvidenceDecisionAction
        .ANSWER_WITH_LIMITATION
    )

    assert (
        EvidenceDecisionReason
        .EVIDENCE_CONFLICT
        in decision.reasons
    )

    assert (
        EvidenceDecisionReason
        .COMPLETE_EVIDENCE
        in decision.reasons
    )

    assert not decision.requires_expert


def test_hadith_conflict_still_escalates_before_sufficiency():
    decision = EvidenceDecisionPolicy().decide(
        understanding=make_understanding(),
        bundle=_bundle(
            _conflict(
                EvidenceConflictType
                .HADITH_GRADE
            )
        ),
        sufficiency=(
            RetrievalSufficiencyAssessment(
                state=(
                    RetrievalSufficiencyState
                    .SUFFICIENT
                )
            )
        ),
    )

    assert (
        decision.action
        is EvidenceDecisionAction
        .ESCALATE_TO_EXPERT
    )

    assert decision.requires_expert


def test_mixed_fiqh_and_blocking_conflict_still_escalates():
    decision = EvidenceDecisionPolicy().decide(
        understanding=make_understanding(),
        bundle=_bundle(
            _conflict(
                EvidenceConflictType
                .FIQH_POSITION
            ),
            _conflict(
                EvidenceConflictType
                .HADITH_GRADE
            ),
        ),
        sufficiency=(
            RetrievalSufficiencyAssessment(
                state=(
                    RetrievalSufficiencyState
                    .SUFFICIENT
                )
            )
        ),
    )

    assert (
        decision.action
        is EvidenceDecisionAction
        .ESCALATE_TO_EXPERT
    )


def test_missing_evidence_cannot_be_bypassed_by_fiqh_disagreement():
    decision = EvidenceDecisionPolicy().decide(
        understanding=make_understanding(),
        bundle=_bundle(
            _conflict(
                EvidenceConflictType
                .FIQH_POSITION
            )
        ),
        sufficiency=(
            RetrievalSufficiencyAssessment(
                state=(
                    RetrievalSufficiencyState
                    .NEEDS_MORE_RETRIEVAL
                ),
                blocking_needs=(
                    EvidenceNeed
                    .FIQH_CONDITIONS,
                ),
            )
        ),
    )

    assert (
        decision.action
        is EvidenceDecisionAction
        .RETRIEVE_MORE
    )

    assert (
        decision.unresolved_needs
        == (
            EvidenceNeed
            .FIQH_CONDITIONS,
        )
    )


def test_invalid_evidence_link_cannot_be_bypassed_by_fiqh_disagreement():
    decision = EvidenceDecisionPolicy().decide(
        understanding=make_understanding(),
        bundle=_bundle(
            _conflict(
                EvidenceConflictType
                .FIQH_POSITION
            )
        ),
        sufficiency=(
            RetrievalSufficiencyAssessment(
                state=(
                    RetrievalSufficiencyState
                    .INVALID_EVIDENCE_LINK
                ),
                blocking_needs=(
                    EvidenceNeed
                    .FIQH_EVIDENCE,
                ),
                invalid_link_needs=(
                    EvidenceNeed
                    .FIQH_EVIDENCE,
                ),
            )
        ),
    )

    assert (
        decision.action
        is EvidenceDecisionAction
        .ABSTAIN
    )


def test_resolved_absence_plus_fiqh_disagreement_remains_limited():
    decision = EvidenceDecisionPolicy().decide(
        understanding=make_understanding(),
        bundle=_bundle(
            _conflict(
                EvidenceConflictType
                .FIQH_POSITION
            )
        ),
        sufficiency=(
            RetrievalSufficiencyAssessment(
                state=(
                    RetrievalSufficiencyState
                    .RESOLVED_ABSENCE
                ),
                resolved_absence_needs=(
                    EvidenceNeed
                    .REVELATION_CONTEXT,
                ),
            )
        ),
    )

    assert (
        decision.action
        is EvidenceDecisionAction
        .ANSWER_WITH_LIMITATION
    )

    assert set(
        decision.reasons
    ) == {
        EvidenceDecisionReason
        .RESOLVED_ABSENCE,
        EvidenceDecisionReason
        .EVIDENCE_CONFLICT,
    }


def test_no_conflict_sufficient_path_remains_answer():
    decision = EvidenceDecisionPolicy().decide(
        understanding=make_understanding(),
        bundle=_bundle(),
        sufficiency=(
            RetrievalSufficiencyAssessment(
                state=(
                    RetrievalSufficiencyState
                    .SUFFICIENT
                )
            )
        ),
    )

    assert (
        decision.action
        is EvidenceDecisionAction
        .ANSWER
    )


def test_legacy_path_fiqh_disagreement_is_also_limited():
    decision = EvidenceDecisionPolicy().decide(
        understanding=make_understanding(),
        bundle=_bundle(
            _conflict(
                EvidenceConflictType
                .FIQH_POSITION
            )
        ),
    )

    assert (
        decision.action
        is EvidenceDecisionAction
        .ANSWER_WITH_LIMITATION
    )

    assert not decision.requires_expert
