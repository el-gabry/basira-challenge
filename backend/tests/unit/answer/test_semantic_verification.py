from __future__ import annotations

import pytest

from basira.answer.models import (
    StructuredClaim,
)
from basira.answer.semantic_verification import (
    GeneratedClaimEvidenceRecord,
    GeneratedClaimSemanticVerifier,
    GeneratedClaimVerificationAction,
    GeneratedClaimVerificationIssue,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
    RelationOrigin,
)


def node(
    *,
    evidence_id: str,
    text: str = "source text",
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=EvidenceDomain.TAFSIR,
        text=text,
        source_id=f"source:{evidence_id}",
        reference="2:255",
    )


def claim(
    *,
    claim_id: str = "claim:1",
    text: str = "generated claim",
    evidence_ids: tuple[
        str,
        ...,
    ] = ("e:1",),
) -> StructuredClaim:
    return StructuredClaim(
        axis_id="tafsir",
        claim_id=claim_id,
        text=text,
        evidence_ids=evidence_ids,
    )


class MappingEvaluator:
    def __init__(
        self,
        mapping: dict[
            tuple[str, str],
            ClaimEvidenceRelation,
        ],
    ) -> None:
        self.mapping = mapping
        self.calls: list[tuple[str, str]] = []

    def evaluate(
        self,
        *,
        claim: StructuredClaim,
        evidence: EvidenceNode,
    ) -> GeneratedClaimEvidenceRecord:
        key = (
            claim.claim_id,
            evidence.evidence_id,
        )

        self.calls.append(key)

        return GeneratedClaimEvidenceRecord(
            claim_id=claim.claim_id,
            evidence_id=evidence.evidence_id,
            relation=self.mapping[key],
            origin=RelationOrigin.MODEL,
            confidence=0.9,
        )


