from __future__ import annotations

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
)
from basira.reasoning.routing import (
    ReasoningEvidenceAdapter,
    ReligiousReasoningRouter,
)
from basira.retrieval.arabic_query import (
    build_arabic_query,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
)


def _understanding(
    text: str,
    intent: BasiraIntent,
    *,
    required: frozenset[EvidenceNeed] = frozenset(),
    optional: frozenset[EvidenceNeed] = frozenset(),
) -> BasiraQueryUnderstanding:
    return BasiraQueryUnderstanding(
        query=build_arabic_query(text),
        primary_intent=intent,
        risk_tags=frozenset(),
        entities=(),
        context_requirement=(
            ContextRequirement(
                required=required,
                optional=optional,
            )
        ),
        confidence=1.0,
    )


def test_adapter_maps_every_reasoning_obligation() -> None:
    frame = ReligiousReasoningFrame(
        frame_id="all-obligations",
        question="test",
        primary_discipline=(ReligiousDiscipline.CROSS_DISCIPLINARY),
        reasoning_mode=(ReasoningMode.DIRECT_GROUNDING),
        obligations=tuple(EvidenceObligation),
    )

    needs = ReasoningEvidenceAdapter().required_needs_for(frame)

    assert EvidenceNeed.SOURCE_PROVENANCE in needs

    assert EvidenceNeed.CONTEMPORARY_GUIDANCE in needs

    assert EvidenceNeed.FIQH_EVIDENCE in needs


def test_reasoning_adapter_never_weakens_baseline() -> None:
    baseline = ContextRequirement(
        required=frozenset(
            {
                EvidenceNeed.RELATED_HADITH,
            }
        ),
        optional=frozenset(
            {
                EvidenceNeed.TAFSIR,
            }
        ),
    )

    frame = ReligiousReasoningFrame(
        frame_id="frame-1",
        question="test",
        primary_discipline=(ReligiousDiscipline.HADITH),
        reasoning_mode=(ReasoningMode.AUTHENTICITY),
        obligations=(
            EvidenceObligation.HADITH_TEXT,
            EvidenceObligation.HADITH_GRADING,
        ),
    )

    result = ReasoningEvidenceAdapter().strengthen(
        baseline=baseline,
        frame=frame,
    )

    assert EvidenceNeed.RELATED_HADITH in result.required

    assert EvidenceNeed.HADITH_TEXT in result.required

    assert EvidenceNeed.HADITH_GRADE in result.required

    assert EvidenceNeed.SOURCE_PROVENANCE in result.required

    assert EvidenceNeed.TAFSIR in result.optional


def test_hadith_authenticity_routes_to_grade() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            "هل هذا الحديث صحيح؟",
            BasiraIntent.HADITH_AUTHENTICITY,
        )
    )

    assert route.frame.primary_discipline is ReligiousDiscipline.HADITH

    assert route.frame.reasoning_mode is ReasoningMode.AUTHENTICITY

    assert EvidenceNeed.HADITH_TEXT in route.context_requirement.required

    assert EvidenceNeed.HADITH_GRADE in route.context_requirement.required

    assert route.target_domains == (EvidenceDomain.HADITH,)


def test_quran_meaning_requires_tafsir_context() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            "ما معنى الآية؟",
            BasiraIntent.QURAN_MEANING,
        )
    )

    assert route.frame.reasoning_mode is ReasoningMode.INTERPRETATION

    assert EvidenceNeed.CANONICAL_TEXT in route.context_requirement.required

    assert EvidenceNeed.TAFSIR in route.context_requirement.required

    assert route.target_domains == (
        EvidenceDomain.QURAN,
        EvidenceDomain.TAFSIR,
    )


def test_fiqh_comparison_preserves_disagreement() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            ("ما أقوال المذاهب في هذه المسألة؟"),
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert route.frame.reasoning_mode is ReasoningMode.COMPARATIVE

    assert AnswerConstraint.PRESERVE_DISAGREEMENT in route.frame.constraints

    assert AnswerConstraint.DO_NOT_COLLAPSE_MADHHABS in route.frame.constraints

    assert EvidenceNeed.FIQH_EVIDENCE in route.context_requirement.required

    assert EvidenceNeed.FIQH_CONSTRAINTS in route.context_requirement.required


