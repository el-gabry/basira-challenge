from basira.evidence.models import (
    ContextRequirement,
    EvidenceNeed,
)
from basira.reasoning.contracts import (
    EvidenceObligation,
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
    contemporary_fiqh_frame,
)
from basira.reasoning.routing import (
    ReasoningEvidenceAdapter,
)


def _required_for(
    *obligations: EvidenceObligation,
) -> frozenset[EvidenceNeed]:
    adapter = ReasoningEvidenceAdapter()

    frame = ReligiousReasoningFrame(
        frame_id="test:fiqh-obligations",
        question="test",
        primary_discipline=(
            ReligiousDiscipline.FIQH
        ),
        reasoning_mode=(
            ReasoningMode.LEGAL_RULING
        ),
        obligations=obligations,
    )

    return adapter.strengthen(
        baseline=ContextRequirement(),
        frame=frame,
    ).required


def test_classical_conditions_do_not_require_case_applicability():
    required = _required_for(
        EvidenceObligation.CONDITIONS,
    )

    assert (
        EvidenceNeed.FIQH_CONDITIONS
        in required
    )

    assert (
        EvidenceNeed.FIQH_CONSTRAINTS
        in required
    )

    assert (
        EvidenceNeed.APPLICABILITY_CONDITIONS
        not in required
    )


def test_classical_exceptions_do_not_require_case_applicability():
    required = _required_for(
        EvidenceObligation.EXCEPTIONS,
    )

    assert (
        EvidenceNeed.FIQH_EXCEPTIONS
        in required
    )

    assert (
        EvidenceNeed.FIQH_CONSTRAINTS
        in required
    )

    assert (
        EvidenceNeed.APPLICABILITY_CONDITIONS
        not in required
    )


def test_contemporary_facts_still_require_applicability():
    required = _required_for(
        EvidenceObligation.CONTEMPORARY_FACTS,
    )

    assert (
        EvidenceNeed.APPLICABILITY_CONDITIONS
        in required
    )

    assert (
        EvidenceNeed.SOURCE_PROVENANCE
        in required
    )


def test_temporal_context_still_requires_applicability():
    required = _required_for(
        EvidenceObligation.TEMPORAL_CONTEXT,
    )

    assert (
        EvidenceNeed.APPLICABILITY_CONDITIONS
        in required
    )


def test_jurisdiction_context_still_requires_applicability():
    required = _required_for(
        EvidenceObligation.JURISDICTION_CONTEXT,
    )

    assert (
        EvidenceNeed.APPLICABILITY_CONDITIONS
        in required
    )


def test_contemporary_frame_still_contains_application_obligations():
    frame = contemporary_fiqh_frame(
        frame_id="test:contemporary",
        question="ما حكم معاملة مالية معاصرة؟",
    )

    assert (
        EvidenceObligation.CONTEMPORARY_FACTS
        in frame.obligations
    )

    assert (
        EvidenceObligation.TEMPORAL_CONTEXT
        in frame.obligations
    )

    assert (
        EvidenceObligation.JURISDICTION_CONTEXT
        in frame.obligations
    )
