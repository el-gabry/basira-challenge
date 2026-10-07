from __future__ import annotations

import inspect
import re
import unicodedata
from dataclasses import dataclass, replace
from uuid import uuid4

from basira.answer.governed_composer import (
    DenyAllPublicationAuthorizer,
    GovernedGroundedAnswerComposer,
)
from basira.answer.models import GroundedAnswer
from basira.answer.semantic_verification import (
    GeneratedClaimEvidenceRecord,
    GeneratedClaimSemanticVerifier,
)
from basira.api.claim_graph_planner import (
    PublicClaimGraphPlanner,
)
from basira.api.public_graph_outcome import (
    PublicGraphOutcomeEvaluator,
)
from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionAction,
    EvidenceDecisionReason,
)
from basira.evidence.models import EvidenceDomain, EvidenceNeed, EvidenceNode
from basira.evidence.publication import EvidencePublicationAuthorizer
from basira.evidence.service import (
    EvidenceDecisionOutcome,
    EvidenceDecisionService,
)
from basira.models.hadith import (
    HadithGradeCategory,
)
from basira.orchestration.capability_broker import (
    CapabilityBroker,
)
from basira.orchestration.capability_executor import (
    CapabilityExecutionError,
    CapabilityRetrievalBinding,
    GovernedCapabilityExecutor,
)
from basira.orchestration.claim_graph import (
    ClaimGraphPlan,
)
from basira.orchestration.claim_sufficiency import (
    ClaimResolution,
    ClaimResolutionState,
    ClaimSufficiencyAssessment,
    ClaimSufficiencyContract,
    ClaimSufficiencyState,
    SupportRequirement,
)
from basira.orchestration.contracts import AgentCapability, ClaimTask
from basira.orchestration.coordinator import (
    AgentCoordinator,
    CoordinatorRunResult,
)
from basira.orchestration.evidence_acceptance import (
    AnchorKind,
    AnchorOrigin,
    ClaimEvidencePolicySet,
)
from basira.orchestration.evidence_contract_compiler import (
    TaskEvidenceContractCompiler,
    UnresolvedEvidenceIdentityError,
)
from basira.orchestration.evidence_relation import (
    ClaimEvidenceRelation,
    ClaimEvidenceRelationRecord,
    RelationOrigin,
    TaskEvidenceRelationAssessment,
    TaskEvidenceRelationService,
)
from basira.orchestration.execution_ledger import (
    ExecutionBudget,
    ExecutionLedger,
)
from basira.orchestration.quran_anchor_resolution import (
    AnchorResolutionDisposition,
    QuranAnchorResolution,
    QuranCanonicalAnchorResolver,
    VerifiedCanonicalAnchor,
)
from basira.reasoning.contracts import ReasoningMode
from basira.reasoning.route_governor import RouteGovernor
from basira.reasoning.route_proposal import (
    NoOpRouteProposer,
    RouteProposer,
)
from basira.reasoning.routing import ReligiousReasoningRouter
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import BasiraRetrievalPlanner
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
    UnifiedRetrievalResult,
)

_QUOTE_MARKERS = (
    "في قوله تعالى",
    "قوله تعالى",
    "قال تعالى",
    "يقول تعالى",
)

_MEANING_CUES = (
    "ما معنى",
    "ما معني",
    "ما المقصود",
    "ما المراد",
    "تفسير",
    "شرح",
)


# Deterministic canonical names only.
#
# This mapping is identity resolution, not evidence.
# Every resolved reference is still validated against
# the canonical Quran repository before it may become
# a hard execution anchor.
_NAMED_QURAN_REFERENCES = {
    "اية الكرسي": "2:255",
    "آية الكرسي": "2:255",
    "آيه الكرسي": "2:255",
    "ايه الكرسي": "2:255",
}

_STOP_WORDS = frozenset(
    {
        "ما",
        "ماذا",
        "هل",
        "هو",
        "هي",
        "هذا",
        "هذه",
        "ذلك",
        "تلك",
        "في",
        "من",
        "عن",
        "على",
        "إلى",
        "الى",
        "مع",
        "معنى",
        "معني",
        "المقصود",
        "المراد",
        "شرح",
        "تفسير",
        "حكم",
        "درجة",
        "حديث",
        "الحديث",
        "صحيح",
        "صحة",
        "أقوال",
        "اقوال",
        "المذاهب",
        "مسألة",
        "المسألة",
        "قوله",
        "تعالى",
        "آية",
        "اية",
        "الآية",
        "الاية",
        "الآيات",
        "الايات",
        "قال",
    }
)

_EXPLANATION_CUES = (
    "معنى",
    "يعني",
    "أي",
    "اى",
    "المراد",
    "قال",
    "فسر",
    "تفسير",
    "ذكر",
)


def _normalize_char(char: str) -> str:
    if unicodedata.category(char) == "Mn" or char == "ـ":
        return ""

    return {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
    }.get(char, char)


def normalize_semantic_text(text: str) -> str:
    # Semantic normalization only.
    # NFKC safely collapses presentation/compatibility forms
    # before the existing Arabic orthographic normalization.
    text = unicodedata.normalize("NFKC", text)

    chars: list[str] = []
    previous_space = False

    for char in text:
        char = _normalize_char(char)

        if not char:
            continue

        if char.isspace() or not (char.isalnum() or "\u0600" <= char <= "\u06ff"):
            if chars and not previous_space:
                chars.append(" ")
                previous_space = True
            continue

        chars.append(char)
        previous_space = False

    return "".join(chars).strip()


def _normalize_with_offsets(
    text: str,
) -> tuple[str, tuple[int, ...]]:
    chars: list[str] = []
    offsets: list[int] = []
    previous_space = False

    for index, char in enumerate(text):
        char = _normalize_char(char)

        if not char:
            continue

        if char.isspace() or not (char.isalnum() or "\u0600" <= char <= "\u06ff"):
            if chars and not previous_space:
                chars.append(" ")
                offsets.append(index)
                previous_space = True
            continue

        chars.append(char)
        offsets.append(index)
        previous_space = False

    return "".join(chars).strip(), tuple(offsets)


def semantic_terms(question: str) -> tuple[str, ...]:
    prefix = question

    for marker in _QUOTE_MARKERS:
        if marker in prefix:
            prefix = prefix.split(marker, 1)[0]
            break

    cleaned = prefix.strip(" \t\r\n؟?،؛:«»\"'()[]{}.")

    for cue in _MEANING_CUES:
        if cleaned.startswith(cue):
            cleaned = cleaned[len(cue) :].strip()
            break

    stop = {normalize_semantic_text(item) for item in _STOP_WORDS}

    tokens = [
        normalize_semantic_text(token)
        for token in re.findall(
            r"[\u0600-\u06ff]+",
            cleaned,
        )
    ]

    result: list[str] = []

    for token in tokens:
        if len(token) < 3 or token in stop:
            continue

        result.append(token)

        if token.startswith("ال") and len(token) > 4:
            result.append(token[2:])

    return tuple(dict.fromkeys(result))



_MEANING_FOCUS_PATTERNS = (
    re.compile(
        r"(?:ما\s+)?معن[ىي]\s+([\u0600-\u06ff]+)"
    ),
    re.compile(
        r"(?:ما\s+)?المراد\s+(?:بـ?|ب)?([\u0600-\u06ff]+)"
    ),
)


def _explicit_tafsir_focus(
    question: str,
) -> tuple[str, ...] | None:
    """
    Extract an explicit meaning target without inventing
    evidence or identity.

    Example:
        ما معنى الكرسي في قوله تعالى ...
        -> ("الكرسي", "كرسي")

    This is retrieval focus only. It is never evidence.
    """

    normalized = normalize_semantic_text(
        question
    )

    for pattern in _MEANING_FOCUS_PATTERNS:
        match = pattern.search(
            normalized
        )

        if match is None:
            continue

        terms = semantic_terms(
            match.group(1)
        )

        if terms:
            return terms

    return None




def _plan_quran_references(
    plan,
) -> tuple[str, ...]:
    """
    Read only references already present in the governed plan.

    This creates no Quran identity. It merely reuses identity
    that has already entered the retrieval contract.
    """

    references: list[str] = []

    for target in getattr(plan, "targets", ()) or ():
        for reference in (
            getattr(target, "references", ()) or ()
        ):
            value = str(reference).strip()

            if value and value not in references:
                references.append(value)

    return tuple(references)


def _named_quran_focus_for_plan(
    plan,
) -> tuple[str, ...] | None:
    """
    Convert an already-verified Quran reference to a known
    deterministic semantic label when one exists.

    Example:
        2:255 -> آية الكرسي -> ("الكرسي", "كرسي")
    """

    references = set(
        _plan_quran_references(plan)
    )

    if not references:
        return None

    for alias, reference in (
        _NAMED_QURAN_REFERENCES.items()
    ):
        if reference not in references:
            continue

        terms = semantic_terms(alias)

        if terms:
            return terms

    return None


def _within_one_edit(
    left: str,
    right: str,
) -> bool:
    """
    Bounded typo tolerance.

    This is deliberately NOT a global spell checker.
    It is used only against a trusted semantic label
    after Quran identity has already been verified.
    """

    if left == right:
        return True

    if abs(len(left) - len(right)) > 1:
        return False

    if len(left) == len(right):
        return (
            sum(
                a != b
                for a, b in zip(left, right, strict=False)
            )
            <= 1
        )

    if len(left) > len(right):
        left, right = right, left

    i = 0
    j = 0
    edits = 0

    while i < len(left) and j < len(right):
        if left[i] == right[j]:
            i += 1
            j += 1
            continue

        edits += 1

        if edits > 1:
            return False

        j += 1

    return True


