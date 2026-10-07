from __future__ import annotations

import unicodedata
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
        "صحيحه",
        "صح",
        "ضعيف",
        "موضوع",
        "درجه",
        "ما",
        "هو",
        "هذا",
        "هذه",
        "ده",
        "اشرح",
        "شرح",
        "معني",
        "يوجد",
        "فيه",
        "ورد",
        "منسوب",
        "للنبي",
        "النبي",
        "يقول",
        "قال",
        "صلي",
        "الله",
        "عليه",
        "وسلم",
    }
)

_AUTHENTICITY_STOPWORDS = _HADITH_QUERY_SCAFFOLDING | {
    "عن",
    "من",
    "ثم",
    "له",
    "لها",
    "انه",
    "انها",
    "ولا",
    "ايه",

    # English query scaffolding.
    #
    # These tokens describe the verification request,
    # not the Hadith identity itself. Without this set,
    # an English authenticity question is unfairly
    # penalized by the identity-overlap firewall.
    "a",
    "an",
    "are",
    "authentic",
    "authenticity",
    "by",
    "correct",
    "hadith",
    "is",
    "it",
    "judged",
    "narration",
    "report",
    "sahih",
    "saying",
    "the",
    "this",
    "true",
    "was",
    "were",
}

_NUMBER_WORDS = {
    "واحد": 1,
    "واحده": 1,
    "اثنان": 2,
    "اثنين": 2,
    "اثنتان": 2,
    "اثنتين": 2,
    "ثلاث": 3,
    "ثلاثه": 3,
    "اربعه": 4,
    "اربع": 4,
    "خمس": 5,
    "خمسه": 5,
    "ست": 6,
    "سته": 6,
    "سبع": 7,
    "سبعه": 7,
    "ثمان": 8,
    "ثمانيه": 8,
    "ثماني": 8,
    "تسع": 9,
    "تسعه": 9,
    "عشر": 10,
    "عشره": 10,
}


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)

    result: list[str] = []

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ة": "ه",
    }

    for char in value:
        if char == "\u0640":
            continue

        if unicodedata.category(char) in {
            "Mn",
            "Me",
            "Cf",
        }:
            continue

        char = replacements.get(char, char)

        if char.isalnum() or char.isspace():
            result.append(char)
        else:
            result.append(" ")

    return " ".join("".join(result).split())


def _number_concepts(value: str) -> frozenset[int]:
    concepts: set[int] = set()

    for token in _normalize_text(value).split():
        if token in _NUMBER_WORDS:
            concepts.add(_NUMBER_WORDS[token])
            continue

        if token.isdigit():
            try:
                concepts.add(int(token))
            except ValueError:
                pass

    return frozenset(concepts)


def _discovery_query(
    understanding: BasiraQueryUnderstanding,
) -> str:
    tokens = _normalize_text(
        understanding.query.search_text
    ).split()

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


def _is_authenticity_query(
    understanding: BasiraQueryUnderstanding,
) -> bool:
    intent = getattr(
        understanding.primary_intent,
        "value",
        understanding.primary_intent,
    )

    return str(intent) == "hadith_authenticity"


def _authenticity_candidate_matches(
    *,
    question: str,
    hadith_text: str,
) -> bool:
    """
    Authenticity questions are identity-sensitive.

    Search similarity is NOT enough to establish that
    the returned Hadith is the saying the user asked
    about.

    This guard is deliberately conservative:
    - explicit numeric concepts must be preserved;
    - substantive claim wording must materially overlap.
    """

    if not hadith_text.strip():
        return False

    question_normalized = _normalize_text(question)
    candidate_normalized = _normalize_text(hadith_text)

    question_numbers = _number_concepts(question_normalized)

    if question_numbers:
        candidate_numbers = _number_concepts(candidate_normalized)

        # "سبع مرات" must never resolve to
        # "ثلاث مرات / ثمانية أبواب".
        if not question_numbers.issubset(candidate_numbers):
            return False

    question_tokens = {
        token
        for token in question_normalized.split()
        if (
            token not in _AUTHENTICITY_STOPWORDS
            and len(token) >= 3
        )
    }

    if len(question_tokens) < 2:
        # No sufficiently concrete claimed wording.
        # Do not invent an identity.
        return False

    candidate_tokens = set(candidate_normalized.split())

    overlap = question_tokens & candidate_tokens

    return (
        len(overlap) >= 2
        and (
            len(overlap) / len(question_tokens)
        ) >= 0.60
    )


def _filter_authenticity_evidence(
    *,
    understanding: BasiraQueryUnderstanding,
    nodes: tuple[EvidenceNode, ...],
) -> tuple[EvidenceNode, ...]:
    if not _is_authenticity_query(understanding):
        return nodes

    question = understanding.query.original_text

    accepted_text_ids = {
        node.evidence_id
        for node in nodes
        if (
            node.claim_type == "hadith_text"
            and _authenticity_candidate_matches(
                question=question,
                hadith_text=node.text,
            )
        )
    }

    if not accepted_text_ids:
        return ()

    accepted: list[EvidenceNode] = []

    for node in nodes:
        if (
            node.claim_type == "hadith_text"
            and node.evidence_id in accepted_text_ids
        ):
            accepted.append(node)
            continue

        if node.claim_type == "hadith_grade":
            related = set(
                getattr(node, "related_hadith", ()) or ()
            )

            # Grade is admissible only with the exact
            # text identity that survived the guard.
            if related & accepted_text_ids:
                accepted.append(node)

    return tuple(accepted)


class OfficialHadithDomainRetriever:
    """
    Public Hadith retrieval backed exclusively by the
    admitted Dorar Hadith lane.

    Discovery may find candidates; it does not grant
    identity or authenticity authority.
    """

    def __init__(
        self,
        *,
        adapter: OfficialHadithEvidenceAdapter,
        publication_ledger: (
            GovernedPublicationLedger | None
        ) = None,
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
                "OfficialHadithDomainRetriever requires "
                "a Hadith target."
            )

        references = tuple(
            dict.fromkeys(
                value.strip()
                for value in target.references
                if value.strip()
            )
        )

        queries = references or (
            _discovery_query(understanding),
        )

        accepted: list[EvidenceNode] = []
        seen: set[str] = set()

        for query in queries:
            if not query:
                continue

            try:
                raw_nodes = self.adapter.retrieve(
                    CompetitionRetrievalRequest(
                        official_domain=(
                            OfficialDomain.HADITH
                        ),
                        query=query,
                        limit=limit,
                        references=references,
                    )
                )
            except CompetitionRetrievalError as exc:
                raise DomainRetrievalUnavailableError(
                    EvidenceDomain.HADITH
                ) from exc

            nodes = _filter_authenticity_evidence(
                understanding=understanding,
                nodes=raw_nodes,
            )

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

            if accepted and not references:
                break

        return tuple(accepted)
