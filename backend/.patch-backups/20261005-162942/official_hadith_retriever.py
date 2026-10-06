from __future__ import annotations

from typing import Protocol

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


class OfficialHadithEvidenceAdapter(Protocol):
    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[EvidenceNode, ...]: ...


_HADITH_QUERY_SCAFFOLDING = frozenset(
    {
        "هل",
        "حديث",
        "الحديث",
        "صحيح",
        "صحيحة",
        "صح",
        "ضعيف",
        "موضوع",
        "درجة",
        "درجه",
        "ما",
        "هو",
        "هذا",
        "هذه",
        "ده",
        "اشرح",
        "شرح",
        "معنى",
        "معني",
        "يوجد",
        "فيه",
        "ورد",
        "منسوب",
        "للنبي",
        "يقول",
    }
)


def _discovery_query(
    understanding: BasiraQueryUnderstanding,
) -> str:
    """
    Build a deterministic discovery query only.

    Removing question scaffolding does not establish
    Hadith identity, grading, or authority. Those remain
    exclusively source/policy derived.
    """

    tokens = understanding.query.search_text.split()

    meaningful = tuple(
        token
        for token in tokens
        if token not in _HADITH_QUERY_SCAFFOLDING
    )

    if meaningful:
        return " ".join(meaningful)

    search_text = understanding.query.search_text.strip()

    if search_text:
        return search_text

    return understanding.query.original_text.strip()


class OfficialHadithDomainRetriever:
    """
    Basira DomainRetriever backed exclusively by the
    admitted Dorar Hadith evidence lane.

    This adapter does not:
    - fall back to HadeethEnc/QuranLab;
    - infer authenticity;
    - normalize away attributed grading;
    - create religious authority.

    Dorar retrieval + OfficialHadithPolicy remain the
    evidentiary authority.
    """

    def __init__(
        self,
        *,
        adapter: OfficialHadithEvidenceAdapter,
        publication_ledger: GovernedPublicationLedger | None = None,
    ) -> None:
        self.adapter = adapter
        self.publication_ledger = publication_ledger

    def retrieve(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
        target: RetrievalTarget,
        limit: int = 10,
    ) -> tuple[EvidenceNode, ...]:
        if limit <= 0:
            return ()

        if target.domain is not EvidenceDomain.HADITH:
            raise ValueError(
                "OfficialHadithDomainRetriever requires a Hadith target."
            )

        references = tuple(
            dict.fromkeys(
                value.strip()
                for value in target.references
                if value.strip()
            )
        )

        # A projected identity is execution authority.
        # Do not widen it back into an unconstrained query.
        queries = references or (_discovery_query(understanding),)

        accepted: list[EvidenceNode] = []
        seen: set[str] = set()

        for query in queries:
            if not query:
                continue

            try:
                nodes = self.adapter.retrieve(
                    CompetitionRetrievalRequest(
                        official_domain=OfficialDomain.HADITH,
                        query=query,
                        limit=limit,
                        references=references,
                    )
                )
            except CompetitionRetrievalError as exc:
                raise DomainRetrievalUnavailableError(
                    EvidenceDomain.HADITH
                ) from exc

            for node in nodes:
                if node.domain is not EvidenceDomain.HADITH:
                    raise DomainRetrievalUnavailableError(
                        EvidenceDomain.HADITH
                    )

                if node.evidence_id in seen:
                    continue

                seen.add(node.evidence_id)

                if self.publication_ledger is not None:
                    self.publication_ledger.admit(node)

                accepted.append(node)

            # Discovery mode: once an admitted source result
            # exists, do not widen the search further.
            if accepted and not references:
                break

        return tuple(accepted)