def _canonicalize_verified_quran_focus(
    terms: tuple[str, ...],
    plan,
) -> tuple[str, ...]:
    """
    Correct at most a one-edit typo, but only against the
    trusted named focus for an already verified Quran anchor.

    Example with verified 2:255:
        الكرصي -> الكرسي

    Arbitrary user text is never globally rewritten.
    """

    trusted_sets: list[
        tuple[str, ...]
    ] = []

    # Best case: the Quran identity is already present
    # in the governed retrieval plan.
    anchored = _named_quran_focus_for_plan(
        plan
    )

    if anchored:
        trusted_sets.append(
            anchored
        )

    # Some quoted-Quran questions resolve their canonical
    # anchor later in the runtime. Permit typo recovery only
    # against deterministic Quran names already registered
    # by Basira. This is NOT a general spell checker.
    for alias in _NAMED_QURAN_REFERENCES:
        alias_terms = semantic_terms(
            alias
        )

        if (
            alias_terms
            and alias_terms not in trusted_sets
        ):
            trusted_sets.append(
                alias_terms
            )

    for term in terms:
        for trusted in trusted_sets:
            for candidate in trusted:
                if (
                    len(term) >= 4
                    and len(candidate) >= 4
                    and _within_one_edit(
                        term,
                        candidate,
                    )
                ):
                    return trusted

    return terms


def _contains_semantic_cue(
    text: str,
    cue: str,
) -> bool:
    normalized_cue = normalize_semantic_text(
        cue
    ).strip()

    if not normalized_cue:
        return False

    if " " in normalized_cue:
        return normalized_cue in text

    return (
        re.search(
            (
                r"(?<![\u0600-\u06ff])"
                + re.escape(normalized_cue)
                + r"(?![\u0600-\u06ff])"
            ),
            text,
        )
        is not None
    )


def _nested_arabic_match(
    text: str,
    position: int,
) -> bool:
    """
    True when a candidate begins inside an Arabic word.

    Example:
        bare "كرسي" inside "الكرسي"

    Such a match must not compete separately with the
    complete "الكرسي" focus occurrence.
    """

    if position <= 0:
        return False

    previous = text[position - 1]

    return "\u0600" <= previous <= "\u06ff"


def _tafsir_focus_score(
    text: str,
    terms: tuple[str, ...],
) -> int:
    """
    Rank an already retrieved Tafsir excerpt by how
    directly it explains the requested focus.

    This score cannot promote an untrusted source.
    """

    normalized = normalize_semantic_text(
        text
    )

    best = 0

    for term in terms:
        cursor = 0

        while True:
            position = normalized.find(
                term,
                cursor,
            )

            if position < 0:
                break

            if _nested_arabic_match(
                normalized,
                position,
            ):
                cursor = position + 1
                continue

            prefix = normalized[
                max(0, position - 24) : position
            ]

            suffix = normalized[
                position
                + len(term) :
                position
                + len(term)
                + 110
            ]

            score = 1

            # Headword / glossary-style explanation.
            if (
                position <= 24
                or prefix.rstrip().endswith(":")
            ):
                score += 5

            # Explicit explanatory construction.
            if any(
                cue in suffix
                for cue in (
                    " هو ",
                    " وهو ",
                    " هي ",
                    " وهي ",
                    " يعني ",
                    " المراد ",
                    " الذي هو ",
                    " التي هي ",
                )
            ):
                score += 7

            # Generic explanation signals nearby.
            local = normalized[
                max(0, position - 80) :
                min(
                    len(normalized),
                    position
                    + len(term)
                    + 180,
                )
            ]

            if any(
                _contains_semantic_cue(
                    local,
                    cue,
                )
                for cue in _EXPLANATION_CUES
            ):
                score += 3

            # "آية الكرسي" is often contextual mention,
            # not an explanation of what الكرسي means.
            if re.search(
                r"(?:^|\s)اية\s*$",
                prefix,
            ):
                score -= 10

            best = max(
                best,
                score,
            )

            cursor = position + 1

    return best


def _focused_excerpt(
    text: str,
    terms: tuple[str, ...],
    *,
    before: int = 36,
    after: int = 420,
) -> str | None:
    if not terms:
        return text

    normalized, offsets = _normalize_with_offsets(text)

    if not normalized or not offsets:
        return None

    cues = tuple(normalize_semantic_text(cue) for cue in _EXPLANATION_CUES)

    candidates: list[tuple[int, int, int]] = []

    for term in terms:
        cursor = 0

        while True:
            position = normalized.find(term, cursor)

            if position < 0:
                break

            if _nested_arabic_match(
                normalized,
                position,
            ):
                cursor = position + 1
                continue

            end_position = min(
                position + len(term) - 1,
                len(offsets) - 1,
            )

            original_start = offsets[position]
            original_end = offsets[end_position] + 1

            local = normalized[
                max(0, position - 140) : min(
                    len(normalized),
                    position + len(term) + 420,
                )
            ]

            prefix = normalized[
                max(0, position - 32) :
                position
            ]

            suffix = normalized[
                position + len(term) :
                min(
                    len(normalized),
                    position + len(term) + 140,
                )
            ]

            score = (
                3
                if original_start >= 120
                else 0
            )

            if any(
                _contains_semantic_cue(
                    local,
                    cue,
                )
                for cue in cues
            ):
                score += 4

            if prefix.rstrip().endswith(":"):
                score += 8

            if suffix.lstrip().startswith(":"):
                score += 8

            if any(
                cue in suffix
                for cue in (
                    " هو ",
                    " وهو ",
                    " هي ",
                    " وهي ",
                    " يعني ",
                    " المراد ",
                    " الذي هو ",
                    " التي هي ",
                )
            ):
                score += 7

            if re.search(
                r"(?:^|\s)اية\s*$",
                prefix,
            ):
                score -= 10

            candidates.append(
                (
                    score,
                    original_start,
                    original_end,
                )
            )

            cursor = position + 1

    if not candidates:
        return None

    _, start, end = max(
        candidates,
        key=lambda item: (
            item[0],
            -item[1],
        ),
    )

    left = max(
        0,
        start - before,
    )
    right = min(
        len(text),
        end + after,
    )

    # Prefer a real source boundary before the focus so
    # unrelated preceding glossary/sentence material is
    # not published with the requested explanation.
    left_candidates = [
        text.rfind(
            separator,
            max(0, start - 180),
            start,
        )
        for separator in (
            "\n",
            ".",
            "؟",
            "!",
            "؛",
            ":",
        )
    ]

    bounded_left = max(
        left_candidates,
        default=-1,
    )

    if bounded_left >= 0:
        left = max(
            left,
            bounded_left + 1,
        )

    # Stop at the first sentence-like boundary after the
    # focus. Colon is intentionally excluded here because
    # many Tafsir pages use it between headword and
    # explanation.
    right_candidates = [
        position
        for separator in (
            "\n",
            ".",
            "؟",
            "!",
            "؛",
        )
        if (
            position := text.find(
                separator,
                end,
                min(
                    len(text),
                    end + after,
                ),
            )
        )
        >= 0
    ]

    if right_candidates:
        right = min(
            right,
            min(right_candidates) + 1,
        )

    excerpt = text[
        left:right
    ].strip(
        " \n\t:؛"
    )

    if not excerpt:
        return None

    normalized_excerpt = normalize_semantic_text(excerpt)

    if not any(term in normalized_excerpt for term in terms):
        return None

    return excerpt


class FocusAwareRetriever:
    """
    Source-faithful semantic projection inside the governed executor.

    It cannot create evidence or authority. It may only keep an exact
    substring from a retrieved Tafsir node around the claim focus.
    """

    def __init__(
        self,
        delegate: BasiraUnifiedRetriever,
    ) -> None:
        self.delegate = delegate

    def retrieve(
        self,
        plan,
        *,
        limit_per_domain: int = 10,
    ) -> UnifiedRetrievalResult:
        result = self.delegate.retrieve(
            plan,
            limit_per_domain=limit_per_domain,
        )

        query_text = (
            plan.understanding.query.original_text
        )

        explicit_focus = (
            _explicit_tafsir_focus(
                query_text
            )
        )

        if explicit_focus is not None:
            explicit_focus = (
                _canonicalize_verified_quran_focus(
                    explicit_focus,
                    plan,
                )
            )

        anchor_focus = (
            None
            if explicit_focus is not None
            else _named_quran_focus_for_plan(
                plan
            )
        )

        # Strict focus may come from:
        #   1. an explicit semantic target in the question; or
        #   2. a deterministic name for an already-verified
        #      Quran reference.
        #
        # Generic words such as "الآية" are ignored.
        strict_focus = (
            explicit_focus
            or anchor_focus
        )

        terms = (
            strict_focus
            or semantic_terms(
                query_text
            )
        )

        if not terms:
            return result

        evidence: list[EvidenceNode] = []
        tafsir_candidates: list[
            tuple[
                int,
                int,
                EvidenceNode,
            ]
        ] = []
        seen_tafsir: set[tuple[str, str]] = set()

        for position, node in enumerate(
            result.evidence
        ):
            if node.domain is not EvidenceDomain.TAFSIR:
                evidence.append(node)
                continue

            excerpt = _focused_excerpt(
                node.text,
                terms,
            )

            if excerpt is None:
                continue

            key = (
                node.source_id,
                normalize_semantic_text(excerpt),
            )

            if key in seen_tafsir:
                continue

            seen_tafsir.add(key)

            focused_node = replace(
                node,
                text=excerpt,
            )

            tafsir_candidates.append(
                (
                    _tafsir_focus_score(
                        excerpt,
                        terms,
                    ),
                    position,
                    focused_node,
                )
            )

        if strict_focus is not None:
            strong = [
                item
                for item in tafsir_candidates
                if item[0] > 1
            ]

            # Fail conservatively: if no direct-looking
            # explanation exists, retain the governed
            # candidates rather than fabricating one.
            selected = (
                strong
                if strong
                else tafsir_candidates
            )

            selected = sorted(
                selected,
                key=lambda item: (
                    -item[0],
                    item[1],
                ),
            )[:3]
        else:
            selected = tafsir_candidates

        evidence.extend(
            node
            for _score, _position, node
            in selected
        )

        return UnifiedRetrievalResult(
            plan=result.plan,
            evidence=tuple(evidence),
            unavailable_domains=result.unavailable_domains,
        )


