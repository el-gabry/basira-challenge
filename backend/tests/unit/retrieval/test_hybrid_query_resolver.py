from basira.retrieval.hybrid_query_resolver import (
    HybridLookupMode,
    HybridTopic,
    ResponseGovernanceLevel,
    resolve_hybrid_query,
)


def test_hadith_number_is_candidate_identity_not_truth() -> None:
    result = resolve_hybrid_query(
        question="ما صحة حديث 65065؟",
        language="ar",
    )

    assert result.topic is HybridTopic.HADITH
    assert result.lookup_mode is HybridLookupMode.IDENTIFIER
    assert result.response_level is ResponseGovernanceLevel.A
    assert result.identifier_candidate == "65065"


def test_english_hadith_number_uses_same_resolution_contract() -> None:
    result = resolve_hybrid_query(
        question="Is hadith 65065 authentic?",
        language="en",
    )

    assert result.topic is HybridTopic.HADITH
    assert result.language == "en"
    assert result.identifier_candidate == "65065"
    assert result.allow_cross_language_fallback is False


def test_explicit_quran_meaning_routes_to_tafsir() -> None:
    result = resolve_hybrid_query(
        question="ما معنى الكرسي في آية الكرسي؟",
        language="ar",
    )

    assert result.topic is HybridTopic.TAFSIR
    assert result.response_level is ResponseGovernanceLevel.B


def test_bare_kursi_concept_is_not_promoted_to_quran() -> None:
    result = resolve_hybrid_query(
        question="ما هو الكرسي؟",
        language="ar",
    )

    assert result.topic is HybridTopic.GENERAL
    assert result.capability == "general_islamic"


def test_aqeedah_concept() -> None:
    result = resolve_hybrid_query(
        question="ما معنى التوحيد؟",
        language="ar",
    )

    assert result.topic is HybridTopic.AQEEDAH
    assert result.capability == "aqeedah"
    assert result.response_level is ResponseGovernanceLevel.B


def test_terminology_translation_requires_target_language_source() -> None:
    result = resolve_hybrid_query(
        question="Translate tawhid into English",
        language="en",
    )

    assert result.topic is HybridTopic.TERMINOLOGY
    assert result.lookup_mode is HybridLookupMode.TRANSLATION
    assert result.allow_cross_language_fallback is False


def test_sensitive_history_is_level_c() -> None:
    result = resolve_hybrid_query(
        question="هل الإسلام انتشر بالسيف؟",
        language="ar",
    )

    assert result.topic is HybridTopic.HISTORY
    assert result.response_level is ResponseGovernanceLevel.C


def test_misconception_question_uses_shubuhat_capability() -> None:
    result = resolve_hybrid_query(
        question="لماذا يعبد المسلمون الكعبة؟",
        language="ar",
    )

    assert result.topic is HybridTopic.SHUBUHAT
    assert result.capability == "shubuhat_faq"


def test_personalized_fiqh_is_level_d() -> None:
    result = resolve_hybrid_query(
        question=("أنا في دولة كذا هل يجوز لي فعل هذا في زواجي؟"),
        language="ar",
    )

    assert result.topic is HybridTopic.FIQH
    assert result.personalized is True
    assert result.lookup_mode is HybridLookupMode.PERSONALIZED_APPLICATION
    assert result.response_level is ResponseGovernanceLevel.D


def test_general_fiqh_preserves_disagreement() -> None:
    result = resolve_hybrid_query(
        question=("هل لمس المرأة فرجها ينقض الوضوء؟"),
        language="ar",
    )

    assert result.topic is HybridTopic.FIQH
    assert result.personalized is False
    assert result.response_level is ResponseGovernanceLevel.C
    assert "no_automated_tarjih" in result.reasons


def test_language_can_be_inferred_without_becoming_authority() -> None:
    arabic = resolve_hybrid_query(
        question="ما معنى التوحيد؟",
    )

    english = resolve_hybrid_query(
        question="What does tawhid mean?",
    )

    assert arabic.language == "ar"
    assert english.language == "en"

    assert arabic.allow_cross_language_fallback is False
    assert english.allow_cross_language_fallback is False


def test_hadith_matn_between_marker_and_grade_routes_to_hadith() -> None:
    result = resolve_hybrid_query(
        question=("هل حديث إنما الأعمال بالنيات صحيح؟"),
        language="ar",
    )

    assert result.topic is HybridTopic.HADITH
    assert result.lookup_mode is HybridLookupMode.PARTIAL_TEXT
    assert result.response_level is ResponseGovernanceLevel.A
    assert result.capability == "hadith"


def test_english_hadith_matn_with_authenticity_cue() -> None:
    result = resolve_hybrid_query(
        question=("Is the hadith actions are by intentions authentic?"),
        language="en",
    )

    assert result.topic is HybridTopic.HADITH
    assert result.lookup_mode is HybridLookupMode.PARTIAL_TEXT
    assert result.capability == "hadith"
