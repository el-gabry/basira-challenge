from __future__ import annotations

from collections.abc import Iterable

from basira.evidence.models import EvidenceNode
from basira.models.source_usage import RuntimeUse
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
)
from basira.retrieval.retrieval_plan import (
    RetrievalTarget,
)
from basira.retrieval.unified_retriever import (
    DomainRetrievalUnavailableError,
    DomainRetriever,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)


class GovernedScholarlyRetriever:
    """
    Fail-closed runtime boundary for scholarly
    retrievers.

    Authorization is evaluated against the configured
    source set before retrieval. This is important for
    sparse corpora: an authorized source with no row
    is a valid empty result, while an unauthorized
    source means the domain is unavailable.
    """

    def __init__(
        self,
        *,
        delegate: DomainRetriever,
        runtime: FailClosedSourceRuntime,
        source_ids: Iterable[str],
    ) -> None:
        normalized = tuple(
            dict.fromkeys(
                " ".join(source_id.split())
                for source_id in source_ids
                if " ".join(source_id.split())
            )
        )

        if not normalized:
            raise ValueError("At least one scholarly source id must be configured.")

        self.delegate = delegate
        self.runtime = runtime
        self.source_ids = normalized

    def retrieve(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
        target: RetrievalTarget,
        limit: int = 10,
    ) -> tuple[EvidenceNode, ...]:
        allowed_source_ids = frozenset(
            source_id
            for source_id in self.source_ids
            if self.runtime.allows(
                source_id=source_id,
                runtime_use=(RuntimeUse.RETRIEVE_PASSAGES),
            )
        )

        if not allowed_source_ids:
            raise DomainRetrievalUnavailableError(target.domain)

        nodes = self.delegate.retrieve(
            understanding=understanding,
            target=target,
            limit=limit,
        )

        return tuple(node for node in nodes if node.source_id in allowed_source_ids)