class PublicTaskEvidenceEvaluator:
    """
    Minimum deterministic E2 gate for public runtime.

    Structural validity has already been decided by the governed executor.
    """

    def evaluate(
        self,
        *,
        task: ClaimTask,
        evidence: EvidenceNode,
    ) -> ClaimEvidenceRelationRecord:
        terms = semantic_terms(task.claim_text)

        # Structural acceptance has already established source,
        # domain and hard-anchor validity before E2 runs.
        #
        # For a direct canonical Quran lookup, lexical overlap
        # between the user's request ("give me verse 2:255")
        # and the verse text is neither expected nor required.
        # A canonically admitted Quran-text node therefore
        # supports the direct-grounding task by verified identity.
        if (
            evidence.domain is EvidenceDomain.QURAN
            and evidence.claim_type == "quran_text"
            and task.frame.reasoning_mode is ReasoningMode.DIRECT_GROUNDING
            and EvidenceNeed.CANONICAL_TEXT
            in task.context_requirement.required
        ):
            relation = ClaimEvidenceRelation.SUPPORTS
        elif (
            evidence.domain is EvidenceDomain.QURAN
            and task.frame.reasoning_mode is ReasoningMode.INTERPRETATION
        ):
            relation = ClaimEvidenceRelation.CONTEXT_ONLY
        elif not terms:
            relation = ClaimEvidenceRelation.SUPPORTS
        else:
            # Hadith grading evidence is relational evidence:
            # the grade applies to its explicitly linked
            # Hadith text. It must not be rejected merely
            # because the verdict does not repeat the matn.
            if (
                evidence.claim_type == "hadith_grade"
                and evidence.related_hadith
            ):
                relation = ClaimEvidenceRelation.SUPPORTS
            else:
                candidate = normalize_semantic_text(
                    evidence.text
                )

                relation = (
                    ClaimEvidenceRelation.SUPPORTS
                    if any(
                        term in candidate
                        for term in terms
                    )
                    else ClaimEvidenceRelation.IRRELEVANT
                )

        return ClaimEvidenceRelationRecord(
            task_id=task.task_id,
            evidence_id=evidence.evidence_id,
            relation=relation,
            origin=RelationOrigin.DETERMINISTIC,
        )



_POSITIVE_PUBLIC_HADITH_GRADES = frozenset(
    {
        HadithGradeCategory.SAHIH.value,
        HadithGradeCategory.HASAN.value,
    }
)

_NEGATIVE_PUBLIC_HADITH_GRADES = frozenset(
    {
        HadithGradeCategory.DAIF.value,
        HadithGradeCategory.MAWDU.value,
    }
)


def _project_public_hadith_admissibility(
    *,
    task: ClaimTask,
    evidence: tuple[EvidenceNode, ...],
    assessment: TaskEvidenceRelationAssessment,
) -> TaskEvidenceRelationAssessment:
    """
    Prevent Hadith text from becoming positive public
    support independently of its linked authenticity
    assessment.

    This projection is public-answer policy only. It does
    not re-grade Hadith, change source authority, or alter
    authenticity-query behavior.

    Grade -> text linkage remains source-derived through
    EvidenceNode.related_hadith.
    """

    # Authenticity questions already have their own
    # governed grading/conflict path. Do not reinterpret it.
    if (
        EvidenceNeed.HADITH_GRADE
        in task.context_requirement.required
    ):
        return assessment

    by_id = {
        node.evidence_id: node
        for node in evidence
    }

    text_nodes = {
        node.evidence_id: node
        for node in evidence
        if (
            node.domain is EvidenceDomain.HADITH
            and node.claim_type == "hadith_text"
        )
    }

    grade_nodes = tuple(
        node
        for node in evidence
        if (
            node.domain is EvidenceDomain.HADITH
            and node.claim_type == "hadith_grade"
        )
    )

    if not text_nodes:
        return assessment

    grades_by_text: dict[
        str,
        list[EvidenceNode],
    ] = {
        evidence_id: []
        for evidence_id in text_nodes
    }

    # Support both current Dorar linkage:
    #   grade.related_hadith -> text evidence_id
    #
    # and the generic Hadith adapter linkage:
    #   text + grade share one Hadith identity key.
    for grade in grade_nodes:
        linked_text_ids: set[str] = set()

        for related in grade.related_hadith:
            direct = by_id.get(related)

            if (
                direct is not None
                and direct.evidence_id in text_nodes
            ):
                linked_text_ids.add(
                    direct.evidence_id
                )
                continue

            for text_id, text_node in text_nodes.items():
                if related in text_node.related_hadith:
                    linked_text_ids.add(text_id)

        for text_id in linked_text_ids:
            grades_by_text[text_id].append(
                grade
            )

    projected: list[
        ClaimEvidenceRelationRecord
    ] = []

    for record in assessment.records:
        node = by_id.get(record.evidence_id)

        if (
            node is None
            or node.domain is not EvidenceDomain.HADITH
        ):
            projected.append(record)
            continue

        # A grade is relational evidence. For an ordinary
        # Hadith-content claim it must not independently
        # satisfy positive-support sufficiency.
        if node.claim_type == "hadith_grade":
            projected.append(
                replace(
                    record,
                    relation=(
                        ClaimEvidenceRelation.CONTEXT_ONLY
                    ),
                    rationale=(
                        "hadith_grade_is_relational_context"
                    ),
                )
            )
            continue

        if node.claim_type != "hadith_text":
            projected.append(record)
            continue

        linked_grades = grades_by_text.get(
            node.evidence_id,
            [],
        )

        categories = {
            grade.topic
            for grade in linked_grades
            if grade.topic
        }

        has_positive = bool(
            categories
            & _POSITIVE_PUBLIC_HADITH_GRADES
        )

        has_negative = bool(
            categories
            & _NEGATIVE_PUBLIC_HADITH_GRADES
        )

        if has_positive and has_negative:
            projected.append(
                replace(
                    record,
                    relation=(
                        ClaimEvidenceRelation.CONTRADICTS
                    ),
                    rationale=(
                        "conflicting_hadith_authenticity"
                    ),
                )
            )
            continue

        if has_positive:
            # Preserve the semantic relation already
            # established for this Hadith text.
            projected.append(record)
            continue

        # Weak, fabricated, unknown, unclassified, or
        # ungraded Hadith text cannot independently support
        # a positive public religious claim.
        projected.append(
            replace(
                record,
                relation=(
                    ClaimEvidenceRelation.IRRELEVANT
                ),
                rationale=(
                    "hadith_text_not_publicly_admissible"
                ),
            )
        )

    return TaskEvidenceRelationAssessment(
        task_id=assessment.task_id,
        records=tuple(projected),
    )


class PublicTaskEvidenceRelationService(
    TaskEvidenceRelationService
):
    """
    Public semantic relation service with:

    1. optional explicit dependency semantic grounding;
    2. final deterministic Hadith admissibility projection.

    Dependency grounding changes only the text used to
    assess evidence relation. It never changes the actual
    ClaimTask, transfers evidence, or bypasses dependency
    resolution.
    """

    def __init__(
        self,
        *,
        evaluator: PublicTaskEvidenceEvaluator,
        semantic_basis_by_task_id: (
            dict[str, str] | None
        ) = None,
    ) -> None:
        super().__init__(
            evaluator=evaluator,
        )

        self._semantic_basis_by_task_id = dict(
            semantic_basis_by_task_id or {}
        )

    def evaluate(
        self,
        *,
        task: ClaimTask,
        structural,
    ) -> TaskEvidenceRelationAssessment:
        semantic_basis = (
            self._semantic_basis_by_task_id.get(
                task.task_id
            )
        )

        relation_task = task

        if (
            semantic_basis
            and task.frame.primary_discipline.value
            == "hadith"
            and task.frame.reasoning_mode
            is ReasoningMode.INTERPRETATION
        ):
            relation_frame = replace(
                task.frame,
                question=semantic_basis,
            )

            relation_task = replace(
                task,
                claim_text=semantic_basis,
                frame=relation_frame,
            )

        assessment = super().evaluate(
            task=relation_task,
            structural=structural,
        )

        # Authenticity/admissibility policy must still use
        # the REAL task contract, not the temporary semantic
        # relation basis.
        return _project_public_hadith_admissibility(
            task=task,
            evidence=tuple(
                structural.accepted_evidence
            ),
            assessment=assessment,
        )


class LiteralGeneratedClaimEvaluator:
    """
    E4 for the current deterministic composer.

    Current claims are source excerpts. PASS is granted only when a cited
    source literally contains the claim after normalization.
    """

    def evaluate(
        self,
        *,
        claim,
        evidence: EvidenceNode,
    ) -> GeneratedClaimEvidenceRecord:
        claim_text = normalize_semantic_text(claim.text)
        evidence_text = normalize_semantic_text(evidence.text)

        if claim_text and claim_text in evidence_text:
            relation = ClaimEvidenceRelation.SUPPORTS
            confidence = 1.0
        else:
            claim_tokens = set(claim_text.split())
            evidence_tokens = set(evidence_text.split())
            overlap = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))

            if overlap >= 0.6:
                relation = ClaimEvidenceRelation.PARTIAL
            else:
                relation = ClaimEvidenceRelation.IRRELEVANT

            confidence = overlap

        return GeneratedClaimEvidenceRecord(
            claim_id=claim.claim_id,
            evidence_id=evidence.evidence_id,
            relation=relation,
            origin=RelationOrigin.DETERMINISTIC,
            confidence=confidence,
        )


