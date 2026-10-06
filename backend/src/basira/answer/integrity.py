from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.answer.models import (
    StructuredClaim,
)
from basira.evidence.models import (
    EvidenceNode,
)


class ClaimIntegrityIssueType(StrEnum):
    EMPTY_AXIS_ID = "empty_axis_id"

    EMPTY_CLAIM_ID = "empty_claim_id"

    DUPLICATE_CLAIM_ID = "duplicate_claim_id"

    EMPTY_CLAIM_TEXT = "empty_claim_text"

    MISSING_EVIDENCE_LINK = "missing_evidence_link"

    UNKNOWN_EVIDENCE_ID = "unknown_evidence_id"

    NON_LITERAL_CLAIM_TEXT = "non_literal_claim_text"


@dataclass(
    frozen=True,
    slots=True,
)
class ClaimIntegrityIssue:
    issue_type: ClaimIntegrityIssueType

    claim_id: str

    evidence_ids: tuple[
        str,
        ...,
    ] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class ClaimIntegrityReport:
    """
    Deterministic literal/source-integrity result.

    PASS means only that each structured claim is
    traceable as literal text to one of its linked
    evidence nodes.

    It does NOT mean:
    - semantic entailment;
    - religious correctness;
    - factual correctness;
    - claim verification.
    """

    issues: tuple[
        ClaimIntegrityIssue,
        ...,
    ] = ()

    @property
    def passed(
        self,
    ) -> bool:
        return not self.issues


class ClaimIntegrityError(
    ValueError,
):
    def __init__(
        self,
        report: ClaimIntegrityReport,
    ) -> None:
        self.report = report

        issue_names = ", ".join(issue.issue_type.value for issue in report.issues)

        super().__init__("Claim/source integrity check failed: " + issue_names)


def _normalize_literal(
    text: str,
) -> str:
    return " ".join(text.split())


def _claim_literal_candidate(
    text: str,
) -> str:
    """
    Normalize a claim for literal traceability.

    Composer excerpts may end in a Unicode ellipsis
    when the source was safely truncated. The ellipsis
    itself is composer punctuation, so it is excluded
    from literal-source matching.
    """

    normalized = _normalize_literal(text)

    if normalized.endswith("…"):
        normalized = normalized[:-1].rstrip()

    return normalized


class ClaimSourceIntegrityVerifier:
    """
    Fail-closed deterministic provenance verifier.

    Every claim must:
    - have stable identifiers;
    - link to at least one selected evidence node;
    - contain only evidence IDs present in the supplied
      publication evidence set;
    - be a literal normalized excerpt of at least one
      linked evidence node.

    This verifier performs no semantic inference.
    """

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
    ) -> ClaimIntegrityReport:
        by_id = {node.evidence_id: node for node in evidence}

        seen_claim_ids: set[str] = set()

        issues: list[ClaimIntegrityIssue] = []

        for claim in claims:
            claim_id = claim.claim_id.strip()

            if not (claim.axis_id.strip()):
                issues.append(
                    ClaimIntegrityIssue(
                        issue_type=(ClaimIntegrityIssueType.EMPTY_AXIS_ID),
                        claim_id=claim_id,
                        evidence_ids=(claim.evidence_ids),
                    )
                )

            if not claim_id:
                issues.append(
                    ClaimIntegrityIssue(
                        issue_type=(ClaimIntegrityIssueType.EMPTY_CLAIM_ID),
                        claim_id="",
                        evidence_ids=(claim.evidence_ids),
                    )
                )

            elif claim_id in seen_claim_ids:
                issues.append(
                    ClaimIntegrityIssue(
                        issue_type=(ClaimIntegrityIssueType.DUPLICATE_CLAIM_ID),
                        claim_id=claim_id,
                        evidence_ids=(claim.evidence_ids),
                    )
                )

            else:
                seen_claim_ids.add(claim_id)

            candidate = _claim_literal_candidate(claim.text)

            if not candidate:
                issues.append(
                    ClaimIntegrityIssue(
                        issue_type=(ClaimIntegrityIssueType.EMPTY_CLAIM_TEXT),
                        claim_id=claim_id,
                        evidence_ids=(claim.evidence_ids),
                    )
                )

            if not claim.evidence_ids:
                issues.append(
                    ClaimIntegrityIssue(
                        issue_type=(ClaimIntegrityIssueType.MISSING_EVIDENCE_LINK),
                        claim_id=claim_id,
                    )
                )

                continue

            unknown_ids = tuple(
                evidence_id
                for evidence_id in claim.evidence_ids
                if evidence_id not in by_id
            )

            if unknown_ids:
                issues.append(
                    ClaimIntegrityIssue(
                        issue_type=(ClaimIntegrityIssueType.UNKNOWN_EVIDENCE_ID),
                        claim_id=claim_id,
                        evidence_ids=(unknown_ids),
                    )
                )

            linked_nodes = tuple(
                by_id[evidence_id]
                for evidence_id in claim.evidence_ids
                if evidence_id in by_id
            )

            if (
                candidate
                and linked_nodes
                and not any(
                    candidate in _normalize_literal(node.text) for node in linked_nodes
                )
            ):
                issues.append(
                    ClaimIntegrityIssue(
                        issue_type=(ClaimIntegrityIssueType.NON_LITERAL_CLAIM_TEXT),
                        claim_id=claim_id,
                        evidence_ids=(claim.evidence_ids),
                    )
                )

        return ClaimIntegrityReport(
            issues=tuple(issues),
        )

    def require_valid(
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
    ) -> ClaimIntegrityReport:
        report = self.verify(
            claims=claims,
            evidence=evidence,
        )

        if not report.passed:
            raise ClaimIntegrityError(report)

        return report
