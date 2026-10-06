from __future__ import annotations

from dataclasses import dataclass

from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
    EvidenceNeed,
)
from basira.reasoning.contracts import (
    AnswerConstraint,
    EvidenceObligation,
    ReasoningMode,
    ReligiousDiscipline,
    ReligiousReasoningFrame,
    classical_fiqh_comparison_frame,
    contemporary_fiqh_frame,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
)


class UnmappedEvidenceObligationError(RuntimeError):
    pass


_OBLIGATION_NEEDS: dict[
    EvidenceObligation,
    frozenset[EvidenceNeed],
] = {
    EvidenceObligation.EXACT_CANONICAL_TEXT: frozenset(
        {
            EvidenceNeed.CANONICAL_TEXT,
        }
    ),
    EvidenceObligation.SOURCE_ATTRIBUTION: frozenset(
        {
            EvidenceNeed.SOURCE_PROVENANCE,
        }
    ),
    EvidenceObligation.HADITH_TEXT: frozenset(
        {
            EvidenceNeed.HADITH_TEXT,
        }
    ),
    EvidenceObligation.HADITH_GRADING: frozenset(
        {
            EvidenceNeed.HADITH_GRADE,
        }
    ),
    EvidenceObligation.TAFSIR_CONTEXT: frozenset(
        {
            EvidenceNeed.TAFSIR,
        }
    ),
    EvidenceObligation.REVELATION_CONTEXT: frozenset(
        {
            EvidenceNeed.REVELATION_CONTEXT,
        }
    ),
    EvidenceObligation.CLASSICAL_FIQH_POSITION: frozenset(
        {
            EvidenceNeed.FIQH_EVIDENCE,
        }
    ),
    EvidenceObligation.MADHHAB_SCOPE: frozenset(
        {
            EvidenceNeed.FIQH_CONSTRAINTS,
            EvidenceNeed.FIQH_MADHHAB_SCOPE,
        }
    ),
    EvidenceObligation.USUL_PRINCIPLE: frozenset(
        {
            EvidenceNeed.FIQH_EVIDENCE,
        }
    ),
    EvidenceObligation.LEGAL_RATIONALE: frozenset(
        {
            EvidenceNeed.FIQH_EVIDENCE,
        }
    ),
    EvidenceObligation.CONDITIONS: frozenset(
        {
            EvidenceNeed.FIQH_CONSTRAINTS,
            EvidenceNeed.FIQH_CONDITIONS,
        }
    ),
    EvidenceObligation.EXCEPTIONS: frozenset(
        {
            EvidenceNeed.FIQH_CONSTRAINTS,
            EvidenceNeed.FIQH_EXCEPTIONS,
        }
    ),
    EvidenceObligation.CONTEMPORARY_GUIDANCE: frozenset(
        {
            EvidenceNeed.CONTEMPORARY_GUIDANCE,
        }
    ),
    EvidenceObligation.CONTEMPORARY_FACTS: frozenset(
        {
            EvidenceNeed.APPLICABILITY_CONDITIONS,
        }
    ),
    EvidenceObligation.TEMPORAL_CONTEXT: frozenset(
        {
            EvidenceNeed.APPLICABILITY_CONDITIONS,
        }
    ),
    EvidenceObligation.JURISDICTION_CONTEXT: frozenset(
        {
            EvidenceNeed.APPLICABILITY_CONDITIONS,
        }
    ),
    EvidenceObligation.INSTITUTION_ATTRIBUTION: frozenset(
        {
            EvidenceNeed.ACTOR_AUTHORITY,
            EvidenceNeed.SOURCE_PROVENANCE,
        }
    ),
    EvidenceObligation.DOCUMENTED_DISAGREEMENT: frozenset(
        {
            EvidenceNeed.FIQH_EVIDENCE,
            EvidenceNeed.FIQH_CONSTRAINTS,
            EvidenceNeed.FIQH_DISAGREEMENT,
        }
    ),
}