def build_public_semantic_verifier() -> GeneratedClaimSemanticVerifier:
    return GeneratedClaimSemanticVerifier(evaluator=LiteralGeneratedClaimEvaluator())


class FrozenUnderstandingService:
    def __init__(
        self,
        understanding: BasiraQueryUnderstanding,
    ) -> None:
        self.understanding = understanding

    def understand(
        self,
        _question: str,
    ) -> BasiraQueryUnderstanding:
        return self.understanding


class ClaimMappedUnderstandingService:
    """
    Serve the governed understanding prepared for each
    exact graph claim.

    One claim can never inherit another claim's routing
    or context requirements.
    """

    def __init__(
        self,
        by_claim_text: dict[
            str,
            BasiraQueryUnderstanding,
        ],
    ) -> None:
        self._by_claim_text = dict(
            by_claim_text
        )

    def understand(
        self,
        question: str,
    ) -> BasiraQueryUnderstanding:
        try:
            return self._by_claim_text[
                question
            ]
        except KeyError as exc:
            raise ValueError(
                "no governed understanding prepared "
                "for graph claim"
            ) from exc


@dataclass(
    frozen=True,
    slots=True,
)
class PublicClaimGraphExecution:
    plan: ClaimGraphPlan
    run: CoordinatorRunResult
    executor: GovernedCapabilityExecutor
    evaluator: PublicGraphOutcomeEvaluator


@dataclass(
    frozen=True,
    slots=True,
)
class GovernedRuntimeResult:
    question: str
    understanding: BasiraQueryUnderstanding
    retrieval: UnifiedRetrievalResult
    outcome: EvidenceDecisionOutcome
    answer: GroundedAnswer
    relation: TaskEvidenceRelationAssessment | None
    sufficiency: ClaimSufficiencyAssessment | None
    dependency: ClaimResolution | None

    clarification_reason: str | None = None

    clarification_candidates: tuple[
        str,
        ...,
    ] = ()


class _QuranIdentityClarificationRequired(
    RuntimeError
):
    def __init__(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
        resolution: QuranAnchorResolution,
    ) -> None:
        super().__init__(
            resolution.reason
        )

        self.understanding = understanding
        self.resolution = resolution


def _quran_repository(
    retriever: BasiraUnifiedRetriever,
):
    mapping = getattr(
        retriever,
        "retrievers",
        None,
    )

    if mapping is None:
        mapping = getattr(
            retriever,
            "_retrievers",
            None,
        )

    if not isinstance(mapping, dict):
        return None

    quran_retriever = mapping.get(EvidenceDomain.QURAN)

    return (
        getattr(
            quran_retriever,
            "repository",
            None,
        )
        if quran_retriever is not None
        else None
    )


def _resolver(
    retriever: BasiraUnifiedRetriever,
) -> QuranCanonicalAnchorResolver | None:
    signature = inspect.signature(QuranCanonicalAnchorResolver)

    required = tuple(
        parameter
        for parameter in signature.parameters.values()
        if (
            parameter.default is inspect.Parameter.empty
            and parameter.kind
            in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
        )
    )

    if not required:
        return QuranCanonicalAnchorResolver()

    repository = _quran_repository(retriever)

    if repository is None:
        return None

    if any(parameter.name == "repository" for parameter in required):
        return QuranCanonicalAnchorResolver(repository=repository)

    return None


def _resolution_from_reference(
    *,
    reference: str,
    retriever: BasiraUnifiedRetriever,
) -> QuranAnchorResolution | None:
    match = re.fullmatch(
        r"\s*(\d{1,3}):(\d{1,3})\s*",
        reference,
    )

    if match is None:
        return None

    surah = int(match.group(1))
    ayah = int(match.group(2))

    if not 1 <= surah <= 114 or ayah < 1:
        return None

    repository = _quran_repository(retriever)
    matched_text = reference.strip()

    if repository is not None:
        verse = repository.get(surah, ayah)

        if verse is None:
            return None

        matched_text = verse.text_search

    return QuranAnchorResolution(
        disposition=AnchorResolutionDisposition.RESOLVED,
        anchors=(
            VerifiedCanonicalAnchor(
                reference=f"{surah}:{ayah}",
                kind=AnchorKind.QURAN_AYAH,
                origin=AnchorOrigin.EXPLICIT_REFERENCE,
                matched_text=matched_text,
            ),
        ),
        reason="validated_explicit_quran_reference",
    )


def _named_quran_resolution(
    *,
    question: str,
    retriever: BasiraUnifiedRetriever,
) -> QuranAnchorResolution | None:
    """
    Resolve deterministic, well-known Quran names.

    A named reference never creates evidence and never
    bypasses canonical validation. It is converted into
    a candidate Quran reference, then validated through
    the same repository-backed reference resolver used
    by explicit numeric references.
    """

    normalized_question = normalize_semantic_text(question)

    matches = {
        reference
        for alias, reference in _NAMED_QURAN_REFERENCES.items()
        if normalize_semantic_text(alias) in normalized_question
    }

    # Ambiguous aliases fail closed.
    if len(matches) != 1:
        return None

    reference = next(iter(matches))

    resolution = _resolution_from_reference(
        reference=reference,
        retriever=retriever,
    )

    if not _is_resolved(resolution):
        return None

    return replace(
        resolution,
        reason="validated_named_quran_reference",
    )


def _quote_resolution(
    *,
    question: str,
    retriever: BasiraUnifiedRetriever,
) -> QuranAnchorResolution | None:
    repository = _quran_repository(retriever)

    if repository is None:
        return None

    for marker in _QUOTE_MARKERS:
        if marker not in question:
            continue

        candidate = question.split(
            marker,
            1,
        )[1].strip(" \t\r\n؟?،؛:«»\"'()[]{}.")

        if not candidate:
            continue

        matches = repository.find_exact(candidate)

        if not matches:
            matches = repository.find_containing(candidate)

        if len(matches) != 1:
            continue

        verse = matches[0]

        return QuranAnchorResolution(
            disposition=(AnchorResolutionDisposition.RESOLVED),
            anchors=(
                VerifiedCanonicalAnchor(
                    reference=verse.reference,
                    kind=AnchorKind.QURAN_AYAH,
                    origin=(AnchorOrigin.CANONICAL_TEXT_MATCH),
                    matched_text=candidate,
                ),
            ),
            reason=("unique_canonical_quran_text_match"),
        )

    return None


def _is_resolved(
    resolution: QuranAnchorResolution | None,
) -> bool:
    return bool(
        resolution is not None
        and resolution.disposition is AnchorResolutionDisposition.RESOLVED
        and resolution.anchors
    )


_QURAN_CLARIFICATION_INTENTS = frozenset(
    {
        BasiraIntent.QURAN_LOOKUP,
        BasiraIntent.QURAN_MEANING,
        BasiraIntent.TAFSIR_CONTEXT,
    }
)


def _needs_quran_identity_clarification(
    *,
    understanding: BasiraQueryUnderstanding,
    resolution: QuranAnchorResolution | None,
) -> bool:
    return bool(
        resolution is not None
        and resolution.disposition
        in {
            AnchorResolutionDisposition.ASK_USER,
            AnchorResolutionDisposition.BOUNDED_BRANCH,
        }
        and understanding.primary_intent
        in _QURAN_CLARIFICATION_INTENTS
    )


def _canonical_resolution(
    *,
    understanding: BasiraQueryUnderstanding,
    question: str,
    quran_reference: str | None,
    retriever: BasiraUnifiedRetriever,
) -> QuranAnchorResolution | None:
    resolver = _resolver(retriever)

    resolution = None

    if resolver is not None:
        resolution = resolver.resolve(
            understanding
        )

        if _is_resolved(
            resolution
        ):
            return resolution

        if (
            resolution.disposition
            is AnchorResolutionDisposition.BOUNDED_BRANCH
        ):
            return resolution

        if (
            resolution.disposition
            is AnchorResolutionDisposition.ASK_USER
            and resolution.reason
            != "anchor_requested_but_not_canonically_resolved"
        ):
            return resolution

    # Canonical text match has priority over a contradictory manual hint.
    quote_resolution = _quote_resolution(
        question=question,
        retriever=retriever,
    )

    if _is_resolved(quote_resolution):
        return quote_resolution

    named_resolution = _named_quran_resolution(
        question=question,
        retriever=retriever,
    )

    if _is_resolved(named_resolution):
        return named_resolution

    if quran_reference:
        return _resolution_from_reference(
            reference=quran_reference,
            retriever=retriever,
        )

    entities = {entity.entity_type: entity.value for entity in understanding.entities}

    surah = entities.get("surah_number")
    ayah = entities.get("ayah_number")

    if surah and ayah:
        return _resolution_from_reference(
            reference=f"{surah}:{ayah}",
            retriever=retriever,
        )

    return resolution



_QURAN_LOOKUP_SOURCE_CUES = (
    "القران",
    "في القران",
    "ذكر القران",
    "امر القران",
    "قال القران",
)

_HADITH_LOOKUP_SOURCE_CUES = (
    "في السنة",
    "السنة النبوية",
    "ورد في السنة",
    "ثبت في السنة",
    "في الحديث",
    "ورد في الحديث",
)


