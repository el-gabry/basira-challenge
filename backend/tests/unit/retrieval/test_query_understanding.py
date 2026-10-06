from __future__ import annotations

from basira.evidence.models import (
    EvidenceNeed,
)
from basira.retrieval.arabic_query import (
    ArabicDialect,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
    RiskTag,
)


def service() -> BasiraQueryUnderstandingService:
    return BasiraQueryUnderstandingService()


def test_gulf_hadith_authenticity_query() -> None:
    result = service().understand(
        "وش صحة هالحديث؟"
    )

    assert (
        result.query.dialect
        is ArabicDialect.GULF
    )

    assert (
        result.primary_intent
        is BasiraIntent
        .HADITH_AUTHENTICITY
    )

    assert (
        result.context_requirement
        .requires(
            EvidenceNeed.HADITH_TEXT
        )
    )

    assert (
        result.context_requirement
        .requires(
            EvidenceNeed.HADITH_GRADE
        )
    )


def test_egyptian_hadith_authenticity_query() -> None:
    result = service().understand(
        "الحديث ده صح ولا ايه؟"
    )

    assert (
        result.query.dialect
        is ArabicDialect.EGYPTIAN
    )

    assert (
        result.primary_intent
        is BasiraIntent
        .HADITH_AUTHENTICITY
    )


def test_sensitive_quran_query_declares_context_requirements() -> None:
    result = service().understand(
        "ما معنى آية فاقتلوا المشركين "
        "حيث وجدتموهم؟"
    )

    assert (
        result.primary_intent
        is BasiraIntent.QURAN_MEANING
    )

    assert (
        RiskTag.ARMED_CONFLICT
        in result.risk_tags
    )

    assert (
        RiskTag.CONTEXT_SENSITIVE
        in result.risk_tags
    )

    required = (
        result.context_requirement
        .required
    )

    assert (
        EvidenceNeed.CANONICAL_TEXT
        in required
    )

    assert (
        EvidenceNeed
        .SURROUNDING_CONTEXT
        in required
    )

    assert (
        EvidenceNeed.TAFSIR
        in required
    )

    assert (
        EvidenceNeed.RELATED_HADITH
        in required
    )

    assert (
        EvidenceNeed
        .FIQH_CONSTRAINTS
        in required
    )

    assert (
        EvidenceNeed.ACTOR_AUTHORITY
        in required
    )

    assert (
        EvidenceNeed
        .APPLICABILITY_CONDITIONS
        in required
    )


def test_regular_quran_meaning_does_not_force_sensitive_context() -> None:
    result = service().understand(
        "ما معنى آية الكرسي؟"
    )

    assert (
        result.primary_intent
        is BasiraIntent.QURAN_MEANING
    )

    assert (
        RiskTag.CONTEXT_SENSITIVE
        not in result.risk_tags
    )

    assert (
        result.context_requirement
        .requires(
            EvidenceNeed.CANONICAL_TEXT
        )
    )

    assert not (
        result.context_requirement
        .requires(
            EvidenceNeed
            .ACTOR_AUTHORITY
        )
    )


def test_hadith_number_entity_is_extracted() -> None:
    result = service().understand(
        "ما صحة حديث رقم 1751؟"
    )

    values = {
        (
            entity.entity_type,
            entity.value,
        )
        for entity
        in result.entities
    }

    assert (
        "hadith_number",
        "1751",
    ) in values


def test_msa_hadith_authenticity_query() -> None:
    result = service().understand(
        "ما صحة هذا الحديث؟"
    )

    assert (
        result.primary_intent
        is BasiraIntent
        .HADITH_AUTHENTICITY
    )


def test_hadith_grade_wording_routes_to_authenticity() -> None:
    result = service().understand(
        "ما درجة هذا الحديث؟"
    )

    assert (
        result.primary_intent
        is BasiraIntent
        .HADITH_AUTHENTICITY
    )


def test_quran_tafsir_wording_routes_to_meaning() -> None:
    result = service().understand(
        "تفسير آية الكرسي"
    )

    assert (
        result.primary_intent
        is BasiraIntent.QURAN_MEANING
    )


def test_normalized_maqsura_meaning_cue_is_recognized() -> None:
    result = service().understand(
        "ما معنى آية الكرسي؟"
    )

    assert (
        result.query.intent_text
        == "ما معني اية الكرسي"
    )

    assert (
        result.primary_intent
        is BasiraIntent.QURAN_MEANING
    )


def test_numeric_quran_reference_is_extracted() -> None:
    result = service().understand(
        "ما معنى الآية 2:255؟"
    )

    values = {
        (
            entity.entity_type,
            entity.value,
        )
        for entity
        in result.entities
    }

    assert (
        "surah_number",
        "2",
    ) in values

    assert (
        "ayah_number",
        "255",
    ) in values

    assert (
        result.primary_intent
        is BasiraIntent.QURAN_MEANING
    )
