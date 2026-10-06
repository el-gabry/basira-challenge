from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionRetrievalBridge,
    CompetitionRetrievalRequest,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlan,
    RetrievalTarget,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)
from basira.sources.quran.repository import (
    QuranRepository,
)

# Only domains with an already-proven Competition
# evidence lane belong here.
#
# Fiqh is deliberately NOT mapped yet because its
# bridge requires an immutable Fiqh policy envelope.
#
# Revelation context is deliberately NOT mapped until
# its Competition runtime lane exists.
_EVIDENCE_DOMAIN_MAP = {
    EvidenceDomain.QURAN: OfficialDomain.QURAN,
    EvidenceDomain.HADITH: OfficialDomain.HADITH,
    EvidenceDomain.TAFSIR: OfficialDomain.TAFSIR,
}


@dataclass(
    frozen=True,
    slots=True,
)
class _QuranRepositoryView:
    """
    Compatibility surface for the existing canonical
    Quran anchor resolver.

    This object is NOT a retrieval authority.

    It exposes only the already-admitted Quranpedia
    repository so canonical anchor resolution can
    continue using the proven Basira resolver.
    """

    repository: QuranRepository


def _target_references(
    target: RetrievalTarget,
) -> tuple[str, ...]:
    references = getattr(
        target,
        "references",
        (),
    )

    if not references:
        return ()

    return tuple(
        value.strip()
        for value in references
        if isinstance(value, str) and value.strip()
    )


