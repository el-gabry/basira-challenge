from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.answer.models import (
    StructuredClaim,
)
from basira.answer.semantic_verification import (
    GeneratedClaimSemanticVerifier,
    GeneratedClaimVerificationAction,
    GeneratedClaimVerificationIssue,
)
from basira.evidence.models import (
    EvidenceNode,
)
from basira.evidence.publication import (
    EvidencePublicationAuthorizer,
)


class FinalOutputIssue(StrEnum):
    """
    Structural/publication failures detected before
    semantic claim verification.

    These are hard publication failures.
    """

    NO_CLAIMS = "no_claims"
    EMPTY_CLAIM_ID = "empty_claim_id"
    DUPLICATE_CLAIM_ID = "duplicate_claim_id"
    EMPTY_CLAIM_TEXT = "empty_claim_text"
    MISSING_EVIDENCE_LINK = "missing_evidence_link"
    UNKNOWN_EVIDENCE_ID = "unknown_evidence_id"
    DUPLICATE_EVIDENCE_ID = "duplicate_evidence_id"
    DUPLICATE_EVIDENCE_LINK = "duplicate_evidence_link"
    UNAUTHORIZED_EVIDENCE = "unauthorized_evidence"


@dataclass(
    frozen=True,
    slots=True,
)
class FinalOutputDraft:
    """
    LLM-facing publication contract.

    The LLM does not return publishable free text.

    It returns atomic user-facing claims. Each claim
    must explicitly name the evidence IDs it relies on.

    Basira verifies these claims before any final answer
    may be rendered to the user.
    """

    claims: tuple[
        StructuredClaim,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class FinalOutputVerificationResult:
    action: GeneratedClaimVerificationAction

    issues: tuple[
        FinalOutputIssue,
        ...,
    ] = ()

    semantic_issues: tuple[
        GeneratedClaimVerificationIssue,
        ...,
    ] = ()

    verified_claim_ids: tuple[
        str,
        ...,
    ] = ()

    verified_evidence_ids: tuple[
        str,
        ...,
    ] = ()

    @property
    def passed(
        self,
    ) -> bool:
        return self.action is GeneratedClaimVerificationAction.PASS


class FinalOutputVerifier:
    """
    Final publication firewall for generated answers.

    Invariant:

        generated claim
            -> explicit evidence IDs
            -> real retrieved evidence
            -> publication-authorized evidence
            -> semantic claim/evidence verification
            -> PASS before publication

    The verifier deliberately does NOT require generated
    wording to be a literal source substring.

    That literal restriction is suitable for Basira's
    current deterministic excerpt composer, but future
    LLM paraphrases must instead be judged by the
    semantic claim/evidence verifier.

    The LLM never owns publication authority.
    """

    def __init__(
        self,
        *,
        publication_authorizer: EvidencePublicationAuthorizer,
        semantic_verifier: GeneratedClaimSemanticVerifier,
    ) -> None:
        self.publication_authorizer = publication_authorizer

        self.semantic_verifier = semantic_verifier

    def verify(
        self,
        *,
        draft: FinalOutputDraft,
        evidence: tuple[
            EvidenceNode,
            ...,
        ],
    ) -> FinalOutputVerificationResult:
        issues: list[FinalOutputIssue] = []

        evidence_by_id = {node.evidence_id: node for node in evidence}

        if len(evidence_by_id) != len(evidence):
            issues.append(FinalOutputIssue.DUPLICATE_EVIDENCE_ID)

        if not draft.claims:
            issues.append(FinalOutputIssue.NO_CLAIMS)

        seen_claim_ids: set[str] = set()

        cited_evidence_ids: list[str] = []

        for claim in draft.claims:
            claim_id = claim.claim_id.strip()

            if not claim_id:
                issues.append(FinalOutputIssue.EMPTY_CLAIM_ID)
            elif claim_id in seen_claim_ids:
                issues.append(FinalOutputIssue.DUPLICATE_CLAIM_ID)
            else:
                seen_claim_ids.add(claim_id)

            if not claim.text.strip():
                issues.append(FinalOutputIssue.EMPTY_CLAIM_TEXT)

            cited_ids = tuple(
                evidence_id.strip()
                for evidence_id in claim.evidence_ids
                if evidence_id.strip()
            )

            if not cited_ids:
                issues.append(FinalOutputIssue.MISSING_EVIDENCE_LINK)

                continue

            if len(set(cited_ids)) != len(cited_ids):
                issues.append(FinalOutputIssue.DUPLICATE_EVIDENCE_LINK)

            cited_evidence_ids.extend(cited_ids)

            for evidence_id in cited_ids:
                node = evidence_by_id.get(evidence_id)

                if node is None:
                    issues.append(FinalOutputIssue.UNKNOWN_EVIDENCE_ID)

                    continue

                if not (self.publication_authorizer.may_publish(node)):
                    issues.append(FinalOutputIssue.UNAUTHORIZED_EVIDENCE)

        structural_issues = tuple(dict.fromkeys(issues))

        if structural_issues:
            return FinalOutputVerificationResult(
                action=(GeneratedClaimVerificationAction.BLOCK),
                issues=structural_issues,
            )

        semantic_result = self.semantic_verifier.verify(
            claims=draft.claims,
            evidence=evidence,
        )

        if semantic_result.action is not GeneratedClaimVerificationAction.PASS:
            return FinalOutputVerificationResult(
                action=(semantic_result.action),
                semantic_issues=(semantic_result.issue_types),
            )

        return FinalOutputVerificationResult(
            action=(GeneratedClaimVerificationAction.PASS),
            verified_claim_ids=tuple(claim.claim_id for claim in draft.claims),
            verified_evidence_ids=tuple(dict.fromkeys(cited_evidence_ids)),
        )
