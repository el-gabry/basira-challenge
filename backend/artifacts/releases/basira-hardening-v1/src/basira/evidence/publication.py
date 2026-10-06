from __future__ import annotations

from dataclasses import fields
from typing import Protocol

from basira.evidence.models import (
    EvidenceNode,
)


class EvidencePublicationAuthorizer(Protocol):
    def get_admitted(
        self,
        evidence_id: str,
    ) -> EvidenceNode | None:
        """
        Return only evidence that already received a governed
        publication capability.

        This does not perform source retrieval and cannot
        discover unpublished evidence.
        """

        cleaned = evidence_id.strip()

        if not cleaned:
            return None

        return self._admitted.get(cleaned)

    def may_publish(
        self,
        node: EvidenceNode,
    ) -> bool: ...


def _normalized_text(
    value: str,
) -> str:
    return " ".join(value.split())


def _same_admitted_identity(
    *,
    admitted: EvidenceNode,
    candidate: EvidenceNode,
) -> bool:
    """
    Preserve every admitted field except the evidence
    text itself.

    Public runtime may replace Tafsir text only with an
    exact source-faithful excerpt. No provenance field
    may change during that projection.
    """

    for field in fields(EvidenceNode):
        name = field.name

        if name in {
            "text",
            "claim_type",
        }:
            continue

        if getattr(
            admitted,
            name,
        ) != getattr(
            candidate,
            name,
        ):
            return False

    # Semantic role is part of governed evidence identity.
    #
    # A derived projection may narrow presentation text,
    # but it may never acquire a new or stronger role.
    return candidate.claim_type == admitted.claim_type


class GovernedPublicationLedger:
    """
    In-memory publication capability issued only after
    evidence passes an official governed source lane.

    A source_id is never sufficient publication proof.
    """

    def __init__(
        self,
    ) -> None:
        self._admitted: dict[
            str,
            EvidenceNode,
        ] = {}

    def admit(
        self,
        node: EvidenceNode,
    ) -> EvidenceNode:
        existing = self._admitted.get(node.evidence_id)

        if existing is not None and existing != node:
            raise ValueError(f"publication evidence_id collision: {node.evidence_id}")

        self._admitted[node.evidence_id] = node

        return node

    def get_admitted(
        self,
        evidence_id: str,
    ) -> EvidenceNode | None:
        """
        Return only evidence already admitted through the
        governed publication lane.

        This is a read-only capability lookup. It performs
        no retrieval and cannot admit new evidence.
        """

        cleaned = evidence_id.strip()

        if not cleaned:
            return None

        return self._admitted.get(cleaned)

    def may_publish(
        self,
        node: EvidenceNode,
    ) -> bool:
        admitted = self._admitted.get(node.evidence_id)

        if admitted is None:
            return False

        if not _same_admitted_identity(
            admitted=admitted,
            candidate=node,
        ):
            return False

        admitted_text = _normalized_text(admitted.text)

        candidate_text = _normalized_text(node.text)

        if not admitted_text or not candidate_text:
            return False

        # Exact admitted text is publishable.
        if candidate_text == admitted_text:
            return True

        # Governed semantic focus is allowed only when
        # it is still an exact substring of the admitted
        # source text.
        return candidate_text in admitted_text