def _promote_explicit_source_lookup(
    *,
    understanding: BasiraQueryUnderstanding,
    question: str,
) -> BasiraQueryUnderstanding:
    """
    Promote only a generic public question when the user
    explicitly names the authority lane.

    This is routing metadata only:
    - it does not choose a source record;
    - it does not create a Quran/Hadith identity;
    - it does not create evidence;
    - ambiguous mixed-source wording stays generic.
    """

    if (
        understanding.primary_intent
        is not BasiraIntent.GENERAL_ISLAMIC_QUESTION
    ):
        return understanding

    normalized = normalize_semantic_text(
        question
    )

    # If the same atomic question explicitly asks about
    # both Quran and Sunnah, do not collapse it into one
    # authority lane. Decomposition or a later governed
    # specialization must resolve that ambiguity.
    explicit_quran_name = (
        re.search(
            r"(?<![\u0600-\u06ff])"
            r"(?:و)?القران"
            r"(?![\u0600-\u06ff])",
            normalized,
        )
        is not None
    )

    explicit_sunnah_name = (
        re.search(
            r"(?<![\u0600-\u06ff])"
            r"(?:و)?السنة"
            r"(?![\u0600-\u06ff])",
            normalized,
        )
        is not None
    )

    if (
        explicit_quran_name
        and explicit_sunnah_name
    ):
        return understanding

    quran_cue = any(
        cue in normalized
        for cue in _QURAN_LOOKUP_SOURCE_CUES
    )

    hadith_cue = any(
        cue in normalized
        for cue in _HADITH_LOOKUP_SOURCE_CUES
    )

    if quran_cue == hadith_cue:
        return understanding

    return replace(
        understanding,
        primary_intent=(
            BasiraIntent.QURAN_LOOKUP
            if quran_cue
            else BasiraIntent.HADITH_LOOKUP
        ),
    )


def _promote_quran_meaning(
    *,
    understanding: BasiraQueryUnderstanding,
    question: str,
    resolution: QuranAnchorResolution | None,
) -> BasiraQueryUnderstanding:
    if resolution is None:
        return understanding

    if (
        understanding.primary_intent
        is not BasiraIntent.GENERAL_ISLAMIC_QUESTION
    ):
        return understanding

    normalized = normalize_semantic_text(
        question
    )

    has_meaning_cue = any(
        normalize_semantic_text(
            cue
        )
        in normalized
        for cue in _MEANING_CUES
    )

    if (
        has_meaning_cue
        and resolution.disposition
        in {
            AnchorResolutionDisposition.RESOLVED,
            AnchorResolutionDisposition.ASK_USER,
            AnchorResolutionDisposition.BOUNDED_BRANCH,
        }
    ):
        return replace(
            understanding,
            primary_intent=(
                BasiraIntent.QURAN_MEANING
            ),
            confidence=max(
                understanding.confidence,
                0.95,
            ),
        )

    if not _is_resolved(
        resolution
    ):
        return understanding

    if (
        resolution.reason
        == "validated_named_quran_reference"
    ):
        named_lookup_forms = {
            normalize_semantic_text(
                alias
            )
            for alias
            in _NAMED_QURAN_REFERENCES
        }

        if normalized in named_lookup_forms:
            return replace(
                understanding,
                primary_intent=(
                    BasiraIntent.QURAN_LOOKUP
                ),
                confidence=max(
                    understanding.confidence,
                    0.95,
                ),
            )

    return understanding



def _support_domains(
    contract,
) -> frozenset[EvidenceDomain]:
    required = frozenset(contract.required_domains)

    if EvidenceDomain.TAFSIR in required:
        return frozenset({EvidenceDomain.TAFSIR})

    if EvidenceDomain.HADITH in required:
        return frozenset({EvidenceDomain.HADITH})

    fiqh = required & frozenset(
        {
            EvidenceDomain.FIQH,
            EvidenceDomain.FATWA,
        }
    )

    if fiqh:
        return fiqh

    non_quran = required - frozenset({EvidenceDomain.QURAN})

    return non_quran or required


def _semantic_retrieval(
    *,
    retrieval: UnifiedRetrievalResult,
    relation: TaskEvidenceRelationAssessment,
) -> UnifiedRetrievalResult:
    allowed_ids = set(relation.supporting_evidence_ids)
    allowed_ids.update(relation.context_only_evidence_ids)
    allowed_ids.update(relation.partial_evidence_ids)
    allowed_ids.update(relation.contradicting_evidence_ids)

    return UnifiedRetrievalResult(
        plan=retrieval.plan,
        evidence=tuple(
            node for node in retrieval.evidence if node.evidence_id in allowed_ids
        ),
        unavailable_domains=(retrieval.unavailable_domains),
    )


