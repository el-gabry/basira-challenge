from __future__ import annotations

from basira.evidence.hadith_adapter import (
    HadithEvidenceAdapter,
)
from basira.evidence.models import (
    EvidenceNode,
)
from basira.retrieval.hadith_index import (
    HadithLocalIndex,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
)
from basira.retrieval.retrieval_plan import (
    RetrievalTarget,
)


def _entity_value(
    understanding: BasiraQueryUnderstanding,
    entity_type: str,
) -> str | None:
    for entity in understanding.entities:
        if entity.entity_type == entity_type:
            return entity.value

    return None


class HadithDomainRetriever:
    """
    Execute the Hadith portion of a Basira retrieval
    plan against the deterministic local index.

    default_collection_id is intentionally explicit.
    Basira must not assume collection numbering across
    unrelated sources.
    """

    def __init__(
        self,
        *,
        index: HadithLocalIndex,
        default_collection_id: (
            str | None
        ) = None,
        adapter: (
            HadithEvidenceAdapter | None
        ) = None,
    ) -> None:
        self.index = index

        self.default_collection_id = (
            default_collection_id
        )

        self.adapter = (
            adapter
            or HadithEvidenceAdapter()
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
        del target

        hadith_number = _entity_value(
            understanding,
            "hadith_number",
        )

        if (
            hadith_number is not None
            and self.default_collection_id
            is not None
        ):
            hits = (
                self.index
                .search_reference(
                    collection_id=(
                        self.default_collection_id
                    ),
                    hadith_number=(
                        hadith_number
                    ),
                    limit=limit,
                )
            )
        else:
            hits = (
                self.index.search_query(
                    understanding.query,
                    limit=limit,
                )
            )

        nodes: list[
            EvidenceNode
        ] = []

        seen: set[str] = set()

        for hit in hits:
            for node in (
                self.adapter.from_hit(
                    hit
                )
            ):
                if (
                    node.evidence_id
                    in seen
                ):
                    continue

                seen.add(
                    node.evidence_id
                )

                nodes.append(node)

        return tuple(nodes)
