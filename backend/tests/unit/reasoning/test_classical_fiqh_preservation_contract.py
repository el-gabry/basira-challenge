from basira.reasoning.contracts import (
    AnswerConstraint,
    EvidenceObligation,
)
from basira.reasoning.routing import (
    ReligiousReasoningRouter,
)


def test_general_classical_fiqh_preserves_optional_structure_without_requiring_it():
    frame = (
        ReligiousReasoningRouter
        ._classical_fiqh_ruling(
            "ما حكم مس المرأة فرجها؟"
        )
    )

    assert (
        EvidenceObligation.CLASSICAL_FIQH_POSITION
        in frame.obligations
    )

    assert (
        EvidenceObligation.MADHHAB_SCOPE
        in frame.obligations
    )

    assert (
        EvidenceObligation.SOURCE_ATTRIBUTION
        in frame.obligations
    )

    assert (
        EvidenceObligation.CONDITIONS
        not in frame.obligations
    )

    assert (
        EvidenceObligation.EXCEPTIONS
        not in frame.obligations
    )

    assert (
        AnswerConstraint.PRESERVE_CONDITIONS
        in frame.constraints
    )

    assert (
        AnswerConstraint.PRESERVE_EXCEPTIONS
        in frame.constraints
    )
