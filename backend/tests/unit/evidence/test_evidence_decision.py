from dataclasses import replace

from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceConflict,
    EvidenceConflictType,
    EvidenceRequirementAssessment,
    EvidenceRequirementState,
)
from basira.evidence.decision import (
    EvidenceDecisionAction,
    EvidenceDecisionPolicy,
    EvidenceDecisionReason,
)
from basira.evidence.models import (
    EvidenceNeed,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
    RiskTag,
)


def make_understanding():
    return (
        BasiraQueryUnderstandingService()
        .understand(
            "ما سبب نزول الآية 58:1؟"
        )
    )


def bundle_with(
    *assessments: (
        EvidenceRequirementAssessment
    ),
) -> EvidenceBundle:
    return EvidenceBundle(
        evidence=(),
        required_assessments=(
            assessments
        ),
    )


def assessment(
    need: EvidenceNeed,
    state: EvidenceRequirementState,
) -> EvidenceRequirementAssessment:
    return (
        EvidenceRequirementAssessment(
            need=need,
            state=state,
        )
    )


def test_complete_evidence_allows_answer() -> None:
    bundle = bundle_with(
        assessment(
            EvidenceNeed.CANONICAL_TEXT,
            EvidenceRequirementState
            .SATISFIED,
        ),
        assessment(
            EvidenceNeed.TAFSIR,
            EvidenceRequirementState
            .SATISFIED,
        ),
    )

    decision = (
        EvidenceDecisionPolicy()
        .decide(
            understanding=(
                make_understanding()
            ),
            bundle=bundle,
        )
    )

    assert (
        decision.action
        == EvidenceDecisionAction.ANSWER
    )


def test_resolved_absence_answers_with_limitation() -> None:
    bundle = bundle_with(
        assessment(
            EvidenceNeed.CANONICAL_TEXT,
            EvidenceRequirementState
            .SATISFIED,
        ),
        assessment(
            EvidenceNeed.REVELATION_CONTEXT,
            EvidenceRequirementState
            .NO_ATTESTED_ENTRY,
        ),
    )

    decision = (
        EvidenceDecisionPolicy()
        .decide(
            understanding=(
                make_understanding()
            ),
            bundle=bundle,
        )
    )

    assert (
        decision.action
        == EvidenceDecisionAction
        .ANSWER_WITH_LIMITATION
    )

    assert (
        EvidenceDecisionReason
        .RESOLVED_ABSENCE
        in decision.reasons
    )


def test_missing_evidence_requests_more_retrieval() -> None:
    bundle = bundle_with(
        assessment(
            EvidenceNeed.TAFSIR,
            EvidenceRequirementState
            .MISSING_EVIDENCE,
        ),
    )

    decision = (
        EvidenceDecisionPolicy()
        .decide(
            understanding=(
                make_understanding()
            ),
            bundle=bundle,
        )
    )

    assert (
        decision.action
        == EvidenceDecisionAction
        .RETRIEVE_MORE
    )


def test_unavailable_domain_causes_abstention() -> None:
    bundle = bundle_with(
        assessment(
            EvidenceNeed.FIQH_EVIDENCE,
            EvidenceRequirementState
            .UNAVAILABLE_DOMAIN,
        ),
    )

    decision = (
        EvidenceDecisionPolicy()
        .decide(
            understanding=(
                make_understanding()
            ),
            bundle=bundle,
        )
    )

    assert (
        decision.action
        == EvidenceDecisionAction.ABSTAIN
    )


def test_high_risk_case_escalates_to_expert() -> None:
    understanding = replace(
        make_understanding(),
        risk_tags=frozenset(
            {
                RiskTag.TAKFIR,
                RiskTag.CONTEXT_SENSITIVE,
            }
        ),
    )

    bundle = bundle_with(
        assessment(
            EvidenceNeed.CANONICAL_TEXT,
            EvidenceRequirementState
            .SATISFIED,
        ),
        assessment(
            EvidenceNeed.TAFSIR,
            EvidenceRequirementState
            .SATISFIED,
        ),
    )

    decision = (
        EvidenceDecisionPolicy()
        .decide(
            understanding=understanding,
            bundle=bundle,
        )
    )

    assert (
        decision.action
        == EvidenceDecisionAction
        .ESCALATE_TO_EXPERT
    )

    assert decision.requires_expert

    assert decision.risk_tags == (
        RiskTag.TAKFIR,
    )


def test_evidence_conflict_escalates_to_expert() -> None:
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(
            "ما صحة حديث رقم 5457؟"
        )
    )

    bundle = EvidenceBundle(
        evidence=(),
        required_assessments=(
            assessment(
                EvidenceNeed.HADITH_TEXT,
                EvidenceRequirementState
                .SATISFIED,
            ),
            assessment(
                EvidenceNeed.HADITH_GRADE,
                EvidenceRequirementState
                .SATISFIED,
            ),
        ),
        conflicts=(
            EvidenceConflict(
                conflict_type=(
                    EvidenceConflictType
                    .HADITH_GRADE
                ),
                group_id=(
                    "hadeethenc:5457"
                ),
                evidence_ids=(
                    "source-a:5457:grade",
                    "source-b:5457:grade",
                ),
            ),
        ),
    )

    decision = (
        EvidenceDecisionPolicy()
        .decide(
            understanding=understanding,
            bundle=bundle,
        )
    )

    assert (
        decision.action
        == EvidenceDecisionAction
        .ESCALATE_TO_EXPERT
    )

    assert decision.reasons == (
        EvidenceDecisionReason
        .EVIDENCE_CONFLICT,
    )

    assert decision.unresolved_needs == ()
