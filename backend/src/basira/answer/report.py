from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.answer.integrity import (
    ClaimSourceIntegrityVerifier,
)
from basira.answer.models import (
    StructuredClaim,
)
from basira.evidence.bundle import (
    EvidenceConflict,
)
from basira.evidence.models import (
    EvidenceNode,
)


class LiteralSourceIntegrityState(StrEnum):
    PASSED = "passed"

    NOT_APPLICABLE = "not_applicable"


@dataclass(
    frozen=True,
    slots=True,
)
class AnswerIntegrityReport:
    """
    Deterministic transparency report.

    literal_source_integrity:
        Whether published structured claims passed
        Basira's literal/source traceability check.

    This report does NOT represent semantic entailment,
    factual correctness, religious correctness, or
    semantic claim verification.
    """

    literal_source_integrity: LiteralSourceIntegrityState

    claims_checked: int

    claim_ids: tuple[
        str,
        ...,
    ]

    linked_evidence_ids: tuple[
        str,
        ...,
    ]

    has_limitations: bool

    limitation_count: int

    potential_source_conflict: bool

    conflict_count: int

    conflict_types: tuple[
        str,
        ...,
    ]

    conflict_group_ids: tuple[
        str,
        ...,
    ]

    semantic_claim_verification: str = "not_enabled"

    semantic_verification_issues: tuple[
        str,
        ...,
    ] = ()


class AnswerIntegrityReportBuilder:
    """
    Build a deterministic report from already-composed
    answer artifacts.

    When claims exist, literal/source integrity is
    checked again against only the evidence actually
    selected for the published answer.

    This is defense in depth at the presentation
    boundary; it is not a semantic verifier.
    """

    def __init__(
        self,
    ) -> None:
        self.claim_verifier = ClaimSourceIntegrityVerifier()

    def build(
        self,
        *,
        claims: tuple[
            StructuredClaim,
            ...,
        ],
        used_evidence_ids: tuple[
            str,
            ...,
        ],
        evidence: tuple[
            EvidenceNode,
            ...,
        ],
        limitations: tuple[
            str,
            ...,
        ],
        conflicts: tuple[
            EvidenceConflict,
            ...,
        ],
        semantic_claim_verification: str = ("not_enabled"),
        semantic_verification_issues: tuple[
            str,
            ...,
        ] = (),
    ) -> AnswerIntegrityReport:
        used_ids = frozenset(used_evidence_ids)

        if claims:
            publication_evidence = tuple(
                node for node in evidence if node.evidence_id in used_ids
            )

            self.claim_verifier.require_valid(
                claims=claims,
                evidence=(publication_evidence),
            )

            literal_state = LiteralSourceIntegrityState.PASSED

        else:
            literal_state = LiteralSourceIntegrityState.NOT_APPLICABLE

        linked_ids: list[str] = []
        seen_ids: set[str] = set()

        for claim in claims:
            for evidence_id in claim.evidence_ids:
                if evidence_id in seen_ids:
                    continue

                seen_ids.add(evidence_id)

                linked_ids.append(evidence_id)

        conflict_types: list[str] = []
        conflict_groups: list[str] = []

        seen_types: set[str] = set()
        seen_groups: set[str] = set()

        for conflict in conflicts:
            conflict_type = conflict.conflict_type.value

            if conflict_type not in (seen_types):
                seen_types.add(conflict_type)

                conflict_types.append(conflict_type)

            if conflict.group_id not in seen_groups:
                seen_groups.add(conflict.group_id)

                conflict_groups.append(conflict.group_id)

        return AnswerIntegrityReport(
            literal_source_integrity=(literal_state),
            semantic_claim_verification=(semantic_claim_verification),
            semantic_verification_issues=(semantic_verification_issues),
            claims_checked=len(claims),
            claim_ids=tuple(claim.claim_id for claim in claims),
            linked_evidence_ids=tuple(linked_ids),
            has_limitations=bool(limitations),
            limitation_count=len(limitations),
            potential_source_conflict=bool(conflicts),
            conflict_count=len(conflicts),
            conflict_types=tuple(conflict_types),
            conflict_group_ids=tuple(conflict_groups),
        )
