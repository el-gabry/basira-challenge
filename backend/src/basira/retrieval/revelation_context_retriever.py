from __future__ import annotations

from basira.evidence.models import EvidenceNode
from basira.evidence.scholarly_adapter import (
    ScholarlyEvidenceAdapter,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
)
from basira.retrieval.quran_reference import (
    expand_quran_reference,
)
from basira.retrieval.retrieval_plan import (
    RetrievalTarget,
)
from basira.sources.scholarly.repository import (
    ScholarlyRepository,
)


def _entity_value(
    understanding: BasiraQueryUnderstanding,
    entity_type: str,
) -> str | None:
    for entity in understanding.entities:
        if entity.entity_type == entity_type:
            return entity.value

    return None


class RevelationContextRetriever:
    """
    Retrieve attributed revelation-context evidence
    from the trusted local scholarly repository.

    The corpus is intentionally sparse. An empty
    result does not by itself mean retrieval failure.
    """

    def __init__(
        self,
        *,
        repository: ScholarlyRepository,
        adapter: ScholarlyEvidenceAdapter | None = None,
    ) -> None:
        self.repository = repository
        self.adapter = adapter or ScholarlyEvidenceAdapter()

    def _passages_for_verified_references(
        self,
        references: tuple[str, ...],
    ) -> (
        tuple[
            ScholarlyPassage,
            ...,
        ]
        | None
    ):
        points: list[tuple[int, int]] = []

        seen_points: set[tuple[int, int]] = set()

        for reference in references:
            expanded = expand_quran_reference(reference)

            if expanded is None:
                return None

            for point in expanded:
                if point in seen_points:
                    continue

                seen_points.add(point)
                points.append(point)

        passages: list[ScholarlyPassage] = []

        seen_passages: set[str] = set()

        for surah, ayah in points:
            matches = self.repository.find_by_quran_reference(
                surah,
                ayah,
                domain=(ScholarlyDomain.REVELATION_CONTEXT),
            )

            for passage in matches:
                if passage.passage_id in seen_passages:
                    continue

                seen_passages.add(passage.passage_id)
                passages.append(passage)

        return tuple(passages)

    def retrieve(
        self,
        *,
        understanding: (BasiraQueryUnderstanding),
        target: RetrievalTarget,
        limit: int = 10,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        if limit <= 0:
            return ()

        if target.references:
            passages = self._passages_for_verified_references(target.references)

            # A malformed execution constraint must
            # never fall back to query re-parsing.
            if passages is None:
                return ()

            return tuple(
                self.adapter.from_passage(passage) for passage in passages[:limit]
            )

        surah_value = _entity_value(
            understanding,
            "surah_number",
        )

        ayah_value = _entity_value(
            understanding,
            "ayah_number",
        )

        if surah_value is None or ayah_value is None:
            return ()

        passages = self.repository.find_by_quran_reference(
            int(surah_value),
            int(ayah_value),
            domain=(ScholarlyDomain.REVELATION_CONTEXT),
        )

        return tuple(self.adapter.from_passage(passage) for passage in passages[:limit])
