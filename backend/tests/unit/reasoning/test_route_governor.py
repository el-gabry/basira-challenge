from __future__ import annotations

from dataclasses import replace

import pytest

from basira.evidence.models import (
    ContextRequirement,
    EvidenceNeed,
)
from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
)
from basira.reasoning.route_governor import (
    RouteGovernor,
)
from basira.reasoning.route_proposal import (
    RouteProposal,
)
from basira.retrieval.arabic_query import (
    build_arabic_query,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
    BasiraQueryUnderstandingService,
    RiskTag,
    context_requirement_for,
)


def understanding(
    *,
    text: str,
    intent: BasiraIntent,
    risks: frozenset[RiskTag] = frozenset(),
) -> BasiraQueryUnderstanding:
    return BasiraQueryUnderstanding(
        query=build_arabic_query(text),
        primary_intent=intent,
        risk_tags=risks,
        entities=(),
        context_requirement=(
            context_requirement_for(
                intent,
                risks,
            )
        ),
        confidence=1.0,
    )


def test_high_confidence_proposal_can_specialize_generic_intent():
    baseline = understanding(
        text="اشرح لي المقصود",
        intent=(BasiraIntent.GENERAL_ISLAMIC_QUESTION),
    )

    result = RouteGovernor().govern(
        understanding=baseline,
        proposal=RouteProposal(
            proposed_intent=(BasiraIntent.QURAN_MEANING),
            proposed_primary_discipline=(ReligiousDiscipline.QURAN),
            proposed_secondary_disciplines=(ReligiousDiscipline.TAFSIR,),
            proposed_reasoning_mode=(ReasoningMode.INTERPRETATION),
            confidence=0.95,
        ),
    )

    effective = result.effective_understanding

    assert effective.primary_intent is BasiraIntent.QURAN_MEANING

    assert result.accepted_intent_specialization

    assert EvidenceNeed.CANONICAL_TEXT in effective.context_requirement.required


def test_specific_baseline_intent_cannot_be_replaced_by_llm():
    baseline = understanding(
        text="ما معنى الآية؟",
        intent=BasiraIntent.QURAN_MEANING,
    )

    result = RouteGovernor().govern(
        understanding=baseline,
        proposal=RouteProposal(
            proposed_intent=(BasiraIntent.HADITH_AUTHENTICITY),
            confidence=1.0,
        ),
    )

    assert result.effective_understanding.primary_intent is BasiraIntent.QURAN_MEANING

    assert not (result.accepted_intent_specialization)


def test_low_confidence_cannot_specialize_generic_intent():
    baseline = understanding(
        text="سؤال عام",
        intent=(BasiraIntent.GENERAL_ISLAMIC_QUESTION),
    )

    result = RouteGovernor().govern(
        understanding=baseline,
        proposal=RouteProposal(
            proposed_intent=(BasiraIntent.FIQH_QUESTION),
            confidence=0.40,
        ),
    )

    assert (
        result.effective_understanding.primary_intent
        is BasiraIntent.GENERAL_ISLAMIC_QUESTION
    )

    assert not (result.accepted_intent_specialization)


def test_ambiguous_proposal_cannot_specialize_generic_intent():
    baseline = understanding(
        text="سؤال عام",
        intent=(BasiraIntent.GENERAL_ISLAMIC_QUESTION),
    )

    result = RouteGovernor().govern(
        understanding=baseline,
        proposal=RouteProposal(
            proposed_intent=(BasiraIntent.FIQH_QUESTION),
            ambiguity=True,
            confidence=1.0,
        ),
    )

    assert (
        result.effective_understanding.primary_intent
        is BasiraIntent.GENERAL_ISLAMIC_QUESTION
    )


def test_llm_risk_hint_uses_existing_context_policy():
    baseline = understanding(
        text="ما معنى الآية؟",
        intent=BasiraIntent.QURAN_MEANING,
    )

    assert EvidenceNeed.SURROUNDING_CONTEXT not in baseline.context_requirement.required

    result = RouteGovernor().govern(
        understanding=baseline,
        proposal=RouteProposal(
            additional_risk_tags=frozenset(
                {
                    RiskTag.CONTEXT_SENSITIVE,
                }
            ),
            confidence=0.20,
        ),
    )

    effective = result.effective_understanding

    assert RiskTag.CONTEXT_SENSITIVE in effective.risk_tags

    required = effective.context_requirement.required

    assert EvidenceNeed.SURROUNDING_CONTEXT in required

    assert EvidenceNeed.TAFSIR in required

    assert EvidenceNeed.RELATED_HADITH in required

    assert EvidenceNeed.FIQH_CONSTRAINTS in required

    assert EvidenceNeed.ACTOR_AUTHORITY in required

    assert EvidenceNeed.APPLICABILITY_CONDITIONS in required


def test_governor_never_removes_baseline_requirement():
    baseline = understanding(
        text="سؤال عام",
        intent=(BasiraIntent.GENERAL_ISLAMIC_QUESTION),
    )

    baseline = replace(
        baseline,
        context_requirement=(
            ContextRequirement(
                required=frozenset(
                    {
                        EvidenceNeed.RELATED_HADITH,
                    }
                ),
                optional=frozenset(),
            )
        ),
    )

    result = RouteGovernor().govern(
        understanding=baseline,
        proposal=RouteProposal(
            proposed_intent=(BasiraIntent.FIQH_QUESTION),
            confidence=0.99,
        ),
    )

    assert (
        EvidenceNeed.RELATED_HADITH
        in result.effective_understanding.context_requirement.required
    )


def test_hard_query_identity_fields_are_preserved():
    baseline = BasiraQueryUnderstandingService().understand("ما معنى الآية 2:255؟")

    original_query = baseline.query
    original_entities = baseline.entities

    result = RouteGovernor().govern(
        understanding=baseline,
        proposal=RouteProposal(
            proposed_intent=(BasiraIntent.HADITH_AUTHENTICITY),
            confidence=1.0,
        ),
    )

    effective = result.effective_understanding

    assert effective.query == original_query

    assert effective.entities == original_entities


def test_invalid_specialization_threshold_is_rejected():
    with pytest.raises(
        ValueError,
    ):
        RouteGovernor(minimum_specialization_confidence=(1.1))
