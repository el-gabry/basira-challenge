from __future__ import annotations

from dataclasses import dataclass

from basira.evidence.decision import (
    EvidenceDecisionAction,
)
from basira.evidence.expert_review import (
    ExpertReviewPacket,
)
from basira.evidence.models import (
    EvidenceDomain,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AnswerCitation:
    """
    Resolvable user-facing citation.

    evidence_id is the stable link back to the exact
    EvidenceNode used by the composer.
    """

    marker: str

    evidence_id: str

    domain: EvidenceDomain

    source_id: str

    source_version: str | None = None

    reference: str | None = None

    source_url: str | None = None

    work_title: str | None = None

    author_name: str | None = None

    institution: str | None = None

    publisher: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class StructuredClaim:
    """
    One user-facing answer unit with explicit
    provenance links.

    evidence_ids identify the evidence nodes attached
    to this claim.

    IMPORTANT:
    This relationship is provenance/traceability only.
    It does NOT assert semantic entailment or verified
    claim support. Semantic claim verification is a
    later pipeline stage.
    """

    axis_id: str

    claim_id: str

    text: str

    evidence_ids: tuple[
        str,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class GroundedAnswer:
    """
    Answer-composition result after the deterministic
    evidence decision layer.

    A substantive answer is optional. RETRIEVE_MORE,
    ABSTAIN, and ESCALATE_TO_EXPERT deliberately
    produce no autonomous substantive answer.
    """

    question: str

    action: EvidenceDecisionAction

    answer: str | None

    citations: tuple[
        AnswerCitation,
        ...,
    ]

    limitations: tuple[
        str,
        ...,
    ]

    evidence_coverage: float

    resolution_coverage: float

    used_evidence_ids: tuple[
        str,
        ...,
    ]

    claims: tuple[
        StructuredClaim,
        ...,
    ] = ()

    semantic_claim_verification: str = "not_enabled"

    semantic_verification_issues: tuple[
        str,
        ...,
    ] = ()

    expert_review: ExpertReviewPacket | None = None

    @property
    def has_answer(self) -> bool:
        return bool(self.answer and self.answer.strip())
