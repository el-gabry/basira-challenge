from __future__ import annotations

import re

from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalError,
    CompetitionRetrievalRequest,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.evidence.publication import (
    GovernedPublicationLedger,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
)
from basira.retrieval.retrieval_plan import (
    RetrievalTarget,
)
from basira.retrieval.unified_retriever import (
    DomainRetrievalUnavailableError,
)


def _is_english_fiqh_query(
    query: str,
) -> bool:
    """
    Source-language routing only.

    It never chooses authority, ruling,
    madhhab, or tarjih.
    """

    has_arabic = bool(
        re.search(
            r"[\u0600-\u06ff]",
            query,
        )
    )

    has_latin = bool(
        re.search(
            r"[A-Za-z]",
            query,
        )
    )

    return (
        has_latin
        and not has_arabic
    )


class OfficialFiqhEvidenceAdapterProtocol:
    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        raise NotImplementedError


class OfficialFiqhDomainRetriever:
    """
    Public Fiqh retrieval backed by the admitted
    Dorar Fiqh lane.

    This is deliberately separate from governed
    Shamela-book retrieval.

    Dorar authority comes from the competition's
    explicit source allowance plus runtime identity/
    integrity admission.

    Shamela books remain book-by-book fail-closed.
    """

    def __init__(
        self,
        *,
        adapter: (
            OfficialFiqhEvidenceAdapterProtocol
        ),
        english_adapter: (
            OfficialFiqhEvidenceAdapterProtocol
            | None
        ) = None,
        publication_ledger: (
            GovernedPublicationLedger
            | None
        ) = None,
    ) -> None:
        self.adapter = adapter
        self.english_adapter = english_adapter

        self.publication_ledger = (
            publication_ledger
        )

    def retrieve(
        self,
        *,
        understanding: (
            BasiraQueryUnderstanding
        ),
        target: RetrievalTarget,
        limit: int = 10,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        if limit <= 0:
            return ()

        if (
            target.domain
            is not EvidenceDomain.FIQH
        ):
            raise ValueError(
                "OfficialFiqhDomainRetriever "
                "requires a Fiqh target."
            )

        query = (
            understanding.query.search_text.strip()
            or
            understanding.query.original_text.strip()
        )

        if not query:
            return ()

        adapter = self.adapter

        if (
            self.english_adapter
            is not None
            and _is_english_fiqh_query(
                query
            )
        ):
            adapter = self.english_adapter

        try:
            raw_nodes = (
                adapter.retrieve(
                    CompetitionRetrievalRequest(
                        official_domain=(
                            OfficialDomain
                            .GENERAL_FIQH
                        ),
                        query=query,
                        limit=limit,
                        references=tuple(
                            target.references
                        ),
                    )
                )
            )
        except CompetitionRetrievalError as exc:
            raise (
                DomainRetrievalUnavailableError(
                    EvidenceDomain.FIQH
                )
            ) from exc

        accepted: list[
            EvidenceNode
        ] = []

        seen: set[str] = set()

        for node in raw_nodes:
            if (
                node.domain
                is not EvidenceDomain.FIQH
            ):
                raise (
                    DomainRetrievalUnavailableError(
                        EvidenceDomain.FIQH
                    )
                )

            if node.evidence_id in seen:
                continue

            seen.add(
                node.evidence_id
            )

            if (
                self.publication_ledger
                is not None
            ):
                self.publication_ledger.admit(
                    node
                )

            accepted.append(node)

        return tuple(accepted)
