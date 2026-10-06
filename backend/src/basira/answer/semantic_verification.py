from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from basira.answer.models import (
    StructuredClaim,
)
from basira.evidence.models import (
    EvidenceNode,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
    RelationOrigin,
)


class GeneratedClaimVerificationAction(StrEnum):
    """
    Publication action after semantic verification.

    PASS:
        Every generated claim has positive semantic
        support from at least one cited evidence node,
        with no unresolved or contradictory cited
        relation.

    REGENERATE:
        Citation links are structurally valid, but one
        or more claims are not semantically ready for
        publication.

    BLOCK:
        The publication contract itself is unsafe, such
        as missing/unknown citations or contradiction.
    """

    PASS = "pass"
    REGENERATE = "regenerate"
    BLOCK = "block"


class GeneratedClaimVerificationIssue(StrEnum):
    MISSING_EVIDENCE_LINK = "missing_evidence_link"
    UNKNOWN_EVIDENCE_ID = "unknown_evidence_id"
    DUPLICATE_CLAIM_ID = "duplicate_claim_id"
    MISSING_POSITIVE_SUPPORT = "missing_positive_support"
    PARTIAL_SUPPORT = "partial_support"
    IRRELEVANT_CITATION = "irrelevant_citation"
    UNKNOWN_RELATION = "unknown_relation"
    CONTRADICTED_BY_CITATION = "contradicted_by_citation"


@dataclass(
    frozen=True,
    slots=True,
)
class GeneratedClaimEvidenceRecord:
    claim_id: str
    evidence_id: str
    relation: ClaimEvidenceRelation
    origin: RelationOrigin
    confidence: float | None = None
    rationale: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not self.claim_id.strip():
            raise ValueError("claim_id must not be blank")

        if not self.evidence_id.strip():
            raise ValueError("evidence_id must not be blank")

        if (
            self.origin is RelationOrigin.UNASSESSED
            and self.relation is not ClaimEvidenceRelation.UNKNOWN
        ):
            raise ValueError("unassessed generated-claim relation must be unknown")

        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("confidence must be between 0 and 1")

        if self.rationale is not None:
            rationale = self.rationale.strip()

            if not rationale:
                raise ValueError("rationale must not be blank when provided")

            object.__setattr__(
                self,
                "rationale",
                rationale,
            )


@dataclass(
    frozen=True,
    slots=True,
)
class GeneratedClaimAssessment:
    claim_id: str
    evidence_ids: tuple[
        str,
        ...,
    ]
    records: tuple[
        GeneratedClaimEvidenceRecord,
        ...,
    ]
    issues: tuple[
        GeneratedClaimVerificationIssue,
        ...,
    ]

    @property
    def supported(
        self,
    ) -> bool:
        return (
            any(
                record.relation is ClaimEvidenceRelation.SUPPORTS
                for record in self.records
            )
            and not self.issues
        )


@dataclass(
    frozen=True,
    slots=True,
)
class GeneratedClaimVerificationResult:
    action: GeneratedClaimVerificationAction
    claims: tuple[
        GeneratedClaimAssessment,
        ...,
    ]

    @property
    def passed(
        self,
    ) -> bool:
        return self.action is GeneratedClaimVerificationAction.PASS

    @property
    def issue_types(
        self,
    ) -> tuple[
        GeneratedClaimVerificationIssue,
        ...,
    ]:
        seen: set[GeneratedClaimVerificationIssue] = set()

        ordered: list[GeneratedClaimVerificationIssue] = []

        for assessment in self.claims:
            for issue in assessment.issues:
                if issue in seen:
                    continue

                seen.add(issue)
                ordered.append(issue)

        return tuple(ordered)


class GeneratedClaimEvidenceEvaluator(Protocol):
    """
    Semantic evaluator boundary for one generated claim
    against one cited EvidenceNode.

    It may judge only the relation between the supplied
    claim text and immutable source-derived evidence.
    It may not:
    - create or rewrite evidence;
    - grant source authority;
    - infer uncited evidence;
    - issue a religious ruling;
    - change hadith grading;
    - decide publication by itself.
    """

    def evaluate(
        self,
        *,
        claim: StructuredClaim,
        evidence: EvidenceNode,
    ) -> GeneratedClaimEvidenceRecord: ...


class FailClosedGeneratedClaimEvaluator:
    """
    Safe default until a real semantic verifier is
    explicitly configured.
    """

    def evaluate(
        self,
        *,
        claim: StructuredClaim,
        evidence: EvidenceNode,
    ) -> GeneratedClaimEvidenceRecord:
        return GeneratedClaimEvidenceRecord(
            claim_id=claim.claim_id,
            evidence_id=(evidence.evidence_id),
            relation=(ClaimEvidenceRelation.UNKNOWN),
            origin=(RelationOrigin.UNASSESSED),
        )


