from __future__ import annotations

from basira.answer.composer import (
    GroundedAnswerComposer,
)
from basira.answer.report import (
    AnswerIntegrityReportBuilder,
)
from basira.answer.semantic_verification import (
    GeneratedClaimEvidenceRecord,
    GeneratedClaimSemanticVerifier,
)
from basira.api.service import (
    BasiraQueryService,
)
from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceRequirementAssessment,
    EvidenceRequirementState,
)
from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionAction,
    EvidenceDecisionReason,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.evidence.service import (
    EvidenceDecisionOutcome,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
    RelationOrigin,
)


class RelationEvaluator:
    def __init__(
        self,
        relation: ClaimEvidenceRelation,
    ) -> None:
        self.relation = relation

    def evaluate(
        self,
        *,
        claim,
        evidence,
    ) -> GeneratedClaimEvidenceRecord:
        return GeneratedClaimEvidenceRecord(
            claim_id=claim.claim_id,
            evidence_id=evidence.evidence_id,
            relation=self.relation,
            origin=RelationOrigin.MODEL,
            confidence=0.9,
        )


def outcome() -> EvidenceDecisionOutcome:
    node = EvidenceNode(
        evidence_id="tafsir:1",
        domain=EvidenceDomain.TAFSIR,
        text=("هذا نص تفسيري أصلي مأخوذ من المصدر."),
        source_id="surahapp-tafsir-saadi",
        reference="2:255",
    )

    bundle = EvidenceBundle(
        evidence=(node,),
        required_assessments=(
            EvidenceRequirementAssessment(
                need=EvidenceNeed.TAFSIR,
                state=(EvidenceRequirementState.SATISFIED),
                evidence_ids=(node.evidence_id,),
            ),
        ),
    )

    return EvidenceDecisionOutcome(
        bundle=bundle,
        decision=EvidenceDecision(
            action=(EvidenceDecisionAction.ANSWER),
            reasons=(EvidenceDecisionReason.COMPLETE_EVIDENCE,),
        ),
        expert_review=None,
    )


def composer_for(
    relation: ClaimEvidenceRelation,
) -> GroundedAnswerComposer:
    return GroundedAnswerComposer(
        semantic_verifier=(
            GeneratedClaimSemanticVerifier(evaluator=(RelationEvaluator(relation)))
        )
    )


def test_semantic_pass_allows_publication() -> None:
    answer = composer_for(ClaimEvidenceRelation.SUPPORTS).compose(
        question="ما معنى الآية؟",
        outcome=outcome(),
    )

    assert answer.has_answer

    assert answer.semantic_claim_verification == "pass"

    assert answer.semantic_verification_issues == ()

    assert answer.claims
    assert answer.citations


def test_semantic_regenerate_suppresses_publication() -> None:
    answer = composer_for(ClaimEvidenceRelation.PARTIAL).compose(
        question="ما معنى الآية؟",
        outcome=outcome(),
    )

    assert not answer.has_answer

    assert answer.semantic_claim_verification == "regenerate"

    assert "partial_support" in answer.semantic_verification_issues

    assert answer.claims == ()
    assert answer.citations == ()
    assert answer.used_evidence_ids == ()


def test_semantic_block_suppresses_publication() -> None:
    answer = composer_for(ClaimEvidenceRelation.CONTRADICTS).compose(
        question="ما معنى الآية؟",
        outcome=outcome(),
    )

    assert not answer.has_answer

    assert answer.semantic_claim_verification == "block"

    assert "contradicted_by_citation" in answer.semantic_verification_issues


def test_default_composer_remains_backward_compatible() -> None:
    answer = GroundedAnswerComposer().compose(
        question="ما معنى الآية؟",
        outcome=outcome(),
    )

    assert answer.has_answer

    assert answer.semantic_claim_verification == "not_enabled"


def test_integrity_report_carries_runtime_semantic_state() -> None:
    answer = composer_for(ClaimEvidenceRelation.SUPPORTS).compose(
        question="ما معنى الآية؟",
        outcome=outcome(),
    )

    report = AnswerIntegrityReportBuilder().build(
        claims=answer.claims,
        used_evidence_ids=(answer.used_evidence_ids),
        evidence=(outcome().bundle.evidence),
        limitations=(answer.limitations),
        conflicts=(),
        semantic_claim_verification=(answer.semantic_claim_verification),
        semantic_verification_issues=(answer.semantic_verification_issues),
    )

    assert report.semantic_claim_verification == "pass"

    assert report.semantic_verification_issues == ()


def test_api_service_can_inject_semantic_verifier() -> None:
    verifier = GeneratedClaimSemanticVerifier(
        evaluator=(RelationEvaluator(ClaimEvidenceRelation.SUPPORTS))
    )

    service = BasiraQueryService(
        retriever=object(),  # type: ignore[arg-type]
        semantic_verifier=verifier,
    )

    assert service.composer.semantic_verifier is verifier


def test_final_render_is_exactly_verified_claim_units() -> None:
    answer = composer_for(ClaimEvidenceRelation.SUPPORTS).compose(
        question="ما معنى الآية؟",
        outcome=outcome(),
    )

    assert answer.has_answer
    assert answer.claims

    rendered = answer.answer or ""

    residual = rendered.replace(
        "وفق الأدلة المعتمدة:",
        "",
        1,
    )

    for index, claim in enumerate(
        answer.claims,
        start=1,
    ):
        unit = f"[{index}] {claim.text}"

        assert unit in rendered

        residual = residual.replace(
            unit,
            "",
            1,
        )

    assert not residual.strip()