_DISCIPLINE_DOMAINS: dict[
    ReligiousDiscipline,
    tuple[EvidenceDomain, ...],
] = {
    ReligiousDiscipline.QURAN: (EvidenceDomain.QURAN,),
    ReligiousDiscipline.HADITH: (EvidenceDomain.HADITH,),
    ReligiousDiscipline.TAFSIR: (EvidenceDomain.TAFSIR,),
    ReligiousDiscipline.ASBAB_AL_NUZUL: (EvidenceDomain.REVELATION_CONTEXT,),
    ReligiousDiscipline.AQIDAH: (EvidenceDomain.AQIDAH,),
    ReligiousDiscipline.FIQH: (EvidenceDomain.FIQH,),
    ReligiousDiscipline.USUL_AL_FIQH: (EvidenceDomain.FIQH,),
    ReligiousDiscipline.CONTEMPORARY_FIQH: (EvidenceDomain.FATWA,),
    ReligiousDiscipline.SIRAH: (EvidenceDomain.SIRA,),
    ReligiousDiscipline.MAWARITH: (EvidenceDomain.FIQH,),
    ReligiousDiscipline.CROSS_DISCIPLINARY: (EvidenceDomain.GENERAL,),
}


_COMPARATIVE_CUES = (
    "المذاهب",
    "المذهب",
    "الاقوال",
    "الأقوال",
    "الخلاف",
    "اختلف",
    "اختلاف",
    "مقارنة",
    "الحنفي",
    "المالكي",
    "الشافعي",
    "الحنبلي",
)


_CONTEMPORARY_CUES = (
    "معاصر",
    "العملات الرقمية",
    "عملة رقمية",
    "بيتكوين",
    "bitcoin",
    "crypto",
    "بنك",
    "البنوك",
    "بطاقة ائتمان",
    "التامين",
    "التأمين",
    "اسهم",
    "أسهم",
    "etf",
    "تمويل",
    "مرابحة",
    "الذكاء الاصطناعي",
    "اطفال الانابيب",
    "أطفال الأنابيب",
    "زرع الاعضاء",
    "زرع الأعضاء",
    "نقل الاعضاء",
    "نقل الأعضاء",
)


_CONTESTED_CUES = (
    "شبهة",
    "يزعم",
    "يدعي",
    "يدّعي",
    "هل صحيح ان",
    "هل صحيح أن",
    "هل حقا",
    "هل حقًا",
    "تناقض",
    "يناقض",
    "تعارض",
    "يتعارض",
    "كيف نرد",
    "الرد على",
)


_MAWARITH_CUES = (
    "ميراث",
    "الميراث",
    "مواريث",
    "الفرائض",
    "تركة",
    "التركة",
)


def _contains_any(
    text: str,
    cues: tuple[str, ...],
) -> bool:
    return any(cue in text for cue in cues)


