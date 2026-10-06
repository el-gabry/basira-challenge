from types import SimpleNamespace

from basira.answer.governed_composer import (
    GovernedGroundedAnswerComposer,
)
from basira.answer.semantic_verification import (
    GeneratedClaimSemanticVerifier,
)
from basira.evidence.publication import (
    GovernedPublicationLedger,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
)
from tests.unit.answer.test_fiqh_group_complete_publication import (
    _outcome,
)


class _SupportsEvaluator:
    def evaluate(
        self,
        *,
        claim,
        evidence,
    ):
        return SimpleNamespace(
            claim_id=claim.claim_id,
            evidence_id=(
                evidence.evidence_id
            ),
            relation=(
                ClaimEvidenceRelation
                .SUPPORTS
            ),
        )


def _composer_and_outcome():
    outcome = _outcome()

    ledger = (
        GovernedPublicationLedger()
    )

    for node in (
        outcome.bundle.evidence
    ):
        ledger.admit(
            node
        )

    verifier = (
        GeneratedClaimSemanticVerifier(
            evaluator=(
                _SupportsEvaluator()
            )
        )
    )

    composer = (
        GovernedGroundedAnswerComposer(
            publication_authorizer=(
                ledger
            ),
            semantic_verifier=(
                verifier
            ),
        )
    )

    return (
        composer,
        outcome,
    )


def test_governed_fiqh_publication_preserves_complete_issue():
    (
        composer,
        outcome,
    ) = _composer_and_outcome()

    answer = composer.compose(
        question=(
            "ما أقوال المذاهب؟"
        ),
        outcome=outcome,
    )

    assert (
        answer.action.value
        == "answer_with_limitation"
    )

    assert (
        answer.semantic_claim_verification
        == "pass"
    )

    assert answer.answer is not None

    assert (
        len(
            answer.used_evidence_ids
        )
        == 28
    )


def test_governed_fiqh_publication_preserves_four_madhhabs():
    (
        composer,
        outcome,
    ) = _composer_and_outcome()

    answer = composer.compose(
        question=(
            "ما أقوال المذاهب؟"
        ),
        outcome=outcome,
    )

    assert answer.answer is not None

    for label in (
        "المذهب الحنفي",
        "المذهب المالكي",
        "المذهب الشافعي",
        "المذهب الحنبلي",
    ):
        assert (
            label
            in answer.answer
        )


def test_governed_fiqh_publication_preserves_legal_structure():
    (
        composer,
        outcome,
    ) = _composer_and_outcome()

    answer = composer.compose(
        question=(
            "ما أقوال المذاهب؟"
        ),
        outcome=outcome,
    )

    assert answer.answer is not None

    for label in (
        "الحكم:",
        "الدليل:",
        "وجه الدلالة:",
        "الشرط:",
        "الاستثناء:",
        "بيان الخلاف:",
    ):
        assert (
            label
            in answer.answer
        )


def test_governed_fiqh_publication_keeps_no_tarjih_boundary():
    (
        composer,
        outcome,
    ) = _composer_and_outcome()

    answer = composer.compose(
        question=(
            "ما أقوال المذاهب؟"
        ),
        outcome=outcome,
    )

    limitations = " ".join(
        answer.limitations
    )

    assert (
        "من دون ترجيح آلي"
        in limitations
    )

    assert (
        "تصويت بالأغلبية"
        in limitations
    )


def test_governed_fiqh_claims_are_all_evidence_linked():
    (
        composer,
        outcome,
    ) = _composer_and_outcome()

    answer = composer.compose(
        question=(
            "ما أقوال المذاهب؟"
        ),
        outcome=outcome,
    )

    assert answer.claims

    publication_ids = set(
        answer.used_evidence_ids
    )

    for claim in answer.claims:
        assert (
            claim.evidence_ids
        )

        assert set(
            claim.evidence_ids
        ).issubset(
            publication_ids
        )
