from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.evidence.publication import (
    EvidencePublicationAuthorizer,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlan,
    RetrievalTarget,
)


class DomainRetrievalUnavailableError(RuntimeError):
    """
    Raised when a registered domain retriever exists
    but cannot safely retrieve from any authorized
    source for the requested domain.

    This is deliberately different from an empty
    successful retrieval.
    """

    def __init__(
        self,
        domain: EvidenceDomain,
    ) -> None:
        self.domain = domain

        super().__init__(f"Retrieval domain unavailable: {domain.value}")


class DomainRetriever(Protocol):
    def retrieve(
        self,
        *,
        understanding: (BasiraQueryUnderstanding),
        target: RetrievalTarget,
        limit: int = 10,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]: ...


@dataclass(
    frozen=True,
    slots=True,
)
class UnifiedRetrievalResult:
    plan: BasiraRetrievalPlan

    evidence: tuple[
        EvidenceNode,
        ...,
    ]

    unavailable_domains: frozenset[EvidenceDomain]

    @property
    def has_evidence(
        self,
    ) -> bool:
        return bool(self.evidence)


class BasiraUnifiedRetriever:
    """
    Execute a BasiraRetrievalPlan across registered
    domain retrievers.

    Missing domain implementations are surfaced
    explicitly. They are never silently treated as
    successful retrieval.
    """

    def __init__(
        self,
        retrievers: dict[
            EvidenceDomain,
            DomainRetriever,
        ],
        *,
        publication_authorizer: EvidencePublicationAuthorizer | None = None,
    ) -> None:
        self.retrievers = dict(retrievers)

        self.publication_authorizer = publication_authorizer

    def retrieve(
        self,
        plan: BasiraRetrievalPlan,
        *,
        limit_per_domain: int = 10,
    ) -> UnifiedRetrievalResult:
        evidence: list[EvidenceNode] = []

        unavailable: set[EvidenceDomain] = set()

        seen: set[str] = set()

        for target in plan.targets:
            retriever = self.retrievers.get(target.domain)

            if retriever is None:
                unavailable.add(target.domain)
                continue

            try:
                nodes = retriever.retrieve(
                    understanding=(plan.understanding),
                    target=target,
                    limit=limit_per_domain,
                )
            except DomainRetrievalUnavailableError:
                unavailable.add(target.domain)
                continue

            for node in nodes:
                if node.evidence_id in seen:
                    continue

                seen.add(node.evidence_id)

                evidence.append(node)

        return UnifiedRetrievalResult(
            plan=plan,
            evidence=tuple(evidence),
            unavailable_domains=(frozenset(unavailable)),
        )