class ReasoningEvidenceAdapter:
    """
    Map the new reasoning obligations into Basira's
    existing enforceable EvidenceNeed contract.

    The adapter may only strengthen an existing
    ContextRequirement. It never removes a baseline
    requirement.

    Unmapped obligations fail closed.
    """

    def required_needs_for(
        self,
        frame: ReligiousReasoningFrame,
    ) -> frozenset[EvidenceNeed]:
        required: set[EvidenceNeed] = {
            EvidenceNeed.SOURCE_PROVENANCE,
        }

        for obligation in frame.obligations:
            needs = _OBLIGATION_NEEDS.get(obligation)

            if needs is None:
                raise (
                    UnmappedEvidenceObligationError(
                        "No EvidenceNeed mapping "
                        "for reasoning obligation: "
                        f"{obligation.value}"
                    )
                )

            required.update(needs)

        return frozenset(required)

    def strengthen(
        self,
        *,
        baseline: ContextRequirement,
        frame: ReligiousReasoningFrame,
    ) -> ContextRequirement:
        required = set(baseline.required)

        required.update(self.required_needs_for(frame))

        optional = set(baseline.optional) - required

        return ContextRequirement(
            required=frozenset(required),
            optional=frozenset(optional),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ReligiousReasoningRoute:
    frame: ReligiousReasoningFrame

    context_requirement: ContextRequirement

    target_domains: tuple[
        EvidenceDomain,
        ...,
    ]

    routing_reasons: tuple[
        str,
        ...,
    ]


class ReligiousReasoningRouter:
    """
    Deterministic bridge between the existing query
    understanding layer and the richer religious
    reasoning contract.

    This is not a semantic verifier.

    Routing decisions remain inspectable through
    routing_reasons.
    """

    def __init__(
        self,
        *,
        evidence_adapter: (ReasoningEvidenceAdapter | None) = None,
    ) -> None:
        self._evidence_adapter = evidence_adapter or ReasoningEvidenceAdapter()

    def route(
        self,
        understanding: (BasiraQueryUnderstanding),
    ) -> ReligiousReasoningRoute:
        frame, reasons = self._build_frame(understanding)

        requirement = self._evidence_adapter.strengthen(
            baseline=(understanding.context_requirement),
            frame=frame,
        )

        return ReligiousReasoningRoute(
            frame=frame,
            context_requirement=(requirement),
            target_domains=(self._target_domains(frame)),
            routing_reasons=tuple(reasons),
        )

    def _build_frame(
        self,
        understanding: (BasiraQueryUnderstanding),
    ) -> tuple[
        ReligiousReasoningFrame,
        list[str],
    ]:
        intent = understanding.primary_intent

        text = understanding.query.intent_text

        question = understanding.query.original_text

        reasons = [(f"baseline_intent:{intent.value}")]

        if _contains_any(
            text,
            _MAWARITH_CUES,
        ):
            reasons.append("explicit_cue:mawarith")

            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:mawarith"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.MAWARITH),
                    secondary_disciplines=(ReligiousDiscipline.FIQH,),
                    reasoning_mode=(ReasoningMode.DETERMINISTIC_CALCULATION),
                    obligations=(
                        EvidenceObligation.CLASSICAL_FIQH_POSITION,
                        EvidenceObligation.CONDITIONS,
                        EvidenceObligation.SOURCE_ATTRIBUTION,
                    ),
                    constraints=(AnswerConstraint.PRESERVE_CONDITIONS,),
                ),
                reasons,
            )

        if intent is BasiraIntent.QURAN_LOOKUP:
            exact_text_request = _contains_any(
                text,
                (
                    "هات نص الاية",
                    "هات نص الآية",
                    "ما نص الاية",
                    "ما نص الآية",
                    "اذكر الاية",
                    "اذكر الآية",
                    "اكتب الاية",
                    "اكتب الآية",
                    "نص الاية",
                    "نص الآية",
                ),
            )

            if exact_text_request:
                reasons.append(
                    "explicit_cue:quran_exact_text_request"
                )
                reasoning_mode = (
                    ReasoningMode.DIRECT_GROUNDING
                )
            else:
                reasons.append(
                    "quran_lookup:conceptual_discovery"
                )
                reasoning_mode = (
                    ReasoningMode.CONCEPTUAL_GROUNDING
                )

            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:quran_lookup"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.QURAN),
                    reasoning_mode=reasoning_mode,
                    obligations=(
                        EvidenceObligation.EXACT_CANONICAL_TEXT,
                        EvidenceObligation.SOURCE_ATTRIBUTION,
                    ),
                ),
                reasons,
            )

        if intent is BasiraIntent.QURAN_MEANING:
            if _contains_any(
                text,
                _CONTESTED_CUES,
            ):
                reasons.append("explicit_cue:contested_claim")

                return (
                    self._quran_contested(question),
                    reasons,
                )

            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:quran_meaning"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.QURAN),
                    secondary_disciplines=(ReligiousDiscipline.TAFSIR,),
                    reasoning_mode=(ReasoningMode.INTERPRETATION),
                    obligations=(
                        EvidenceObligation.EXACT_CANONICAL_TEXT,
                        EvidenceObligation.TAFSIR_CONTEXT,
                        EvidenceObligation.SOURCE_ATTRIBUTION,
                    ),
                    constraints=(AnswerConstraint.REQUIRE_CONTEXT_BEFORE_CONCLUSION,),
                ),
                reasons,
            )

        if intent is BasiraIntent.TAFSIR_CONTEXT:
            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:tafsir_context"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.QURAN),
                    secondary_disciplines=(
                        ReligiousDiscipline.TAFSIR,
                        ReligiousDiscipline.ASBAB_AL_NUZUL,
                    ),
                    reasoning_mode=(ReasoningMode.INTERPRETATION),
                    obligations=(
                        EvidenceObligation.EXACT_CANONICAL_TEXT,
                        EvidenceObligation.TAFSIR_CONTEXT,
                        EvidenceObligation.REVELATION_CONTEXT,
                        EvidenceObligation.SOURCE_ATTRIBUTION,
                    ),
                    constraints=(AnswerConstraint.REQUIRE_CONTEXT_BEFORE_CONCLUSION,),
                ),
                reasons,
            )

        if intent is BasiraIntent.HADITH_AUTHENTICITY:
            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:hadith_authenticity"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.HADITH),
                    reasoning_mode=(ReasoningMode.AUTHENTICITY),
                    obligations=(
                        EvidenceObligation.HADITH_TEXT,
                        EvidenceObligation.HADITH_GRADING,
                        EvidenceObligation.SOURCE_ATTRIBUTION,
                    ),
                    constraints=(AnswerConstraint.ATTRIBUTE_OPINIONS,),
                ),
                reasons,
            )

        if intent is BasiraIntent.HADITH_LOOKUP:
            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:hadith_lookup"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.HADITH),
                    reasoning_mode=(ReasoningMode.DIRECT_GROUNDING),
                    obligations=(
                        EvidenceObligation.HADITH_TEXT,
                        EvidenceObligation.SOURCE_ATTRIBUTION,
                    ),
                ),
                reasons,
            )

        if intent is BasiraIntent.HADITH_EXPLANATION:
            if _contains_any(
                text,
                _CONTESTED_CUES,
            ):
                reasons.append("explicit_cue:contested_claim")

                return (
                    self._hadith_contested(question),
                    reasons,
                )

            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:hadith_explanation"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.HADITH),
                    reasoning_mode=(ReasoningMode.INTERPRETATION),
                    obligations=(
                        EvidenceObligation.HADITH_TEXT,
                        EvidenceObligation.SOURCE_ATTRIBUTION,
                    ),
                    constraints=(AnswerConstraint.REQUIRE_CONTEXT_BEFORE_CONCLUSION,),
                ),
                reasons,
            )

        if intent is BasiraIntent.FIQH_QUESTION:
            if _contains_any(
                text,
                _CONTEMPORARY_CUES,
            ):
                reasons.append("explicit_cue:contemporary_fiqh")

                return (
                    contemporary_fiqh_frame(
                        frame_id=("reasoning:contemporary_fiqh"),
                        question=question,
                    ),
                    reasons,
                )

            if _contains_any(
                text,
                _CONTESTED_CUES,
            ):
                reasons.append("explicit_cue:contested_claim")

                return (
                    self._fiqh_contested(question),
                    reasons,
                )

            if _contains_any(
                text,
                _COMPARATIVE_CUES,
            ):
                reasons.append("explicit_cue:comparative_fiqh")

                return (
                    classical_fiqh_comparison_frame(
                        frame_id=("reasoning:comparative_fiqh"),
                        question=question,
                    ),
                    reasons,
                )

            return (
                self._classical_fiqh_ruling(question),
                reasons,
            )

        if intent is BasiraIntent.FATWA_LOOKUP:
            reasons.append("baseline_intent:fatwa_as_contemporary")

            return (
                contemporary_fiqh_frame(
                    frame_id=("reasoning:fatwa"),
                    question=question,
                ),
                reasons,
            )

        if intent is BasiraIntent.THEOLOGY:
            if _contains_any(
                text,
                _CONTESTED_CUES,
            ):
                reasons.append("explicit_cue:contested_claim")

                return (
                    self._aqidah_contested(question),
                    reasons,
                )

            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:aqidah"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.AQIDAH),
                    reasoning_mode=(ReasoningMode.DIRECT_GROUNDING),
                    obligations=(EvidenceObligation.SOURCE_ATTRIBUTION,),
                    constraints=(AnswerConstraint.ATTRIBUTE_OPINIONS,),
                ),
                reasons,
            )

        if intent is BasiraIntent.HISTORICAL_CONTEXT:
            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:sirah"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.SIRAH),
                    reasoning_mode=(ReasoningMode.INTERPRETATION),
                    obligations=(EvidenceObligation.SOURCE_ATTRIBUTION,),
                    constraints=(AnswerConstraint.REQUIRE_CONTEXT_BEFORE_CONCLUSION,),
                ),
                reasons,
            )

        if intent in {
            BasiraIntent.SOURCE_VERIFICATION,
            BasiraIntent.QUOTE_VERIFICATION,
        }:
            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:source_verification"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.CROSS_DISCIPLINARY),
                    reasoning_mode=(ReasoningMode.DIRECT_GROUNDING),
                    obligations=(EvidenceObligation.SOURCE_ATTRIBUTION,),
                ),
                reasons,
            )

        if _contains_any(
            text,
            _CONTESTED_CUES,
        ):
            reasons.append("explicit_cue:contested_claim")

            return (
                ReligiousReasoningFrame(
                    frame_id=("reasoning:cross_discipline_contested"),
                    question=question,
                    primary_discipline=(ReligiousDiscipline.CROSS_DISCIPLINARY),
                    reasoning_mode=(ReasoningMode.CONTESTED_CLAIM),
                    obligations=(EvidenceObligation.SOURCE_ATTRIBUTION,),
                    constraints=(
                        AnswerConstraint.DO_NOT_ACCEPT_PREMISE_AS_FACT,
                        AnswerConstraint.REQUIRE_CONTEXT_BEFORE_CONCLUSION,
                    ),
                ),
                reasons,
            )

        return (
            ReligiousReasoningFrame(
                frame_id=("reasoning:general"),
                question=question,
                primary_discipline=(ReligiousDiscipline.CROSS_DISCIPLINARY),
                reasoning_mode=(ReasoningMode.DIRECT_GROUNDING),
                obligations=(EvidenceObligation.SOURCE_ATTRIBUTION,),
            ),
            reasons,
        )

    @staticmethod
    def _classical_fiqh_ruling(
        question: str,
    ) -> ReligiousReasoningFrame:
        return ReligiousReasoningFrame(
            frame_id=("reasoning:classical_fiqh_ruling"),
            question=question,
            primary_discipline=(ReligiousDiscipline.FIQH),
            secondary_disciplines=(ReligiousDiscipline.USUL_AL_FIQH,),
            reasoning_mode=(ReasoningMode.LEGAL_RULING),
            obligations=(
                EvidenceObligation.CLASSICAL_FIQH_POSITION,
                EvidenceObligation.MADHHAB_SCOPE,
                EvidenceObligation.SOURCE_ATTRIBUTION,
            ),
            constraints=(
                AnswerConstraint.ATTRIBUTE_OPINIONS,
                AnswerConstraint.DO_NOT_CLAIM_CONSENSUS,
                AnswerConstraint.PRESERVE_CONDITIONS,
                AnswerConstraint.PRESERVE_EXCEPTIONS,
            ),
        )

    @staticmethod
    def _fiqh_contested(
        question: str,
    ) -> ReligiousReasoningFrame:
        return ReligiousReasoningFrame(
            frame_id=("reasoning:fiqh_contested_claim"),
            question=question,
            primary_discipline=(ReligiousDiscipline.FIQH),
            secondary_disciplines=(ReligiousDiscipline.USUL_AL_FIQH,),
            reasoning_mode=(ReasoningMode.CONTESTED_CLAIM),
            obligations=(
                EvidenceObligation.CLASSICAL_FIQH_POSITION,
                EvidenceObligation.MADHHAB_SCOPE,
                EvidenceObligation.CONDITIONS,
                EvidenceObligation.DOCUMENTED_DISAGREEMENT,
                EvidenceObligation.SOURCE_ATTRIBUTION,
            ),
            constraints=(
                AnswerConstraint.DO_NOT_ACCEPT_PREMISE_AS_FACT,
                AnswerConstraint.REQUIRE_CONTEXT_BEFORE_CONCLUSION,
                AnswerConstraint.PRESERVE_DISAGREEMENT,
                AnswerConstraint.DO_NOT_CLAIM_CONSENSUS,
                AnswerConstraint.DO_NOT_COLLAPSE_MADHHABS,
            ),
        )

    @staticmethod
    def _hadith_contested(
        question: str,
    ) -> ReligiousReasoningFrame:
        return ReligiousReasoningFrame(
            frame_id=("reasoning:hadith_contested_claim"),
            question=question,
            primary_discipline=(ReligiousDiscipline.HADITH),
            reasoning_mode=(ReasoningMode.CONTESTED_CLAIM),
            obligations=(
                EvidenceObligation.HADITH_TEXT,
                EvidenceObligation.HADITH_GRADING,
                EvidenceObligation.SOURCE_ATTRIBUTION,
            ),
            constraints=(
                AnswerConstraint.DO_NOT_ACCEPT_PREMISE_AS_FACT,
                AnswerConstraint.REQUIRE_CONTEXT_BEFORE_CONCLUSION,
            ),
        )

    @staticmethod
    def _quran_contested(
        question: str,
    ) -> ReligiousReasoningFrame:
        return ReligiousReasoningFrame(
            frame_id=("reasoning:quran_contested_claim"),
            question=question,
            primary_discipline=(ReligiousDiscipline.QURAN),
            secondary_disciplines=(ReligiousDiscipline.TAFSIR,),
            reasoning_mode=(ReasoningMode.CONTESTED_CLAIM),
            obligations=(
                EvidenceObligation.EXACT_CANONICAL_TEXT,
                EvidenceObligation.TAFSIR_CONTEXT,
                EvidenceObligation.SOURCE_ATTRIBUTION,
            ),
            constraints=(
                AnswerConstraint.DO_NOT_ACCEPT_PREMISE_AS_FACT,
                AnswerConstraint.REQUIRE_CONTEXT_BEFORE_CONCLUSION,
            ),
        )

    @staticmethod
    def _aqidah_contested(
        question: str,
    ) -> ReligiousReasoningFrame:
        return ReligiousReasoningFrame(
            frame_id=("reasoning:aqidah_contested_claim"),
            question=question,
            primary_discipline=(ReligiousDiscipline.AQIDAH),
            reasoning_mode=(ReasoningMode.CONTESTED_CLAIM),
            obligations=(EvidenceObligation.SOURCE_ATTRIBUTION,),
            constraints=(
                AnswerConstraint.DO_NOT_ACCEPT_PREMISE_AS_FACT,
                AnswerConstraint.REQUIRE_CONTEXT_BEFORE_CONCLUSION,
            ),
        )

    @staticmethod
    def _target_domains(
        frame: ReligiousReasoningFrame,
    ) -> tuple[
        EvidenceDomain,
        ...,
    ]:
        disciplines = (
            frame.primary_discipline,
            *frame.secondary_disciplines,
        )

        targets: list[EvidenceDomain] = []

        seen: set[EvidenceDomain] = set()

        for discipline in disciplines:
            domains = _DISCIPLINE_DOMAINS.get(discipline)

            if domains is None:
                raise RuntimeError(
                    f"No evidence domain mapping for discipline: {discipline.value}"
                )

            for domain in domains:
                if domain in seen:
                    continue

                seen.add(domain)
                targets.append(domain)

        return tuple(targets)


def evidence_domains_for_discipline(
    discipline: ReligiousDiscipline,
) -> tuple[
    EvidenceDomain,
    ...,
]:
    """
    Public read-only projection from a semantic
    religious discipline into evidence domains.

    This does not grant source authority. It only
    preserves the domain contract already owned by
    the reasoning layer.
    """

    domains = _DISCIPLINE_DOMAINS.get(discipline)

    if domains is None:
        raise RuntimeError(
            f"No evidence domain mapping for discipline: {discipline.value}"
        )

    return tuple(domains)


def evidence_domains_for_frame(
    frame: ReligiousReasoningFrame,
) -> tuple[
    EvidenceDomain,
    ...,
]:
    """
    Return deduplicated evidence domains described by
    the frame's primary + secondary disciplines.
    """

    disciplines = (
        frame.primary_discipline,
        *frame.secondary_disciplines,
    )

    result: list[EvidenceDomain] = []

    seen: set[EvidenceDomain] = set()

    for discipline in disciplines:
        for domain in evidence_domains_for_discipline(discipline):
            if domain in seen:
                continue

            seen.add(domain)
            result.append(domain)

    return tuple(result)
