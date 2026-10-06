from basira.reasoning.contracts import (
    ReasoningMode,
)
from basira.reasoning.routing import (
    ReligiousReasoningRouter,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
)


def _route(question: str):
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(question)
    )

    route = (
        ReligiousReasoningRouter()
        .route(understanding)
    )

    return understanding, route


def test_quran_meaning_from_qawlihi_taala() -> None:
    understanding, route = _route(
        "ما معنى الكرسي في قوله تعالى "
        "وسع كرسيه السماوات والأرض؟"
    )

    assert (
        understanding.primary_intent
        is BasiraIntent.QURAN_MEANING
    )

    assert (
        route.frame.reasoning_mode
        is ReasoningMode.INTERPRETATION
    )

    domains = {
        domain.value
        for domain in route.target_domains
    }

    assert "quran" in domains
    assert "tafsir" in domains


def test_quran_meaning_from_qawl_allah_taala() -> None:
    understanding, route = _route(
        "ما معنى قول الله تعالى "
        "حافظوا على الصلوات والصلاة الوسطى؟"
    )

    assert (
        understanding.primary_intent
        is BasiraIntent.QURAN_MEANING
    )

    assert (
        route.frame.reasoning_mode
        is ReasoningMode.INTERPRETATION
    )


def test_explicit_quran_source_without_explanation_is_lookup() -> None:
    understanding, _route_result = _route(
        "ماذا ورد في القرآن عن الصلاة؟"
    )

    assert (
        understanding.primary_intent
        is BasiraIntent.QURAN_LOOKUP
    )


def test_plain_meaning_question_is_not_forced_into_quran() -> None:
    understanding, _route_result = _route(
        "ما معنى الكرسي؟"
    )

    assert (
        understanding.primary_intent
        is BasiraIntent.GENERAL_ISLAMIC_QUESTION
    )
