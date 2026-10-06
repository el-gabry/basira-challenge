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
from basira.retrieval.retrieval_plan import (
    RetrievalTarget,
)
from basira.retrieval.unified_retriever import (
    DomainRetrievalUnavailableError,
)
from basira.sources.quran.repository import (
    QuranRepository,
)

_POINT_REFERENCE = re.compile(r"^\s*(\d{1,3}):(\d{1,3})\s*$")


class OfficialTafsirEvidenceAdapter(Protocol):
    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]: ...


def _point_from_reference(
    value: str,
) -> tuple[int, int] | None:
    """
    Resolve only an exact Quran point for discovery
    focus generation.

    Non-point constraints are deliberately left intact
    and still travel unchanged as hard references.
    """

    match = _POINT_REFERENCE.fullmatch(value)

    if match is None:
        return None

    return (
        int(match.group(1)),
        int(match.group(2)),
    )


def _longest_canonical_overlap(
    *,
    question: str,
    verse_text: str,
) -> str | None:
    """
    Deterministic retrieval hint only.

    Find the longest contiguous phrase that already
    exists in BOTH:
      - the user's question
      - the verified canonical Quran verse

    This function never creates or changes authority.
    """

    question_text = normalize_quran_search_text(question)

    verse = normalize_quran_search_text(verse_text)

    question_tokens = question_text.split()

    # Require at least three words.
    # Short generic religious phrases should not become
    # accidental discovery authority.
    for size in range(
        len(question_tokens),
        2,
        -1,
    ):
        for offset in range(len(question_tokens) - size + 1):
            candidate = " ".join(question_tokens[offset : offset + size])

            if candidate in verse:
                return candidate

    return None


_VERIFIED_TAFSIR_DISCOVERY_HINTS = {
    # Discovery only.
    #
    # Identity and authority remain the verified
    # canonical Quran reference carried separately
    # in target.references.
    #
    "2:255": "وسع كرسيه",
}


def _anchored_discovery_phrase(
    *,
    understanding: BasiraQueryUnderstanding,
    references: tuple[str, ...],
    repository: QuranRepository,
) -> str | None:
    """
    Hard Quran identity -> source-faithful Tafsir
    discovery query.

    Priority:
      1. literal overlap between question and Quran;
      2. explicitly verified discovery hint.

    A discovery hint is accepted only when it is
    itself present in the canonically anchored verse.

    target.references remains the hard identity.
    """

    for reference in references:
        point = _point_from_reference(reference)

        if point is None:
            continue

        surah, ayah = point

        verse = repository.get(
            surah,
            ayah,
        )

        if verse is None:
            continue

        phrase = _longest_canonical_overlap(
            question=(understanding.query.original_text),
            verse_text=(verse.text_search),
        )

        if phrase:
            return phrase

        hint = _VERIFIED_TAFSIR_DISCOVERY_HINTS.get(reference)

        if hint is None:
            continue

        canonical_hint = normalize_quran_search_text(hint)

        canonical_verse = normalize_quran_search_text(verse.text_search)

        if canonical_hint and canonical_hint in canonical_verse:
            return canonical_hint

    return None


def _fallback_discovery_query(
    understanding: BasiraQueryUnderstanding,
) -> str:
    """
    Deterministic fallback search strategy.

    Crucially, this affects only discovery text.
    target.references remains the hard identity.
    """

    search_text = understanding.query.search_text.strip()

    if search_text:
        return search_text

    return understanding.query.original_text.strip()


class OfficialTafsirDomainRetriever:
    """
    Basira DomainRetriever backed by the governed
    official Tafsir evidence adapter.

    Final execution spine:

        GovernedCapabilityExecutor
          -> BasiraUnifiedRetriever
          -> OfficialTafsirDomainRetriever
          -> governed Tafsir source adapter

    No second retrieval orchestrator is introduced.
    """

    def __init__(
        self,
        *,
        adapter: OfficialTafsirEvidenceAdapter,
        quran_repository: QuranRepository,
        publication_ledger: GovernedPublicationLedger | None = None,
    ) -> None:
        self.adapter = adapter

        self.quran_repository = quran_repository

        self.publication_ledger = publication_ledger

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

        if target.domain is not EvidenceDomain.TAFSIR:
            raise ValueError("OfficialTafsirDomainRetriever requires a Tafsir target.")

        references = tuple(
            dict.fromkeys(value.strip() for value in target.references if value.strip())
        )

        if references:
            query = _anchored_discovery_phrase(
                understanding=understanding,
                references=references,
                repository=(self.quran_repository),
            ) or _fallback_discovery_query(understanding)
        else:
            query = _fallback_discovery_query(understanding)

        if not query:
            return ()

        try:
            nodes = self.adapter.retrieve(
                CompetitionRetrievalRequest(
                    official_domain=(OfficialDomain.TAFSIR),
                    query=query,
                    # One accepted passage.
                    #
                    # Dorar source acquisition itself
                    # may inspect up to three search
                    # candidates before returning the
                    # first structurally-valid passage.
                    limit=(1 if references else limit),
                    references=references,
                )
            )
        except CompetitionRetrievalError as exc:
            raise (DomainRetrievalUnavailableError(EvidenceDomain.TAFSIR)) from exc

        accepted: list[EvidenceNode] = []

        for node in nodes:
            if node.domain is not EvidenceDomain.TAFSIR:
                raise (DomainRetrievalUnavailableError(EvidenceDomain.TAFSIR))

            if references:
                coverage = set(node.related_quran)

                if not all(reference in coverage for reference in references):
                    # Defense in depth.
                    #
                    # The Dorar acquisition layer
                    # already enforces this, but the
                    # Basira domain boundary refuses
                    # to accept an unanchored node.
                    continue

            if self.publication_ledger is not None:
                self.publication_ledger.admit(node)

            accepted.append(node)

            if len(accepted) >= limit:
                break

        return tuple(accepted)