def test_supported_generated_claim_passes() -> None:
    evaluator = MappingEvaluator(
        {
            (
                "claim:1",
                "e:1",
            ): (ClaimEvidenceRelation.SUPPORTS),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(claim(),),
        evidence=(node(evidence_id="e:1"),),
    )

    assert result.action is GeneratedClaimVerificationAction.PASS

    assert result.passed
    assert result.issue_types == ()


def test_default_verifier_fails_closed_to_regenerate() -> None:
    result = GeneratedClaimSemanticVerifier().verify(
        claims=(claim(),),
        evidence=(node(evidence_id="e:1"),),
    )

    assert result.action is GeneratedClaimVerificationAction.REGENERATE

    assert GeneratedClaimVerificationIssue.UNKNOWN_RELATION in result.issue_types

    assert (
        GeneratedClaimVerificationIssue.MISSING_POSITIVE_SUPPORT in result.issue_types
    )


@pytest.mark.parametrize(
    (
        "relation",
        "issue",
    ),
    (
        (
            ClaimEvidenceRelation.PARTIAL,
            GeneratedClaimVerificationIssue.PARTIAL_SUPPORT,
        ),
        (
            ClaimEvidenceRelation.IRRELEVANT,
            GeneratedClaimVerificationIssue.IRRELEVANT_CITATION,
        ),
        (
            ClaimEvidenceRelation.UNKNOWN,
            GeneratedClaimVerificationIssue.UNKNOWN_RELATION,
        ),
        (
            ClaimEvidenceRelation.CONTEXT_ONLY,
            GeneratedClaimVerificationIssue.MISSING_POSITIVE_SUPPORT,
        ),
    ),
)
def test_non_support_semantics_require_regeneration(
    relation: ClaimEvidenceRelation,
    issue: (GeneratedClaimVerificationIssue),
) -> None:
    evaluator = MappingEvaluator(
        {
            (
                "claim:1",
                "e:1",
            ): relation,
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(claim(),),
        evidence=(node(evidence_id="e:1"),),
    )

    assert result.action is GeneratedClaimVerificationAction.REGENERATE

    assert issue in result.issue_types


def test_contradiction_blocks_publication_even_if_another_citation_supports() -> None:
    evaluator = MappingEvaluator(
        {
            (
                "claim:1",
                "e:1",
            ): (ClaimEvidenceRelation.SUPPORTS),
            (
                "claim:1",
                "e:2",
            ): (ClaimEvidenceRelation.CONTRADICTS),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(
            claim(
                evidence_ids=(
                    "e:1",
                    "e:2",
                )
            ),
        ),
        evidence=(
            node(evidence_id="e:1"),
            node(evidence_id="e:2"),
        ),
    )

    assert result.action is GeneratedClaimVerificationAction.BLOCK

    assert (
        GeneratedClaimVerificationIssue.CONTRADICTED_BY_CITATION in result.issue_types
    )


def test_missing_citation_blocks_publication() -> None:
    result = GeneratedClaimSemanticVerifier().verify(
        claims=(claim(evidence_ids=()),),
        evidence=(node(evidence_id="e:1"),),
    )

    assert result.action is GeneratedClaimVerificationAction.BLOCK

    assert GeneratedClaimVerificationIssue.MISSING_EVIDENCE_LINK in result.issue_types


def test_unknown_citation_blocks_before_it_can_be_used() -> None:
    evaluator = MappingEvaluator(
        {
            (
                "claim:1",
                "e:1",
            ): (ClaimEvidenceRelation.SUPPORTS),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(
            claim(
                evidence_ids=(
                    "e:1",
                    "missing",
                )
            ),
        ),
        evidence=(node(evidence_id="e:1"),),
    )

    assert result.action is GeneratedClaimVerificationAction.BLOCK

    assert GeneratedClaimVerificationIssue.UNKNOWN_EVIDENCE_ID in result.issue_types

    assert evaluator.calls == [
        (
            "claim:1",
            "e:1",
        )
    ]


def test_evaluator_only_sees_claim_cited_evidence() -> None:
    evaluator = MappingEvaluator(
        {
            (
                "claim:1",
                "e:1",
            ): (ClaimEvidenceRelation.SUPPORTS),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(claim(),),
        evidence=(
            node(evidence_id="e:1"),
            node(evidence_id="uncited"),
        ),
    )

    assert result.passed

    assert evaluator.calls == [
        (
            "claim:1",
            "e:1",
        )
    ]


def test_context_only_may_accompany_real_support() -> None:
    evaluator = MappingEvaluator(
        {
            (
                "claim:1",
                "e:1",
            ): (ClaimEvidenceRelation.SUPPORTS),
            (
                "claim:1",
                "e:2",
            ): (ClaimEvidenceRelation.CONTEXT_ONLY),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(
            claim(
                evidence_ids=(
                    "e:1",
                    "e:2",
                )
            ),
        ),
        evidence=(
            node(evidence_id="e:1"),
            node(evidence_id="e:2"),
        ),
    )

    assert result.passed


def test_irrelevant_extra_citation_requires_regeneration_even_with_support() -> None:
    evaluator = MappingEvaluator(
        {
            (
                "claim:1",
                "e:1",
            ): (ClaimEvidenceRelation.SUPPORTS),
            (
                "claim:1",
                "e:2",
            ): (ClaimEvidenceRelation.IRRELEVANT),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(
            claim(
                evidence_ids=(
                    "e:1",
                    "e:2",
                )
            ),
        ),
        evidence=(
            node(evidence_id="e:1"),
            node(evidence_id="e:2"),
        ),
    )

    assert result.action is GeneratedClaimVerificationAction.REGENERATE

    assert GeneratedClaimVerificationIssue.IRRELEVANT_CITATION in result.issue_types


def test_all_generated_claims_must_pass() -> None:
    evaluator = MappingEvaluator(
        {
            (
                "claim:1",
                "e:1",
            ): (ClaimEvidenceRelation.SUPPORTS),
            (
                "claim:2",
                "e:2",
            ): (ClaimEvidenceRelation.UNKNOWN),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(
            claim(
                claim_id="claim:1",
                evidence_ids=("e:1",),
            ),
            claim(
                claim_id="claim:2",
                evidence_ids=("e:2",),
            ),
        ),
        evidence=(
            node(evidence_id="e:1"),
            node(evidence_id="e:2"),
        ),
    )

    assert result.action is GeneratedClaimVerificationAction.REGENERATE

    by_id = {item.claim_id: item for item in result.claims}

    assert by_id["claim:1"].supported

    assert not by_id["claim:2"].supported


def test_duplicate_claim_id_blocks_publication() -> None:
    evaluator = MappingEvaluator(
        {
            (
                "claim:1",
                "e:1",
            ): (ClaimEvidenceRelation.SUPPORTS),
            (
                "claim:1",
                "e:2",
            ): (ClaimEvidenceRelation.SUPPORTS),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(
            claim(
                evidence_ids=("e:1",),
            ),
            claim(
                evidence_ids=("e:2",),
            ),
        ),
        evidence=(
            node(evidence_id="e:1"),
            node(evidence_id="e:2"),
        ),
    )

    assert result.action is GeneratedClaimVerificationAction.BLOCK

    assert GeneratedClaimVerificationIssue.DUPLICATE_CLAIM_ID in result.issue_types


def test_evaluator_cannot_return_relation_for_different_claim() -> None:
    class BadEvaluator:
        def evaluate(
            self,
            *,
            claim: StructuredClaim,
            evidence: EvidenceNode,
        ) -> GeneratedClaimEvidenceRecord:
            del claim

            return GeneratedClaimEvidenceRecord(
                claim_id="claim:other",
                evidence_id=(evidence.evidence_id),
                relation=(ClaimEvidenceRelation.SUPPORTS),
                origin=(RelationOrigin.MODEL),
            )

    with pytest.raises(
        ValueError,
        match="different claim",
    ):
        (
            GeneratedClaimSemanticVerifier(
                evaluator=BadEvaluator(),
            ).verify(
                claims=(claim(),),
                evidence=(node(evidence_id="e:1"),),
            )
        )


def test_evaluator_cannot_return_relation_for_different_evidence() -> None:
    class BadEvaluator:
        def evaluate(
            self,
            *,
            claim: StructuredClaim,
            evidence: EvidenceNode,
        ) -> GeneratedClaimEvidenceRecord:
            del evidence

            return GeneratedClaimEvidenceRecord(
                claim_id=claim.claim_id,
                evidence_id="other",
                relation=(ClaimEvidenceRelation.SUPPORTS),
                origin=(RelationOrigin.MODEL),
            )

    with pytest.raises(
        ValueError,
        match="different evidence",
    ):
        (
            GeneratedClaimSemanticVerifier(
                evaluator=BadEvaluator(),
            ).verify(
                claims=(claim(),),
                evidence=(node(evidence_id="e:1"),),
            )
        )


def test_semantic_result_does_not_grant_religious_authority() -> None:
    evaluator = MappingEvaluator(
        {
            (
                "claim:1",
                "e:1",
            ): (ClaimEvidenceRelation.SUPPORTS),
        }
    )

    result = GeneratedClaimSemanticVerifier(
        evaluator=evaluator,
    ).verify(
        claims=(claim(),),
        evidence=(node(evidence_id="e:1"),),
    )

    for forbidden in (
        "religious_ruling",
        "source_authority",
        "hadith_grade",
        "fatwa",
    ):
        assert not hasattr(
            result,
            forbidden,
        )