def test_contemporary_fiqh_routes_to_fatwa_and_fiqh() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            "ما حكم البيتكوين؟",
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert route.frame.primary_discipline is ReligiousDiscipline.CONTEMPORARY_FIQH

    assert route.frame.reasoning_mode is ReasoningMode.CONTEMPORARY_APPLICATION

    assert route.target_domains == (
        EvidenceDomain.FATWA,
        EvidenceDomain.FIQH,
    )

    assert EvidenceNeed.CONTEMPORARY_GUIDANCE in route.context_requirement.required

    assert EvidenceNeed.APPLICABILITY_CONDITIONS in route.context_requirement.required

    assert EvidenceNeed.ACTOR_AUTHORITY in route.context_requirement.required


def test_fatwa_intent_uses_contemporary_contract() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            "فتوى عن معاملة حديثة",
            BasiraIntent.FATWA_LOOKUP,
        )
    )

    assert route.frame.primary_discipline is ReligiousDiscipline.CONTEMPORARY_FIQH

    assert EvidenceDomain.FATWA in route.target_domains

    assert EvidenceNeed.CONTEMPORARY_GUIDANCE in route.context_requirement.required


def test_contested_fiqh_is_mode_not_domain() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            ("يزعم أن المذاهب متفقة في هذه المسألة"),
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert route.frame.primary_discipline is ReligiousDiscipline.FIQH

    assert route.frame.reasoning_mode is ReasoningMode.CONTESTED_CLAIM

    assert AnswerConstraint.DO_NOT_ACCEPT_PREMISE_AS_FACT in route.frame.constraints

    assert EvidenceObligation.DOCUMENTED_DISAGREEMENT in route.frame.obligations


def test_contested_hadith_requires_grading() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            ("يزعم أن هذا الحديث يناقض القرآن"),
            BasiraIntent.HADITH_EXPLANATION,
        )
    )

    assert route.frame.reasoning_mode is ReasoningMode.CONTESTED_CLAIM

    assert EvidenceNeed.HADITH_GRADE in route.context_requirement.required


def test_mawarith_gets_deterministic_reasoning_mode() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            ("كيف تقسم التركة في هذا الميراث؟"),
            BasiraIntent.GENERAL_ISLAMIC_QUESTION,
        )
    )

    assert route.frame.primary_discipline is ReligiousDiscipline.MAWARITH

    assert route.frame.reasoning_mode is ReasoningMode.DETERMINISTIC_CALCULATION

    assert route.target_domains == (EvidenceDomain.FIQH,)


def test_route_records_why_it_changed() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            "ما حكم البيتكوين؟",
            BasiraIntent.FIQH_QUESTION,
        )
    )

    assert "baseline_intent:fiqh_question" in route.routing_reasons

    assert "explicit_cue:contemporary_fiqh" in route.routing_reasons


def test_regular_quran_meaning_does_not_force_surrounding_context() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            "ما معنى آية الكرسي؟",
            BasiraIntent.QURAN_MEANING,
        )
    )

    assert EvidenceNeed.TAFSIR in route.context_requirement.required

    assert EvidenceNeed.SURROUNDING_CONTEXT not in route.context_requirement.required


def test_quran_meaning_preserves_baseline_surrounding_context() -> None:
    route = ReligiousReasoningRouter().route(
        _understanding(
            ("ما معنى آية فاقتلوا المشركين حيث وجدتموهم؟"),
            BasiraIntent.QURAN_MEANING,
            required=frozenset(
                {
                    EvidenceNeed.SURROUNDING_CONTEXT,
                }
            ),
        )
    )

    assert EvidenceNeed.TAFSIR in route.context_requirement.required

    assert EvidenceNeed.SURROUNDING_CONTEXT in route.context_requirement.required