class GeneratedClaimSemanticVerifier:
    """
    Verify only the evidence explicitly cited by each
    generated claim.

    Pre-generation task↔evidence support is not reused
    as proof here: generated wording may overstate,
    generalize, reverse, or otherwise distort what the
    evidence supports.

    This post-generation check therefore re-evaluates
    claim text against cited evidence before publication.
    """

    def __init__(
        self,
        *,
        evaluator: (GeneratedClaimEvidenceEvaluator | None) = None,
    ) -> None:
        self._evaluator = evaluator or FailClosedGeneratedClaimEvaluator()

    def verify(
        self,
        *,
        claims: tuple[
            StructuredClaim,
            ...,
        ],
        evidence: tuple[
            EvidenceNode,
            ...,
        ],
    ) -> GeneratedClaimVerificationResult:
        evidence_by_id = {node.evidence_id: node for node in evidence}

        if len(evidence_by_id) != len(evidence):
            raise ValueError("publication evidence IDs must be unique")

        seen_claim_ids: set[str] = set()

        assessments: list[GeneratedClaimAssessment] = []

        hard_block = False
        regenerate = False

        for claim in claims:
            claim_id = claim.claim_id.strip()

            issues: list[GeneratedClaimVerificationIssue] = []

            if not claim_id or claim_id in seen_claim_ids:
                issues.append(GeneratedClaimVerificationIssue.DUPLICATE_CLAIM_ID)
                hard_block = True
            else:
                seen_claim_ids.add(claim_id)

            cited_ids = tuple(claim.evidence_ids)

            if not cited_ids:
                issues.append(GeneratedClaimVerificationIssue.MISSING_EVIDENCE_LINK)
                hard_block = True

                assessments.append(
                    GeneratedClaimAssessment(
                        claim_id=claim_id,
                        evidence_ids=(),
                        records=(),
                        issues=tuple(issues),
                    )
                )
                continue

            unknown_ids = tuple(
                evidence_id
                for evidence_id in cited_ids
                if (evidence_id not in evidence_by_id)
            )

            if unknown_ids:
                issues.append(GeneratedClaimVerificationIssue.UNKNOWN_EVIDENCE_ID)
                hard_block = True

            linked_nodes = tuple(
                evidence_by_id[evidence_id]
                for evidence_id in cited_ids
                if (evidence_id in evidence_by_id)
            )

            records = tuple(
                self._validate_record(
                    claim=claim,
                    evidence=node,
                    record=(
                        self._evaluator.evaluate(
                            claim=claim,
                            evidence=node,
                        )
                    ),
                )
                for node in linked_nodes
            )

            relations = tuple(record.relation for record in records)

            has_support = ClaimEvidenceRelation.SUPPORTS in relations

            if ClaimEvidenceRelation.CONTRADICTS in relations:
                issues.append(GeneratedClaimVerificationIssue.CONTRADICTED_BY_CITATION)
                hard_block = True

            if ClaimEvidenceRelation.PARTIAL in relations:
                issues.append(GeneratedClaimVerificationIssue.PARTIAL_SUPPORT)
                regenerate = True

            if ClaimEvidenceRelation.IRRELEVANT in relations:
                issues.append(GeneratedClaimVerificationIssue.IRRELEVANT_CITATION)
                regenerate = True

            if ClaimEvidenceRelation.UNKNOWN in relations:
                issues.append(GeneratedClaimVerificationIssue.UNKNOWN_RELATION)
                regenerate = True

            if not has_support:
                issues.append(GeneratedClaimVerificationIssue.MISSING_POSITIVE_SUPPORT)
                regenerate = True

            assessments.append(
                GeneratedClaimAssessment(
                    claim_id=claim_id,
                    evidence_ids=cited_ids,
                    records=records,
                    issues=tuple(dict.fromkeys(issues)),
                )
            )

        if hard_block:
            action = GeneratedClaimVerificationAction.BLOCK
        elif regenerate:
            action = GeneratedClaimVerificationAction.REGENERATE
        else:
            action = GeneratedClaimVerificationAction.PASS

        return GeneratedClaimVerificationResult(
            action=action,
            claims=tuple(assessments),
        )

    @staticmethod
    def _validate_record(
        *,
        claim: StructuredClaim,
        evidence: EvidenceNode,
        record: GeneratedClaimEvidenceRecord,
    ) -> GeneratedClaimEvidenceRecord:
        if record.claim_id != claim.claim_id:
            raise ValueError(
                "semantic evaluator returned a relation for a different claim"
            )

        if record.evidence_id != evidence.evidence_id:
            raise ValueError(
                "semantic evaluator returned a relation for different evidence"
            )

        return record
