from __future__ import annotations

from collections.abc import Iterable

from basira.evidence.models import (
    EvidenceNode,
)
from basira.evidence.scholarly_adapter import (
    ScholarlyEvidenceAdapter,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.retrieval.atomic_query import (
    plan_atomic_queries,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
)
from basira.retrieval.quran_reference import (
    expand_quran_reference,
)
from basira.retrieval.retrieval_plan import (
    RetrievalStrategy,
    RetrievalTarget,
)
from basira.retrieval.scholarly_lexical import (
    ScholarlyLexicalIndex,
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


class TafsirDomainRetriever:
    """
    Retrieve Tafsir evidence from the trusted local
    scholarly repository.

    Retrieval order is intentionally asymmetric:

    1. A deterministic Quran anchor always wins.
    2. Lexical conceptual retrieval is permitted only
       when the plan explicitly requests it.
    3. No dense/semantic fallback is implemented here.

    The original scholarly passage remains the
    evidence object; lexical indexing never rewrites
    source text or provenance.
    """

    def __init__(
        self,
        *,
        repository: ScholarlyRepository,
        source_ids: (Iterable[str] | None) = None,
        adapter: (ScholarlyEvidenceAdapter | None) = None,
    ) -> None:
        self.repository = repository

        self.adapter = adapter or ScholarlyEvidenceAdapter()

        if source_ids is None:
            self.source_ids = None
        else:
            self.source_ids = frozenset(
                source_id.strip() for source_id in source_ids if source_id.strip()
            )

        self._lexical_index: ScholarlyLexicalIndex | None = None

    def _allowed_passages(
        self,
        passages: Iterable[ScholarlyPassage],
    ) -> tuple[
        ScholarlyPassage,
        ...,
    ]:
        if self.source_ids is None:
            return tuple(passages)

        return tuple(
            passage for passage in passages if passage.source_id in self.source_ids
        )

    def _conceptual_index(
        self,
    ) -> ScholarlyLexicalIndex:
        if self._lexical_index is None:
            passages = self.repository.find_by_domain(ScholarlyDomain.TAFSIR)

            self._lexical_index = ScholarlyLexicalIndex(
                self._allowed_passages(passages)
            )

        return self._lexical_index

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
                domain=(ScholarlyDomain.TAFSIR),
            )

            for passage in matches:
                if passage.passage_id in seen_passages:
                    continue

                seen_passages.add(passage.passage_id)
                passages.append(passage)

        return self._allowed_passages(passages)

    def _rank_from_index(
        self,
        *,
        index: ScholarlyLexicalIndex,
        understanding: (BasiraQueryUnderstanding),
        limit: int,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        query = understanding.query.search_text.strip()

        if not query:
            return ()

        atomic_plan = plan_atomic_queries(understanding.query.original_text)

        search_queries = (
            query,
            *(
                atomic_query.search_text
                for atomic_query in atomic_plan.atomic_queries
                if (
                    atomic_query.search_text.strip()
                    and atomic_query.search_text.strip() != query
                )
            ),
        )

        hit_groups = tuple(
            index.search(
                search_query,
                limit=limit,
            )
            for search_query in search_queries
        )

        node_groups = tuple(
            tuple(self.adapter.from_passage(hit.passage) for hit in hits)
            for hits in hit_groups
        )

        rrf_k = 60

        original_group = node_groups[0] if node_groups else ()

        locked: list[EvidenceNode] = []

        if original_group:
            locked.append(original_group[0])

        locked_ids = {node.evidence_id for node in locked}

        scores: dict[
            str,
            float,
        ] = {}

        nodes_by_id: dict[
            str,
            EvidenceNode,
        ] = {}

        original_rank: dict[
            str,
            int,
        ] = {}

        for (
            group_index,
            group,
        ) in enumerate(node_groups):
            for rank, node in enumerate(
                group,
                start=1,
            ):
                evidence_id = node.evidence_id

                if evidence_id in locked_ids:
                    continue

                nodes_by_id.setdefault(
                    evidence_id,
                    node,
                )

                scores[evidence_id] = scores.get(
                    evidence_id,
                    0.0,
                ) + 1.0 / (rrf_k + rank)

                if group_index == 0:
                    original_rank.setdefault(
                        evidence_id,
                        rank,
                    )

        ranked_ids = sorted(
            scores,
            key=lambda evidence_id: (
                -scores[evidence_id],
                original_rank.get(
                    evidence_id,
                    10**9,
                ),
                evidence_id,
            ),
        )

        remaining = limit - len(locked)

        return tuple(
            (
                *locked,
                *(nodes_by_id[evidence_id] for evidence_id in ranked_ids[:remaining]),
            )
        )

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

        # Contract-projected references are execution
        # constraints, not query hints. They therefore
        # take precedence over re-parsing the user text.
        if target.references:
            passages = self._passages_for_verified_references(target.references)

            # Invalid execution references fail closed.
            # Never fall back to user-query entities.
            if passages is None:
                return ()

            if not passages:
                return ()

            # HYBRID behavior:
            # lock retrieval to the verified Quran
            # parent scope, then use lexical relevance
            # only to ORDER material inside that scope.
            #
            # Unmatched anchored sources remain present
            # after ranked hits so lexical matching
            # cannot silently destroy source diversity.
            if RetrievalStrategy.LEXICAL_FALLBACK in target.strategies:
                ranked = self._rank_from_index(
                    index=(ScholarlyLexicalIndex(passages)),
                    understanding=(understanding),
                    limit=limit,
                )

                if ranked:
                    ranked_ids = {node.evidence_id for node in ranked}

                    remainder = tuple(
                        self.adapter.from_passage(passage)
                        for passage in passages
                        if (passage.passage_id not in ranked_ids)
                    )

                    return tuple(
                        (
                            *ranked,
                            *remainder,
                        )[:limit]
                    )

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

        # Backward-compatible baseline behavior for
        # plans that do not carry a verified reference.
        if surah_value is not None and ayah_value is not None:
            passages = self.repository.find_by_quran_reference(
                int(surah_value),
                int(ayah_value),
                domain=(ScholarlyDomain.TAFSIR),
            )

            passages = self._allowed_passages(passages)

            return tuple(
                self.adapter.from_passage(passage) for passage in passages[:limit]
            )

        if RetrievalStrategy.LEXICAL_FALLBACK not in target.strategies:
            return ()

        return self._rank_from_index(
            index=self._conceptual_index(),
            understanding=understanding,
            limit=limit,
        )