def _quran_references(
    plan: BasiraRetrievalPlan,
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()

    for target in plan.targets:
        if target.domain is not EvidenceDomain.QURAN:
            continue

        for reference in _target_references(target):
            if reference in seen:
                continue

            seen.add(reference)
            result.append(reference)

    return tuple(result)


def _normalize_focus_text(
    value: str,
) -> str:
    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    normalized: list[str] = []

    letter_map = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
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

        char = letter_map.get(
            char,
            char,
        )

        if char.isalnum() or char.isspace():
            normalized.append(char)
        else:
            normalized.append(" ")

    return " ".join("".join(normalized).split())


def _parse_quran_reference(
    value: str,
) -> tuple[int, int] | None:
    match = re.fullmatch(
        r"\s*(\d{1,3}):(\d{1,3})\s*",
        value,
    )

    if match is None:
        return None

    return (
        int(match.group(1)),
        int(match.group(2)),
    )


def _longest_quran_overlap(
    *,
    question: str,
    verse_text: str,
) -> str | None:
    """
    Discovery focus only.

    The phrase must already exist in both:
    - the user's question; and
    - the canonically anchored Quran verse.

    It creates no evidence and grants no authority.
    """

    question_tokens = _normalize_focus_text(question).split()

    verse = _normalize_focus_text(verse_text)

    # Avoid generic one/two-word phrases.
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


def _quran_focus_query(
    *,
    plan: BasiraRetrievalPlan,
    references: tuple[str, ...],
    repository: QuranRepository,
) -> str | None:
    question = plan.understanding.query.original_text

    for reference in references:
        parsed = _parse_quran_reference(reference)

        if parsed is None:
            continue

        surah, ayah = parsed

        verse = repository.get(
            surah,
            ayah,
        )

        if verse is None:
            continue

        focus = _longest_quran_overlap(
            question=question,
            verse_text=verse.text_uthmani,
        )

        if focus:
            return focus

    return None


def _queries_for_target(
    *,
    plan: BasiraRetrievalPlan,
    target: RetrievalTarget,
    quran_repository: QuranRepository,
) -> tuple[str, ...]:
    own_references = _target_references(target)

    # Exact identities remain executable for
    # non-Tafsir lanes.
    if own_references and target.domain is not EvidenceDomain.TAFSIR:
        return own_references

    if target.domain is EvidenceDomain.TAFSIR:
        anchors = own_references or _quran_references(plan)

        if anchors:
            focus = _quran_focus_query(
                plan=plan,
                references=anchors,
                repository=quran_repository,
            )

            if focus:
                return (focus,)

    query = plan.understanding.query.original_text.strip()

    return (query,) if query else ()


def _request_limit(
    *,
    plan: BasiraRetrievalPlan,
    target: RetrievalTarget,
    default: int,
) -> int:
    """
    Return at most one anchored Tafsir passage.

    Dorar source acquisition may inspect up to three
    candidates before returning the first admitted
    passage whose Quran coverage satisfies the hard
    identity.
    """

    if target.domain is EvidenceDomain.TAFSIR and (
        _target_references(target) or _quran_references(plan)
    ):
        return 1

    return default


class CompetitionUnifiedRetriever:
    """
    Compatibility layer between the existing governed
    orchestration contract and CompetitionRetrievalBridge.

    It preserves the existing:
        retrieve(plan, limit_per_domain) -> UnifiedRetrievalResult

    interface expected by GovernedCapabilityExecutor.

    It does NOT:
    - call BasiraUnifiedRetriever;
    - widen unavailable Competition domains;
    - fall back to Tanzil / SurahApp / HadeethEnc;
    - choose source families;
    - create authority;
    - reinterpret bridge failures as successful zero hits.
    """

    def __init__(
        self,
        *,
        bridge: CompetitionRetrievalBridge,
        quran_repository: QuranRepository,
    ) -> None:
        self.bridge = bridge

        # Existing canonical anchor resolution looks for:
        #
        # retriever.retrievers[EvidenceDomain.QURAN]
        #     .repository
        #
        # Preserve that read-only interface while actual
        # retrieval remains exclusively bridge-backed.
        self.retrievers = {
            EvidenceDomain.QURAN: _QuranRepositoryView(
                repository=quran_repository,
            ),
        }

    def retrieve(
        self,
        plan: BasiraRetrievalPlan,
        *,
        limit_per_domain: int = 10,
    ) -> UnifiedRetrievalResult:
        if limit_per_domain <= 0:
            return UnifiedRetrievalResult(
                plan=plan,
                evidence=(),
                unavailable_domains=frozenset(),
            )

        evidence: list[EvidenceNode] = []
        unavailable: set[EvidenceDomain] = set()
        seen: set[str] = set()

        for target in plan.targets:
            official_domain = _EVIDENCE_DOMAIN_MAP.get(target.domain)

            if official_domain is None:
                unavailable.add(target.domain)
                continue

            queries = _queries_for_target(
                plan=plan,
                target=target,
                quran_repository=(self.retrievers[EvidenceDomain.QURAN].repository),
            )

            if not queries:
                unavailable.add(target.domain)
                continue

            domain_nodes: list[EvidenceNode] = []

            domain_unavailable = False

            for query in queries:
                result = self.bridge.retrieve(
                    CompetitionRetrievalRequest(
                        official_domain=(official_domain),
                        query=query,
                        limit=_request_limit(
                            plan=plan,
                            target=target,
                            default=limit_per_domain,
                        ),
                        references=(
                            (_target_references(target) or _quran_references(plan))
                            if target.domain is EvidenceDomain.TAFSIR
                            else _target_references(target)
                        ),
                    )
                )

                if result.unavailable:
                    domain_unavailable = True
                    break

                domain_nodes.extend(result.evidence)

            if domain_unavailable:
                # Fail closed for the whole domain.
                # Do not publish partial evidence from
                # an execution whose authorized source
                # became unavailable.
                unavailable.add(target.domain)
                continue

            for node in domain_nodes:
                if node.domain is not target.domain:
                    # Defensive authority boundary:
                    # an adapter registered for one Basira
                    # evidence domain may not smuggle another
                    # domain through this compatibility layer.
                    continue

                if node.evidence_id in seen:
                    continue

                seen.add(node.evidence_id)
                evidence.append(node)

        return UnifiedRetrievalResult(
            plan=plan,
            evidence=tuple(evidence),
            unavailable_domains=(frozenset(unavailable)),
        )
