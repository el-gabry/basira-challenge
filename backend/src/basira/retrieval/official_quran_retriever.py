from __future__ import annotations

import re
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
from basira.normalization.quran import (
    normalize_quran_search_text,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
)
from basira.retrieval.quran_reference import (
    expand_quran_reference,
    normalize_quran_reference,
)
from basira.retrieval.retrieval_plan import (
    RetrievalTarget,
)
from basira.retrieval.unified_retriever import (
    DomainRetrievalUnavailableError,
)
from basira.sources.quran.repository import (
    QuranRepository,
)

_QUERY_SCAFFOLDING = frozenset(
    {
        "ما",
        "ماذا",
        "معنى",
        "معني",
        "شرح",
        "تفسير",
        "اية",
        "آية",
        "الاية",
        "الآية",
        "سورة",
        "يعني",
        "تعني",
    }
)



_CONCEPTUAL_STOP_WORDS = frozenset(
    {
        "هل",
        "وهل",
        "ما",
        "ماذا",
        "في",
        "من",
        "عن",
        "علي",
        "على",
        "الي",
        "إلى",
        "القران",
        "القرآن",
        "اية",
        "آية",
        "الاية",
        "الآية",
        "امر",
        "أمر",
        "قال",
        "ذكر",
    }
)

_LIGHT_PREFIXES = (
    "وال",
    "فال",
    "بال",
    "كال",
    "لل",
    "ال",
    "و",
    "ف",
    "ب",
)

_LIGHT_SUFFIXES = (
    "ات",
    "ون",
    "ين",
    "وا",
    "ة",
)


def _light_arabic_variants(
    token: str,
) -> tuple[str, ...]:
    """
    Bounded query-side lexical variants only.

    This is NOT Quran identity resolution and NOT
    evidence generation. It only broadens discovery
    inside the already-canonical Quran repository.
    """

    normalized = normalize_quran_search_text(
        token
    )

    if len(normalized) < 4:
        return ()

    seen = {
        normalized,
    }

    frontier = [
        normalized,
    ]

    # Three bounded transformation rounds are enough
    # for clitic + derivational forms such as:
    #
    # بالمحافظة -> محافظة -> محافظ -> حافظ
    #
    # No Quran reference is ever inferred here.
    for _ in range(3):
        next_frontier: list[str] = []

        for value in frontier:
            for prefix in _LIGHT_PREFIXES:
                if (
                    value.startswith(prefix)
                    and len(value) - len(prefix) >= 4
                ):
                    candidate = value[
                        len(prefix):
                    ]

                    if candidate not in seen:
                        seen.add(candidate)
                        next_frontier.append(
                            candidate
                        )

            for suffix in _LIGHT_SUFFIXES:
                if (
                    value.endswith(suffix)
                    and len(value) - len(suffix) >= 4
                ):
                    candidate = value[
                        : -len(suffix)
                    ]

                    if candidate not in seen:
                        seen.add(candidate)
                        next_frontier.append(
                            candidate
                        )

            # Common Arabic derived-noun prefix.
            # Keep this deliberately conservative:
            # only remove م after at least one other
            # normalization step has produced a long
            # enough token.
            if (
                value.startswith("م")
                and len(value) >= 5
                and value != normalized
            ):
                candidate = value[1:]

                if (
                    len(candidate) >= 4
                    and candidate not in seen
                ):
                    seen.add(candidate)
                    next_frontier.append(
                        candidate
                    )

        if not next_frontier:
            break

        frontier = next_frontier

    return tuple(
        sorted(
            seen,
            key=lambda item: (
                -len(item),
                item,
            ),
        )
    )


