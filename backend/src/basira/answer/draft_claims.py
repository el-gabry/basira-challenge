from __future__ import annotations

from typing import Protocol

from basira.answer.final_output import (
    FinalOutputDraft,
)
from basira.answer.models import (
    StructuredClaim,
)
from basira.evidence.models import (
    EvidenceNeed,
    EvidenceNode,
)


class DraftClaimGenerator(Protocol):
    """
    Generation boundary for answer claims.

    A generator may propose wording, but it owns no
    publication authority.

    Its FinalOutputDraft must pass the downstream
    FinalOutputVerifier before user-facing rendering.
    """

    def generate(
        self,
        *,
        question: str,
        primary_need: EvidenceNeed | None,
        evidence: tuple[
            EvidenceNode,
            ...,
        ],
    ) -> FinalOutputDraft: ...


class DeterministicClaimBuilder(Protocol):
    """
    Existing deterministic claim-building behavior.

    Kept as a callable boundary so the current composer
    remains byte-for-byte behaviorally authoritative
    during generator injection.
    """

    def __call__(
        self,
        *,
        primary_need: EvidenceNeed | None,
        nodes: tuple[
            EvidenceNode,
            ...,
        ],
    ) -> tuple[
        StructuredClaim,
        ...,
    ]: ...


class DeterministicDraftClaimGenerator:
    """
    Adapter around Basira's existing deterministic
    claim builder.

    It deliberately adds no paraphrasing and performs
    no semantic or publication decision.
    """

    def __init__(
        self,
        *,
        builder: DeterministicClaimBuilder,
    ) -> None:
        self._builder = builder

    def generate(
        self,
        *,
        question: str,
        primary_need: EvidenceNeed | None,
        evidence: tuple[
            EvidenceNode,
            ...,
        ],
    ) -> FinalOutputDraft:
        del question

        return FinalOutputDraft(
            claims=self._builder(
                primary_need=primary_need,
                nodes=evidence,
            )
        )
