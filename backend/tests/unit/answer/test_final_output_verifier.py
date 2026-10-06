from __future__ import annotations

from types import SimpleNamespace

from basira.answer.final_output import (
    FinalOutputDraft,
    FinalOutputIssue,
    FinalOutputVerifier,
)
from basira.answer.models import (
    StructuredClaim,
)
from basira.answer.semantic_verification import (
    GeneratedClaimSemanticVerifier,
    GeneratedClaimVerificationAction,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
)


class FakePublicationAuthorizer:
    def __init__(
        self,
        *allowed_ids: str,
    ) -> None:
        self.allowed_ids = frozenset(allowed_ids)

    def may_publish(
        self,
        node,
    ) -> bool:
        return node.evidence_id in self.allowed_ids


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
    ):
        return SimpleNamespace(
            claim_id=claim.claim_id,
            evidence_id=evidence.evidence_id,
            relation=self.relation,
        )


def evidence(
    *,
    evidence_id: str = "e:1",
    text: str = ("ورد في المصدر أن الكرسي جسم عظيم مخلوق."),
):
    return SimpleNamespace(
        evidence_id=evidence_id,
        text=text,
    )


def claim(
    *,
    claim_id: str = "claim-1",
    text: str = ("الكرسي مخلوق عظيم."),
    evidence_ids: tuple[
        str,
        ...,
    ] = ("e:1",),
) -> StructuredClaim:
    return StructuredClaim(
        axis_id="answer",
        claim_id=claim_id,
        text=text,
        evidence_ids=evidence_ids,
    )


def verifier(
    relation: ClaimEvidenceRelation,
    *,
    allowed_ids: tuple[
        str,
        ...,
    ] = ("e:1",),
) -> FinalOutputVerifier:
    return FinalOutputVerifier(
        publication_authorizer=(FakePublicationAuthorizer(*allowed_ids)),
        semantic_verifier=(
            GeneratedClaimSemanticVerifier(evaluator=(RelationEvaluator(relation)))
        ),
    )


def test_supported_llm_paraphrase_can_pass_without_literal_copy():
    node = evidence()

    result = verifier(ClaimEvidenceRelation.SUPPORTS).verify(
        draft=FinalOutputDraft(claims=(claim(text=("الكرسي مخلوق عظيم.")),)),
        evidence=(node,),  # type: ignore[arg-type]
    )

    assert result.passed

    assert result.action is GeneratedClaimVerificationAction.PASS

    assert result.verified_claim_ids == ("claim-1",)

    assert result.verified_evidence_ids == ("e:1",)


def test_claim_without_evidence_link_is_blocked():
    result = verifier(ClaimEvidenceRelation.SUPPORTS).verify(
        draft=FinalOutputDraft(
            claims=(
                claim(
                    evidence_ids=(),
                ),
            )
        ),
        evidence=(evidence(),),  # type: ignore[arg-type]
    )

    assert result.action is GeneratedClaimVerificationAction.BLOCK

    assert FinalOutputIssue.MISSING_EVIDENCE_LINK in result.issues


def test_unknown_evidence_id_is_blocked():
    result = verifier(ClaimEvidenceRelation.SUPPORTS).verify(
        draft=FinalOutputDraft(
            claims=(
                claim(
                    evidence_ids=("missing",),
                ),
            )
        ),
        evidence=(evidence(),),  # type: ignore[arg-type]
    )

    assert result.action is GeneratedClaimVerificationAction.BLOCK

    assert FinalOutputIssue.UNKNOWN_EVIDENCE_ID in result.issues


def test_non_admitted_evidence_is_blocked():
    result = verifier(
        ClaimEvidenceRelation.SUPPORTS,
        allowed_ids=(),
    ).verify(
        draft=FinalOutputDraft(claims=(claim(),)),
        evidence=(evidence(),),  # type: ignore[arg-type]
    )

    assert result.action is GeneratedClaimVerificationAction.BLOCK

    assert FinalOutputIssue.UNAUTHORIZED_EVIDENCE in result.issues


def test_partial_support_requires_regeneration():
    result = verifier(ClaimEvidenceRelation.PARTIAL).verify(
        draft=FinalOutputDraft(claims=(claim(),)),
        evidence=(evidence(),),  # type: ignore[arg-type]
    )

    assert result.action is GeneratedClaimVerificationAction.REGENERATE


def test_contradiction_blocks_publication():
    result = verifier(ClaimEvidenceRelation.CONTRADICTS).verify(
        draft=FinalOutputDraft(claims=(claim(),)),
        evidence=(evidence(),),  # type: ignore[arg-type]
    )

    assert result.action is GeneratedClaimVerificationAction.BLOCK