def _conceptual_term_groups(
    understanding: BasiraQueryUnderstanding,
) -> tuple[
    tuple[str, ...],
    ...,
]:
    tokens = re.findall(
        r"[\u0600-\u06ff]+",
        understanding.query.original_text,
    )

    groups: list[
        tuple[str, ...]
    ] = []

    seen_groups: set[
        tuple[str, ...]
    ] = set()

    for token in tokens:
        normalized = (
            normalize_quran_search_text(
                token
            )
        )

        if (
            len(normalized) < 3
            or normalized
            in _CONCEPTUAL_STOP_WORDS
        ):
            continue

        variants = (
            _light_arabic_variants(
                normalized
            )
        )

        if not variants:
            continue

        if variants in seen_groups:
            continue

        seen_groups.add(variants)
        groups.append(variants)

    return tuple(groups)


def _rank_conceptual_quran_points(
    *,
    understanding: BasiraQueryUnderstanding,
    repository: QuranRepository,
    limit: int,
) -> tuple[
    tuple[int, int],
    ...,
]:
    """
    Rank canonical verses by independent lexical
    concept coverage.

    Fuzzy matching is discovery-only. Returned values
    are canonical repository coordinates.
    """

    if limit <= 0:
        return ()

    groups = _conceptual_term_groups(
        understanding
    )

    if not groups:
        return ()

    scored: list[
        tuple[
            int,
            int,
            int,
        ]
    ] = []

    for verse in repository.all():
        verse_text = (
            normalize_quran_search_text(
                verse.text_search
            )
        )

        matched_groups = 0

        for variants in groups:
            if any(
                variant in verse_text
                for variant in variants
                if len(variant) >= 4
            ):
                matched_groups += 1

        if matched_groups == 0:
            continue

        scored.append(
            (
                matched_groups,
                verse.surah_number,
                verse.ayah_number,
            )
        )

    if not scored:
        return ()

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1],
            item[2],
        )
    )

    best_score = scored[0][0]

    # When multiple independent semantic terms exist,
    # require at least two to avoid broad single-word
    # Quran matches such as every verse containing
    # "الصلاة".
    minimum_score = (
        2
        if len(groups) >= 2
        else 1
    )

    if best_score < minimum_score:
        return ()

    return tuple(
        (
            surah,
            ayah,
        )
        for score, surah, ayah in scored
        if score == best_score
    )[:limit]


class OfficialQuranEvidenceAdapter(Protocol):
    @property
    def repository(
        self,
    ) -> QuranRepository: ...

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]: ...


def _search_candidates(
    understanding: BasiraQueryUnderstanding,
) -> tuple[str, ...]:
    """
    Deterministic discovery hints only.

    These are used only when no verified execution
    reference was projected onto the target.
    """

    values = [
        understanding.query.original_text,
        understanding.query.intent_text,
    ]

    meaningful_tokens = [
        token
        for token in (understanding.query.intent_text.split())
        if (
            token not in _QUERY_SCAFFOLDING
            and not any(character.isdigit() for character in token)
        )
    ]

    if meaningful_tokens:
        values.append(" ".join(meaningful_tokens))

    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = " ".join(value.split())

        if not cleaned or cleaned in seen:
            continue

        seen.add(cleaned)
        result.append(cleaned)

    return tuple(result)


