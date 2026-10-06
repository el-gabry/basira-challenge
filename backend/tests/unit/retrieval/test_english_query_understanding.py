from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)


def intent(question: str) -> str:
    return BasiraQueryUnderstandingService().understand(question).primary_intent.value


def test_english_quran_meaning_is_understood() -> None:
    assert intent("What does Ayat al-Kursi say?") == "quran_meaning"


def test_english_quran_reference_meaning_is_understood() -> None:
    assert intent("What does Kursi mean in verse 2:255?") == "quran_meaning"


def test_english_hadith_authenticity_is_understood() -> None:
    assert (
        intent("Is the hadith Actions are judged by intentions authentic?")
        == "hadith_authenticity"
    )


def test_explicit_english_tafsir_is_understood() -> None:
    assert intent("Explain the tafsir of verse 2:255") == "quran_meaning"


def test_general_english_question_is_not_hijacked() -> None:
    assert intent("Why is intention important in Islam?") == "general_islamic_question"


def test_english_revelation_context_is_specific() -> None:
    assert (
        intent("What was the occasion of revelation for verse 2:255?")
        == "tafsir_context"
    )