class PublicGovernedQueryRuntime:
    """
    Single public execution spine.

    Retrieval leaves this runtime only after structural acceptance, semantic
    relation assessment and sufficiency/dependency resolution.
    """

    def __init__(
        self,
        *,
        retriever: BasiraUnifiedRetriever,
        publication_authorizer: EvidencePublicationAuthorizer | None = None,
        semantic_verifier: GeneratedClaimSemanticVerifier | None = None,
        route_proposer: RouteProposer | None = None,
        route_governor: RouteGovernor | None = None,
    ) -> None:
        self.retriever = retriever

        self.understanding_service = BasiraQueryUnderstandingService()

        self.route_proposer = (
            route_proposer if route_proposer is not None else NoOpRouteProposer()
        )

        self.route_governor = (
            route_governor if route_governor is not None else RouteGovernor()
        )

        self.router = ReligiousReasoningRouter()

        self.claim_graph_planner = PublicClaimGraphPlanner()

        self.contract_compiler = TaskEvidenceContractCompiler()

        self.decision_service = EvidenceDecisionService()

        # Trust boundary:
        # retrieval capability never implies publication capability.
        #
        # Publication authority must be injected independently by
        # the trusted composition root. Never discover it from the
        # component supplying evidence.
        if publication_authorizer is None:
            publication_authorizer = DenyAllPublicationAuthorizer()

        self.composer = GovernedGroundedAnswerComposer(
            publication_authorizer=(publication_authorizer),
            semantic_verifier=(semantic_verifier or build_public_semantic_verifier()),
        )

    def _prepare_public_claim(
        self,
        *,
        claim_text: str,
        quran_reference: str | None = None,
    ):
        """
        Prepare one atomic public claim through the
        existing governed reasoning spine.

        This method owns no decomposition policy.
        It does not retrieve evidence or publish answers.
        """

        understanding = (
            self.understanding_service
            .understand(
                claim_text
            )
        )

        understanding = (
            _promote_explicit_source_lookup(
                understanding=understanding,
                question=claim_text,
            )
        )

        quran_resolution = (
            _canonical_resolution(
                understanding=understanding,
                question=claim_text,
                quran_reference=quran_reference,
                retriever=self.retriever,
            )
        )

        understanding = (
            _promote_quran_meaning(
                understanding=understanding,
                question=claim_text,
                resolution=quran_resolution,
            )
        )

        proposal = (
            self.route_proposer
            .propose(
                understanding=understanding,
            )
        )

        governance = (
            self.route_governor
            .govern(
                understanding=understanding,
                proposal=proposal,
            )
        )

        understanding = (
            governance
            .effective_understanding
        )

        route = self.router.route(
            understanding
        )

        understanding = replace(
            understanding,
            context_requirement=(
                route.context_requirement
            ),
        )

        task = ClaimTask(
            task_id=(
                f"public-claim-{uuid4()}"
            ),
            claim_text=claim_text,
            frame=route.frame,
            context_requirement=(
                route.context_requirement
            ),
        )

        return (
            task,
            understanding,
            quran_resolution,
            frozenset(
                route.target_domains
            ),
        )

    def _plan_public_claim_graph(
        self,
        *,
        question: str,
        quran_reference: str | None = None,
    ):
        """
        Decompose first, then route every claim through
        the same governed public preparation path.

        A top-level explicit Quran reference is only
        forwarded unchanged when the graph contains one
        claim. Multi-claim graphs must resolve Quran
        identity from each claim itself rather than
        leaking one anchor into unrelated claims.
        """

        prepared = {}

        claim_texts = (
            self.claim_graph_planner
            .decompose(
                question
            )
        )

        single_claim = (
            len(claim_texts) == 1
        )

        def task_factory(
            claim_text: str,
        ) -> ClaimTask:
            (
                task,
                understanding,
                resolution,
                target_domains,
            ) = self._prepare_public_claim(
                claim_text=claim_text,
                quran_reference=(
                    quran_reference
                    if single_claim
                    else None
                ),
            )

            prepared[
                task.task_id
            ] = (
                understanding,
                resolution,
                target_domains,
            )

            return task

        plan = (
            self.claim_graph_planner
            .plan(
                question=question,
                task_factory=task_factory,
            )
        )

        # ------------------------------------------------
        # Explicit dependency context inheritance.
        #
        # A dependent clause such as:
        #
        #   "إذا ثبت، فماذا يدل ..."
        #
        # may omit the source noun because Arabic discourse
        # carries it from the prerequisite claim.
        #
        # The graph may inherit only the source/discipline
        # context here. It MUST NOT copy prerequisite
        # evidence, invent a Hadith identity, or bypass the
        # coordinator dependency gate.
        # ------------------------------------------------

        tasks_by_id = {
            task.task_id: task
            for task in plan.tasks
        }

        changed = False

        for dependency in plan.dependencies:
            prerequisite = prepared[
                dependency.prerequisite_task_id
            ][0]

            (
                dependent_understanding,
                dependent_resolution,
                _dependent_domains,
            ) = prepared[
                dependency.dependent_task_id
            ]

            if (
                dependent_understanding.primary_intent
                is not BasiraIntent.GENERAL_ISLAMIC_QUESTION
            ):
                continue

            if prerequisite.primary_intent not in {
                BasiraIntent.HADITH_AUTHENTICITY,
                BasiraIntent.HADITH_LOOKUP,
                BasiraIntent.HADITH_EXPLANATION,
            }:
                continue

            inherited_query = replace(
                dependent_understanding.query,
                # Retrieval context may inherit the
                # prerequisite's already-understood query.
                #
                # Preserve the dependent original_text and
                # intent_text: this is search context only,
                # not evidence transfer or identity proof.
                search_text=(
                    prerequisite.query.search_text
                ),
            )

            inherited = replace(
                dependent_understanding,
                query=inherited_query,
                primary_intent=(
                    BasiraIntent.HADITH_EXPLANATION
                ),
                confidence=max(
                    dependent_understanding.confidence,
                    0.75,
                ),
            )

            inherited_route = self.router.route(
                inherited
            )

            inherited = replace(
                inherited,
                context_requirement=(
                    inherited_route.context_requirement
                ),
            )

            dependent_task = tasks_by_id[
                dependency.dependent_task_id
            ]

            tasks_by_id[
                dependency.dependent_task_id
            ] = replace(
                dependent_task,
                frame=inherited_route.frame,
                context_requirement=(
                    inherited_route.context_requirement
                ),
            )

            prepared[
                dependency.dependent_task_id
            ] = (
                inherited,
                dependent_resolution,
                frozenset(
                    inherited_route.target_domains
                ),
            )

            changed = True

        if changed:
            plan = type(plan)(
                tasks=tuple(
                    tasks_by_id[
                        task.task_id
                    ]
                    for task in plan.tasks
                ),
                dependencies=plan.dependencies,
            )

        return (
            plan,
            prepared,
        )

    def _execute_public_claim_graph(
        self,
        *,
        question: str,
        quran_reference: str | None = None,
    ) -> PublicClaimGraphExecution:
        """
        Execute an already decomposed public claim graph
        through Basira's existing governed orchestration.

        Final answer aggregation is intentionally separate.
        """

        (
            plan,
            prepared,
        ) = self._plan_public_claim_graph(
            question=question,
            quran_reference=quran_reference,
        )

        if len(plan.tasks) < 2:
            raise ValueError(
                "graph execution requires multiple claims"
            )

        # Identity must be complete before any claim in
        # the graph is allowed to retrieve religious evidence.
        #
        # One ambiguous Quran claim blocks the graph from
        # silently degrading into "missing evidence".
        for task in plan.tasks:
            (
                prepared_understanding,
                prepared_resolution,
                _prepared_domains,
            ) = prepared[
                task.task_id
            ]

            if (
                _needs_quran_identity_clarification(
                    understanding=(
                        prepared_understanding
                    ),
                    resolution=(
                        prepared_resolution
                    ),
                )
            ):
                raise (
                    _QuranIdentityClarificationRequired(
                        understanding=(
                            prepared_understanding
                        ),
                        resolution=(
                            prepared_resolution
                        ),
                    )
                )

        contracts = []
        sufficiency_contracts = []

        understanding_by_claim: dict[
            str,
            BasiraQueryUnderstanding,
        ] = {}

        disciplines = set()
        binding_domains = set()

        for task in plan.tasks:
            (
                understanding,
                quran_resolution,
                target_domains,
            ) = prepared[
                task.task_id
            ]

            understanding_by_claim[
                task.claim_text
            ] = understanding

            contract = (
                self.contract_compiler
                .compile(
                    task=task,
                    quran_resolution=(
                        quran_resolution
                    ),
                )
            )

            support_domains = (
                _support_domains(
                    contract
                )
            )

            if not support_domains:
                raise RuntimeError(
                    "graph claim has no admissible "
                    "support domain"
                )

            contracts.append(
                contract
            )

            sufficiency_contracts.append(
                ClaimSufficiencyContract(
                    task_id=task.task_id,
                    support_requirements=(
                        SupportRequirement(
                            requirement_id=(
                                f"{task.task_id}:"
                                "positive-support"
                            ),
                            domains=(
                                support_domains
                            ),
                        ),
                    ),
                )
            )

            disciplines.add(
                task.frame.primary_discipline
            )

            disciplines.update(
                task.frame.secondary_disciplines
            )

            task_domains = (
                frozenset(
                    target_domains
                )
                & frozenset(
                    contract.allowed_domains
                )
            )

            if not task_domains:
                task_domains = frozenset(
                    contract.allowed_domains
                )

            binding_domains.update(
                task_domains
            )

        if not disciplines:
            raise RuntimeError(
                "graph has no governed discipline"
            )

        if not binding_domains:
            raise RuntimeError(
                "graph has no governed retrieval domain"
            )

        # One execution capability avoids broker ambiguity.
        # Per-task evidence contracts remain authoritative.
        capability_id = (
            "public-graph-capability"
        )

        capability = AgentCapability(
            capability_id=capability_id,
            agent_id=(
                "public-governed-graph-agent"
            ),
            disciplines=frozenset(
                disciplines
            ),
        )

        relation_semantic_basis_by_task: dict[
            str,
            str,
        ] = {}

        for dependency in plan.dependencies:
            (
                prerequisite_understanding,
                _prerequisite_resolution,
                _prerequisite_domains,
            ) = prepared[
                dependency.prerequisite_task_id
            ]

            (
                dependent_understanding,
                _dependent_resolution,
                _dependent_domains,
            ) = prepared[
                dependency.dependent_task_id
            ]

            # Only the bounded inheritance created during
            # graph preparation qualifies.
            #
            # Matching search_text proves that this is the
            # explicitly inherited retrieval context rather
            # than an unrelated dependent claim.
            if (
                dependent_understanding.primary_intent
                is BasiraIntent.HADITH_EXPLANATION
                and prerequisite_understanding.primary_intent
                in {
                    BasiraIntent.HADITH_AUTHENTICITY,
                    BasiraIntent.HADITH_LOOKUP,
                    BasiraIntent.HADITH_EXPLANATION,
                }
                and dependent_understanding.query.search_text
                == prerequisite_understanding.query.search_text
            ):
                relation_semantic_basis_by_task[
                    dependency.dependent_task_id
                ] = (
                    prerequisite_understanding
                    .query
                    .search_text
                )

        executor = GovernedCapabilityExecutor(
            retriever=FocusAwareRetriever(
                self.retriever
            ),
            bindings=(
                CapabilityRetrievalBinding(
                    capability_id=(
                        capability_id
                    ),
                    domains=frozenset(
                        binding_domains
                    ),
                ),
            ),
            understanding_service=(
                ClaimMappedUnderstandingService(
                    understanding_by_claim
                )
            ),
            evidence_policies=(
                ClaimEvidencePolicySet(
                    contracts=tuple(
                        contracts
                    )
                )
            ),
            relation_service=(
                PublicTaskEvidenceRelationService(
                    evaluator=(
                        PublicTaskEvidenceEvaluator()
                    ),
                    semantic_basis_by_task_id=(
                        relation_semantic_basis_by_task
                    ),
                )
            ),
            sufficiency_contracts=tuple(
                sufficiency_contracts
            ),
        )

        evaluator = (
            PublicGraphOutcomeEvaluator(
                decision_service=(
                    self.decision_service
                ),
                executor=executor,
                retrieval_projector=(
                    _semantic_retrieval
                ),
                guard=(
                    self._guard_outcome
                ),
            )
        )

        task_count = len(
            plan.tasks
        )

        ledger = ExecutionLedger(
            execution_id=(
                f"public-graph-{uuid4()}"
            ),
            plan=plan,
            budget=ExecutionBudget(
                max_claims=task_count,
                max_depth=task_count,
                max_delegations=0,
                max_agents_per_claim=1,
                max_total_agent_runs=(
                    task_count
                ),
            ),
        )

        run = AgentCoordinator(
            plan=plan,
            ledger=ledger,
            broker=CapabilityBroker(
                (capability,)
            ),
            executor=executor,
            evaluator=evaluator,
        ).run()

        return PublicClaimGraphExecution(
            plan=plan,
            run=run,
            executor=executor,
            evaluator=evaluator,
        )

    def _aggregate_public_claim_graph(
        self,
        *,
        question: str,
        execution: PublicClaimGraphExecution,
    ) -> GovernedRuntimeResult:
        """
        Publish a graph only when every claim was safely
        released.

        No new factual synthesis happens here. Each claim
        is composed and publication-verified independently;
        this layer only joins those already-verified
        results with claim labels.

        Any withheld, blocked, unresolved, missing, or
        publication-rejected claim fails the whole graph
        closed rather than disappearing from the answer.
        """

        plan = execution.plan
        run = execution.run

        base_understanding = (
            self.understanding_service
            .understand(
                question
            )
        )

        required = set(
            base_understanding
            .context_requirement
            .required
        )

        optional = set(
            base_understanding
            .context_requirement
            .optional
        )

        for task in plan.tasks:
            required.update(
                task.context_requirement.required
            )

            optional.update(
                task.context_requirement.optional
            )

        optional.difference_update(
            required
        )

        aggregate_requirement = replace(
            base_understanding.context_requirement,
            required=frozenset(
                required
            ),
            optional=frozenset(
                optional
            ),
        )

        understanding = replace(
            base_understanding,
            context_requirement=(
                aggregate_requirement
            ),
        )

        all_task_ids = {
            task.task_id
            for task in plan.tasks
        }

        released_task_ids = set(
            run.released_task_ids
        )

        graph_incomplete = (
            released_task_ids != all_task_ids
            or bool(
                run.withheld_task_ids
            )
            or bool(
                run.blocked_task_ids
            )
            or bool(
                run.unresolved_task_ids
            )
        )

        if graph_incomplete:
            return self._fail_closed(
                question=question,
                understanding=understanding,
                context_requirement=(
                    aggregate_requirement
                ),
            )

        ordered_tasks = tuple(
            plan.task(task_id)
            for task_id in (
                plan.topological_order()
            )
        )

        claim_answers = []
        claim_outcomes = []
        semantic_retrievals = []

        for task in ordered_tasks:
            outcome = (
                execution.evaluator
                .outcome_for_task(
                    task.task_id
                )
            )

            retrieval = (
                execution.evaluator
                .retrieval_for_task(
                    task.task_id
                )
            )

            relation = (
                execution.executor
                .relation_for_task(
                    task.task_id
                )
            )

            sufficiency = (
                execution.executor
                .sufficiency_for_task(
                    task.task_id
                )
            )

            if (
                outcome is None
                or retrieval is None
                or relation is None
                or sufficiency is None
            ):
                return self._fail_closed(
                    question=question,
                    understanding=understanding,
                    context_requirement=(
                        aggregate_requirement
                    ),
                )

            if outcome.decision.action not in {
                EvidenceDecisionAction.ANSWER,
                (
                    EvidenceDecisionAction
                    .ANSWER_WITH_LIMITATION
                ),
            }:
                return self._fail_closed(
                    question=question,
                    understanding=understanding,
                    context_requirement=(
                        aggregate_requirement
                    ),
                )

            answer = self.composer.compose(
                question=task.claim_text,
                outcome=outcome,
            )

            # Composition / literal-integrity /
            # semantic-verification remains authoritative.
            if (
                answer.answer is None
                or answer.action
                not in {
                    EvidenceDecisionAction.ANSWER,
                    (
                        EvidenceDecisionAction
                        .ANSWER_WITH_LIMITATION
                    ),
                }
                or (
                    answer
                    .semantic_claim_verification
                    != "pass"
                )
            ):
                return self._fail_closed(
                    question=question,
                    understanding=understanding,
                    context_requirement=(
                        aggregate_requirement
                    ),
                )

            claim_answers.append(
                (
                    task,
                    answer,
                )
            )

            claim_outcomes.append(
                outcome
            )

            semantic_retrievals.append(
                retrieval
            )

        # --------------------------------------------------------
        # Merge only semantic evidence that was actually presented
        # to each claim's decision layer.
        # --------------------------------------------------------

        evidence_by_id = {}

        unavailable_domains = set()

        for retrieval in semantic_retrievals:
            unavailable_domains.update(
                retrieval.unavailable_domains
            )

            for node in retrieval.evidence:
                evidence_by_id.setdefault(
                    node.evidence_id,
                    node,
                )

        aggregate_plan = (
            BasiraRetrievalPlanner()
            .build(
                understanding
            )
        )

        retrieval = UnifiedRetrievalResult(
            plan=aggregate_plan,
            evidence=tuple(
                evidence_by_id.values()
            ),
            unavailable_domains=frozenset(
                unavailable_domains
            ),
        )

        # Re-run the existing deterministic evidence layer over
        # the aggregate semantic evidence. This gives the public
        # QueryExecution a real aggregate EvidenceBundle rather
        # than pretending one child outcome represents the graph.
        aggregate_outcome = (
            self.decision_service
            .evaluate(
                retrieval_result=retrieval,
                expert_case_id=(
                    f"expert-{uuid4()}"
                ),
            )
        )

        if aggregate_outcome.decision.action not in {
            EvidenceDecisionAction.ANSWER,
            (
                EvidenceDecisionAction
                .ANSWER_WITH_LIMITATION
            ),
        }:
            return self._fail_closed(
                question=question,
                understanding=understanding,
                context_requirement=(
                    aggregate_requirement
                ),
            )

        # --------------------------------------------------------
        # Overall decision: limitation propagates upward.
        # --------------------------------------------------------

        overall_action = (
            EvidenceDecisionAction.ANSWER
        )

        if (
            aggregate_outcome.decision.action
            is (
                EvidenceDecisionAction
                .ANSWER_WITH_LIMITATION
            )
            or any(
                outcome.decision.action
                is (
                    EvidenceDecisionAction
                    .ANSWER_WITH_LIMITATION
                )
                for outcome
                in claim_outcomes
            )
        ):
            overall_action = (
                EvidenceDecisionAction
                .ANSWER_WITH_LIMITATION
            )

        reasons = []

        unresolved_needs = []

        for outcome in (
            *claim_outcomes,
            aggregate_outcome,
        ):
            for reason in (
                outcome.decision.reasons
            ):
                if reason not in reasons:
                    reasons.append(
                        reason
                    )

            for need in (
                outcome
                .decision
                .unresolved_needs
            ):
                if need not in unresolved_needs:
                    unresolved_needs.append(
                        need
                    )

        aggregate_outcome = replace(
            aggregate_outcome,
            decision=EvidenceDecision(
                action=overall_action,
                reasons=tuple(
                    reasons
                ),
                unresolved_needs=tuple(
                    unresolved_needs
                ),
            ),
        )

        # --------------------------------------------------------
        # Join only already verified per-claim answers.
        # No raw evidence is rendered here.
        # --------------------------------------------------------

        answer_sections = []

        citations = []

        limitations = []

        used_evidence_ids = []

        claims = []

        semantic_issues = []

        expert_review = None

        for index, (
            task,
            answer,
        ) in enumerate(
            claim_answers,
            start=1,
        ):
            answer_sections.append(
                f"{index}. {task.claim_text}\n"
                f"{answer.answer}"
            )

            citations.extend(
                answer.citations
            )

            limitations.extend(
                answer.limitations
            )

            # Per-claim composers use local claim IDs
            # such as claim-1, claim-2. Once multiple
            # verified claim answers are aggregated those
            # local IDs must be namespaced so the final
            # integrity verifier sees globally unique
            # publication claim identities.
            for claim in answer.claims:
                claims.append(
                    replace(
                        claim,
                        claim_id=(
                            f"graph-{index}-"
                            f"{claim.claim_id}"
                        ),
                    )
                )

            semantic_issues.extend(
                answer.semantic_verification_issues
            )

            for evidence_id in (
                answer.used_evidence_ids
            ):
                if (
                    evidence_id
                    not in used_evidence_ids
                ):
                    used_evidence_ids.append(
                        evidence_id
                    )

            if (
                expert_review is None
                and answer.expert_review
                is not None
            ):
                expert_review = (
                    answer.expert_review
                )

        grounded_answer = GroundedAnswer(
            question=question,
            action=overall_action,
            answer="\n\n".join(
                answer_sections
            ),
            citations=tuple(
                citations
            ),
            limitations=tuple(
                limitations
            ),
            evidence_coverage=min(
                answer.evidence_coverage
                for _, answer
                in claim_answers
            ),
            resolution_coverage=min(
                answer.resolution_coverage
                for _, answer
                in claim_answers
            ),
            used_evidence_ids=tuple(
                used_evidence_ids
            ),
            claims=tuple(
                claims
            ),
            semantic_claim_verification=(
                "pass"
            ),
            semantic_verification_issues=tuple(
                semantic_issues
            ),
            expert_review=expert_review,
        )

        return GovernedRuntimeResult(
            question=question,
            understanding=understanding,
            retrieval=retrieval,
            outcome=aggregate_outcome,
            answer=grounded_answer,
            relation=None,
            sufficiency=None,
            dependency=None,
        )

    def _execute_multi_claim_public(
        self,
        *,
        question: str,
        quran_reference: str | None = None,
    ) -> GovernedRuntimeResult:
        """
        Public multi-claim entrypoint.

        Planning/execution failures fail closed. The
        existing single-claim runtime remains untouched.
        """

        understanding = (
            self.understanding_service
            .understand(
                question
            )
        )

        try:
            execution = (
                self._execute_public_claim_graph(
                    question=question,
                    quran_reference=quran_reference,
                )
            )
        except (
            _QuranIdentityClarificationRequired
        ) as exc:
            return self._clarify_quran_identity(
                question=question,
                understanding=(
                    exc.understanding
                ),
                context_requirement=(
                    exc.understanding
                    .context_requirement
                ),
                resolution=(
                    exc.resolution
                ),
            )

        except (
            UnresolvedEvidenceIdentityError,
            CapabilityExecutionError,
        ):
            return self._fail_closed(
                question=question,
                understanding=understanding,
                context_requirement=(
                    understanding
                    .context_requirement
                ),
            )

        return self._aggregate_public_claim_graph(
            question=question,
            execution=execution,
        )

    def _clarify_quran_identity(
        self,
        *,
        question: str,
        understanding: BasiraQueryUnderstanding,
        context_requirement,
        resolution: QuranAnchorResolution,
    ) -> GovernedRuntimeResult:
        """
        Stop before religious evidence retrieval.

        Identity uncertainty is not evidence
        insufficiency.
        """
        base = self._fail_closed(
            question=question,
            understanding=understanding,
            context_requirement=(
                context_requirement
            ),
        )

        outcome = replace(
            base.outcome,
            decision=EvidenceDecision(
                action=(
                    EvidenceDecisionAction.CLARIFY
                ),
                reasons=(
                    EvidenceDecisionReason
                    .UNRESOLVED_QURAN_IDENTITY,
                ),
                unresolved_needs=(),
            ),
        )

        answer = self.composer.compose(
            question=question,
            outcome=outcome,
        )

        return replace(
            base,
            outcome=outcome,
            answer=answer,
            clarification_reason=(
                resolution.reason
            ),
            clarification_candidates=(
                resolution
                .candidate_references
            ),
        )

    def _fail_closed(
        self,
        *,
        question: str,
        understanding: BasiraQueryUnderstanding,
        context_requirement,
    ) -> GovernedRuntimeResult:
        strengthened = replace(
            understanding,
            context_requirement=context_requirement,
        )

        plan = BasiraRetrievalPlanner().build(strengthened)

        retrieval = UnifiedRetrievalResult(
            plan=plan,
            evidence=(),
            unavailable_domains=frozenset(),
        )

        outcome = self.decision_service.evaluate(
            retrieval_result=retrieval,
            expert_case_id=f"expert-{uuid4()}",
        )

        answer = self.composer.compose(
            question=question,
            outcome=outcome,
        )

        return GovernedRuntimeResult(
            question=question,
            understanding=strengthened,
            retrieval=retrieval,
            outcome=outcome,
            answer=answer,
            relation=None,
            sufficiency=None,
            dependency=None,
        )

    @staticmethod
    def _guard_outcome(
        *,
        outcome: EvidenceDecisionOutcome,
        task: ClaimTask,
        relation: TaskEvidenceRelationAssessment,
        sufficiency: ClaimSufficiencyAssessment,
        dependency: ClaimResolution | None,
    ) -> EvidenceDecisionOutcome:
        # `dependency=None` is allowed only for ClaimGraph
        # execution, where AgentCoordinator owns DAG release
        # and blocking. The legacy single-claim public path
        # continues to pass its ClaimResolution explicitly.
        if outcome.decision.action in {
            EvidenceDecisionAction.ABSTAIN,
            EvidenceDecisionAction.CLARIFY,
            EvidenceDecisionAction.ESCALATE_TO_EXPERT,
        }:
            return outcome

        unresolved = outcome.decision.unresolved_needs or tuple(
            sorted(
                task.context_requirement.required,
                key=lambda item: item.value,
            )
        )

        if relation.has_contradiction:
            return replace(
                outcome,
                decision=EvidenceDecision(
                    action=(EvidenceDecisionAction.ESCALATE_TO_EXPERT),
                    reasons=(EvidenceDecisionReason.EVIDENCE_CONFLICT,),
                    unresolved_needs=unresolved,
                ),
            )

        if (
            relation.has_unresolved_relations
            or not relation.has_positive_support
            or (sufficiency.state is not ClaimSufficiencyState.SUFFICIENT)
            or (
                dependency is not None
                and dependency.state
                is not ClaimResolutionState.READY
            )
        ):
            return replace(
                outcome,
                decision=EvidenceDecision(
                    action=(EvidenceDecisionAction.RETRIEVE_MORE),
                    reasons=(EvidenceDecisionReason.MISSING_REQUIRED_EVIDENCE,),
                    unresolved_needs=unresolved,
                ),
            )

        # E3 + dependency resolution are authoritative for
        # claim answerability. If the older query-level
        # completeness layer alone asks for more evidence,
        # preserve that limitation without bypassing the
        # mandatory semantic publication gate.
        if outcome.decision.action is EvidenceDecisionAction.RETRIEVE_MORE:
            required_values = {
                getattr(need, "value", str(need))
                for need in task.context_requirement.required
            }

            # Authenticity is not a soft enrichment.
            # When Hadith grading is required, absence of
            # attributed grading must fail closed rather
            # than publish a nearby text with a disclaimer.
            if "hadith_grade" in required_values:
                return replace(
                    outcome,
                    decision=replace(
                        outcome.decision,
                        action=(
                            EvidenceDecisionAction.ABSTAIN
                        ),
                    ),
                )

            return replace(
                outcome,
                decision=replace(
                    outcome.decision,
                    action=(
                        EvidenceDecisionAction.ANSWER_WITH_LIMITATION
                    ),
                ),
            )

        return outcome

    def execute(
        self,
        *,
        question: str,
        quran_reference: str | None = None,
    ) -> GovernedRuntimeResult:
        display_question = " ".join(question.split())

        if not display_question:
            raise ValueError("Question must not be blank.")

        claim_texts = (
            self.claim_graph_planner
            .decompose(
                display_question
            )
        )

        if len(claim_texts) > 1:
            return self._execute_multi_claim_public(
                question=display_question,
                quran_reference=quran_reference,
            )

        understanding = self.understanding_service.understand(display_question)

        understanding = (
            _promote_explicit_source_lookup(
                understanding=understanding,
                question=display_question,
            )
        )

        quran_resolution = _canonical_resolution(
            understanding=understanding,
            question=display_question,
            quran_reference=quran_reference,
            retriever=self.retriever,
        )

        understanding = _promote_quran_meaning(
            understanding=understanding,
            question=display_question,
            resolution=quran_resolution,
        )

        proposal = self.route_proposer.propose(
            understanding=understanding,
        )

        governance = self.route_governor.govern(
            understanding=understanding,
            proposal=proposal,
        )

        understanding = governance.effective_understanding

        route = self.router.route(understanding)

        # A generic Quran lookup may begin as conceptual discovery,
        # because routing alone is not allowed to invent Quran identity.
        #
        # Once the governed canonical resolver has independently
        # verified an exact Quran identity, however, the lookup is no
        # longer conceptual discovery. The canonical Quran text is the
        # direct grounding evidence for that verified coordinate.
        #
        # This does not create identity or evidence. It only aligns the
        # reasoning mode with identity that has already been verified.
        if (
            understanding.primary_intent
            is BasiraIntent.QURAN_LOOKUP
            and _is_resolved(quran_resolution)
            and route.frame.reasoning_mode
            is ReasoningMode.CONCEPTUAL_GROUNDING
        ):
            route = replace(
                route,
                frame=replace(
                    route.frame,
                    reasoning_mode=(
                        ReasoningMode.DIRECT_GROUNDING
                    ),
                ),
                routing_reasons=(
                    *route.routing_reasons,
                    (
                        "verified_quran_identity:"
                        "direct_grounding"
                    ),
                ),
            )

        understanding = replace(
            understanding,
            context_requirement=(route.context_requirement),
        )

        if (
            _needs_quran_identity_clarification(
                understanding=understanding,
                resolution=quran_resolution,
            )
        ):
            return self._clarify_quran_identity(
                question=display_question,
                understanding=understanding,
                context_requirement=(
                    route.context_requirement
                ),
                resolution=quran_resolution,
            )

        task = ClaimTask(
            task_id=f"public-claim-{uuid4()}",
            claim_text=display_question,
            frame=route.frame,
            context_requirement=(route.context_requirement),
        )

        try:
            contract = self.contract_compiler.compile(
                task=task,
                quran_resolution=quran_resolution,
            )
        except UnresolvedEvidenceIdentityError:
            return self._fail_closed(
                question=display_question,
                understanding=understanding,
                context_requirement=(route.context_requirement),
            )

        support_domains = _support_domains(contract)

        if not support_domains:
            return self._fail_closed(
                question=display_question,
                understanding=understanding,
                context_requirement=(route.context_requirement),
            )

        sufficiency_contract = ClaimSufficiencyContract(
            task_id=task.task_id,
            support_requirements=(
                SupportRequirement(
                    requirement_id=(f"{task.task_id}:positive-support"),
                    domains=support_domains,
                ),
            ),
        )

        capability_id = f"public-capability-{task.task_id}"

        capability = AgentCapability(
            capability_id=capability_id,
            agent_id="public-governed-agent",
            disciplines=frozenset(
                (
                    route.frame.primary_discipline,
                    *route.frame.secondary_disciplines,
                )
            ),
        )

        binding_domains = frozenset(route.target_domains) & frozenset(
            contract.allowed_domains
        )

        if not binding_domains:
            binding_domains = frozenset(contract.allowed_domains)

        executor = GovernedCapabilityExecutor(
            retriever=FocusAwareRetriever(self.retriever),
            bindings=(
                CapabilityRetrievalBinding(
                    capability_id=capability_id,
                    domains=binding_domains,
                ),
            ),
            understanding_service=(FrozenUnderstandingService(understanding)),
            evidence_policies=(ClaimEvidencePolicySet(contracts=(contract,))),
            relation_service=(
                PublicTaskEvidenceRelationService(
                    evaluator=(
                        PublicTaskEvidenceEvaluator()
                    )
                )
            ),
            sufficiency_contracts=(sufficiency_contract,),
        )

        try:
            product = executor.execute(
                task=task,
                capability=capability,
                delegation=None,
            )
        except CapabilityExecutionError:
            return self._fail_closed(
                question=display_question,
                understanding=understanding,
                context_requirement=(route.context_requirement),
            )

        relation = executor.relation_for_task(task.task_id)
        sufficiency = executor.sufficiency_for_task(task.task_id)

        if relation is None or sufficiency is None:
            return self._fail_closed(
                question=display_question,
                understanding=understanding,
                context_requirement=(route.context_requirement),
            )

        dependency = executor.resolve_claim_dependencies().for_task(task.task_id)

        retrieval = _semantic_retrieval(
            retrieval=product.retrieval_result,
            relation=relation,
        )

        outcome = self.decision_service.evaluate(
            retrieval_result=retrieval,
            expert_case_id=f"expert-{uuid4()}",
        )

        outcome = self._guard_outcome(
            outcome=outcome,
            task=task,
            relation=relation,
            sufficiency=sufficiency,
            dependency=dependency,
        )

        answer = self.composer.compose(
            question=display_question,
            outcome=outcome,
        )

        return GovernedRuntimeResult(
            question=display_question,
            understanding=understanding,
            retrieval=retrieval,
            outcome=outcome,
            answer=answer,
            relation=relation,
            sufficiency=sufficiency,
            dependency=dependency,
        )