class OfficialQuranDomainRetriever:
    """
    Basira DomainRetriever backed by the governed
    Quranpedia evidence adapter.

    Final execution spine:

        GovernedCapabilityExecutor
          -> BasiraUnifiedRetriever
          -> OfficialQuranDomainRetriever
          -> Quranpedia governed adapter

    Verified target.references are execution identity,
    never merely search hints.
    """

    def __init__(
        self,
        *,
        adapter: OfficialQuranEvidenceAdapter,
        publication_ledger: GovernedPublicationLedger | None = None,
    ) -> None:
        self.adapter = adapter

        self.publication_ledger = publication_ledger

        # Intentionally expose the same governed
        # repository to the existing canonical resolver.
        #
        # Reading this property also forces Quranpedia
        # passport/manifest/snapshot admission.
        self.repository = adapter.repository

    def _retrieve_exact_point(
        self,
        *,
        surah: int,
        ayah: int,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        reference = f"{surah}:{ayah}"

        try:
            nodes = self.adapter.retrieve(
                CompetitionRetrievalRequest(
                    official_domain=(OfficialDomain.QURAN),
                    query=reference,
                    limit=1,
                    references=(reference,),
                )
            )
        except CompetitionRetrievalError as exc:
            raise (DomainRetrievalUnavailableError(EvidenceDomain.QURAN)) from exc

        accepted: list[EvidenceNode] = []

        for node in nodes:
            if node.domain is not EvidenceDomain.QURAN:
                raise (DomainRetrievalUnavailableError(EvidenceDomain.QURAN))

            node_reference = normalize_quran_reference(node.reference or "")

            if node_reference != reference:
                raise (DomainRetrievalUnavailableError(EvidenceDomain.QURAN))

            if self.publication_ledger is not None:
                self.publication_ledger.admit(node)

            accepted.append(node)

        return tuple(accepted)

    def retrieve(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
        target: RetrievalTarget,
        limit: int = 10,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        if limit <= 0:
            return ()

        if target.domain is not EvidenceDomain.QURAN:
            raise ValueError("OfficialQuranDomainRetriever requires a Quran target.")

        # ------------------------------------------------
        # Hard execution identity wins.
        # ------------------------------------------------

        if target.references:
            points: list[tuple[int, int]] = []

            seen_points: set[tuple[int, int]] = set()

            for value in target.references:
                expanded = expand_quran_reference(value)

                # Invalid projected execution identity
                # fails closed. Never reinterpret it
                # through the user question.
                if expanded is None:
                    return ()

                for point in expanded:
                    if point in seen_points:
                        continue

                    seen_points.add(point)
                    points.append(point)

            evidence: list[EvidenceNode] = []

            seen_evidence: set[str] = set()

            for surah, ayah in points:
                nodes = self._retrieve_exact_point(
                    surah=surah,
                    ayah=ayah,
                )

                for node in nodes:
                    if node.evidence_id in seen_evidence:
                        continue

                    seen_evidence.add(node.evidence_id)
                    evidence.append(node)

                    if len(evidence) >= limit:
                        return tuple(evidence)

            return tuple(evidence)

        # ------------------------------------------------
        # No hard anchor: deterministic discovery only.
        # ------------------------------------------------

        evidence: list[EvidenceNode] = []

        seen_evidence: set[str] = set()

        for query in _search_candidates(understanding):
            try:
                nodes = self.adapter.retrieve(
                    CompetitionRetrievalRequest(
                        official_domain=(OfficialDomain.QURAN),
                        query=query,
                        limit=limit,
                    )
                )
            except CompetitionRetrievalError as exc:
                raise (DomainRetrievalUnavailableError(EvidenceDomain.QURAN)) from exc

            for node in nodes:
                if node.domain is not EvidenceDomain.QURAN:
                    raise (DomainRetrievalUnavailableError(EvidenceDomain.QURAN))

                if node.evidence_id in seen_evidence:
                    continue

                seen_evidence.add(node.evidence_id)
                if self.publication_ledger is not None:
                    self.publication_ledger.admit(node)

                evidence.append(node)

                if len(evidence) >= limit:
                    return tuple(evidence)

            if evidence:
                break

        if evidence:
            return tuple(evidence)

        # ------------------------------------------------
        # Conceptual lexical fallback.
        #
        # The ranking step discovers only canonical
        # repository coordinates. Every selected point
        # is then fetched again through the governed
        # exact-point adapter so publication admission,
        # provenance and identity checks remain intact.
        # ------------------------------------------------

        points = _rank_conceptual_quran_points(
            understanding=understanding,
            repository=self.repository,
            limit=limit,
        )

        for surah, ayah in points:
            nodes = self._retrieve_exact_point(
                surah=surah,
                ayah=ayah,
            )

            for node in nodes:
                if node.evidence_id in seen_evidence:
                    continue

                seen_evidence.add(
                    node.evidence_id
                )
                evidence.append(node)

                if len(evidence) >= limit:
                    return tuple(evidence)

        return tuple(evidence)
