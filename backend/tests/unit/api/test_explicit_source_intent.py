from basira.api.governed_runtime import (
    _promote_explicit_source_lookup,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
)


def _understand(text: str):
    return BasiraQueryUnderstandingService().understand(
        text
    )


def test_sunnah_cue_promotes_only_generic_to_hadith_lookup() -> None:
    question = "ما فضل الصلاة في السنة؟"

    result = _promote_explicit_source_lookup(
        understanding=_understand(question),
        question=question,
    )

    assert (
        result.primary_intent
        is BasiraIntent.HADITH_LOOKUP
    )


def test_quran_cue_promotes_only_generic_to_quran_lookup() -> None:
    question = "هل أمر القرآن بالمحافظة على الصلاة؟"

    result = _promote_explicit_source_lookup(
        understanding=_understand(question),
        question=question,
    )

    assert (
        result.primary_intent
        is BasiraIntent.QURAN_LOOKUP
    )


def test_existing_specialized_intent_is_not_overridden() -> None:
    question = "هل حديث إنما الأعمال بالنيات صحيح؟"

    baseline = _understand(question)

    result = _promote_explicit_source_lookup(
        understanding=baseline,
        question=question,
    )

    assert (
        result.primary_intent
        is baseline.primary_intent
    )


def test_mixed_explicit_sources_remain_generic_when_ambiguous() -> None:
    question = "ماذا ورد في القرآن والسنة عن الصلاة؟"

    baseline = _understand(question)

    result = _promote_explicit_source_lookup(
        understanding=baseline,
        question=question,
    )

    assert (
        result.primary_intent
        is baseline.primary_intent
    )
