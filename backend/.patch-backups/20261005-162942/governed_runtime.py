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
from basira.evidence.decision import (
    EvidenceDecision,
    EvidenceDecisionAction,
    EvidenceDecisionReason,
)
from basira.evidence.models import EvidenceDomain, EvidenceNode
from basira.evidence.service import (
    EvidenceDecisionOutcome,
    EvidenceDecisionService,
)
from basira.orchestration.capability_executor import (
    CapabilityExecutionError,
    CapabilityRetrievalBinding,
    GovernedCapabilityExecutor,
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


def _focused_excerpt(
    text: str,
    terms: tuple[str, ...],
    *,
    before: int = 150,
    after: int = 760,
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

            score = (3 if original_start >= 120 else 0) + (
                4 if any(cue in local for cue in cues) else 0
            )

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
            item[1],
        ),
    )

    excerpt = text[max(0, start - before) : min(len(text), end + after)].strip()

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

        terms = semantic_terms(plan.understanding.query.original_text)

        if not terms:
            return result

        evidence: list[EvidenceNode] = []
        seen_tafsir: set[tuple[str, str]] = set()

        for node in result.evidence:
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

            evidence.append(
                replace(
                    node,
                    text=excerpt,
                    claim_type=(node.claim_type or "tafsir_focus"),
                )
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

        if (
            evidence.domain is EvidenceDomain.QURAN
            and task.frame.reasoning_mode is ReasoningMode.INTERPRETATION
        ):
            relation = ClaimEvidenceRelation.CONTEXT_ONLY
        elif not terms:
            relation = ClaimEvidenceRelation.SUPPORTS
        else:
            candidate = normalize_semantic_text(
                " ".join(
                    item
                    for item in (
                        evidence.text,
                        evidence.text if evidence.claim_type == "hadith_grade" else "",
                    )
                    if item
                )
            )

            relation = (
                ClaimEvidenceRelation.SUPPORTS
                if any(term in candidate for term in terms)
                else ClaimEvidenceRelation.IRRELEVANT
            )

        return ClaimEvidenceRelationRecord(
            task_id=task.task_id,
            evidence_id=evidence.evidence_id,
            relation=relation,
            origin=RelationOrigin.DETERMINISTIC,
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


def _canonical_resolution(
    *,
    understanding: BasiraQueryUnderstanding,
    question: str,
    quran_reference: str | None,
    retriever: BasiraUnifiedRetriever,
) -> QuranAnchorResolution | None:
    resolver = _resolver(retriever)

    if resolver is not None:
        resolution = resolver.resolve(understanding)

        if _is_resolved(resolution):
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

    return None


def _promote_quran_meaning(
    *,
    understanding: BasiraQueryUnderstanding,
    question: str,
    resolution: QuranAnchorResolution | None,
) -> BasiraQueryUnderstanding:
    if not _is_resolved(resolution):
        return understanding

    if understanding.primary_intent is not BasiraIntent.GENERAL_ISLAMIC_QUESTION:
        return understanding

    normalized = normalize_semantic_text(question)

    if any(normalize_semantic_text(cue) in normalized for cue in _MEANING_CUES):
        return replace(
            understanding,
            primary_intent=BasiraIntent.QURAN_MEANING,
            confidence=max(
                understanding.confidence,
                0.95,
            ),
        )

    if (
        resolution is not None
        and resolution.reason == "validated_named_quran_reference"
    ):
        named_lookup_forms = {
            normalize_semantic_text(alias) for alias in _NAMED_QURAN_REFERENCES
        }

        if normalized in named_lookup_forms:
            return replace(
                understanding,
                primary_intent=BasiraIntent.QURAN_LOOKUP,
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

        self.contract_compiler = TaskEvidenceContractCompiler()

        self.decision_service = EvidenceDecisionService()

        publication_authorizer = getattr(
            retriever,
            "publication_authorizer",
            None,
        )

        if publication_authorizer is None:
            publication_authorizer = DenyAllPublicationAuthorizer()

        self.composer = GovernedGroundedAnswerComposer(
            publication_authorizer=(publication_authorizer),
            semantic_verifier=(semantic_verifier or build_public_semantic_verifier()),
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
        dependency: ClaimResolution,
    ) -> EvidenceDecisionOutcome:
        if outcome.decision.action in {
            EvidenceDecisionAction.ABSTAIN,
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
            or (dependency.state is not ClaimResolutionState.READY)
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
            return replace(
                outcome,
                decision=replace(
                    outcome.decision,
                    action=(EvidenceDecisionAction.ANSWER_WITH_LIMITATION),
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

        understanding = self.understanding_service.understand(display_question)

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

        understanding = replace(
            understanding,
            context_requirement=(route.context_requirement),
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
                TaskEvidenceRelationService(evaluator=(PublicTaskEvidenceEvaluator()))
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
