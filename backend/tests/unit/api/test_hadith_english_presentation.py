from types import SimpleNamespace

from basira.api.presenter import (
    _localized_hadith_answer,
)


def _hadith(
    evidence_id: str,
):
    return SimpleNamespace(
        evidence_id=evidence_id,
        domain=SimpleNamespace(
            value="hadith",
        ),
    )


def _quran(
    evidence_id: str,
):
    return SimpleNamespace(
        evidence_id=evidence_id,
        domain=SimpleNamespace(
            value="quran",
        ),
    )


def test_english_hadith_localizes_only_framing():
    source_claim = (
        "Canonical Sahih al-Bukhari "
        "source verified"
    )

    value = (
        "وفق الأدلة المعتمدة:\n\n"
        "[1] Actions are but by intentions.\n\n"
        "[2] حكم المحدّث "
        "(https://dorar.net/en/ahadith/45): "
        + source_claim
    )

    result = _localized_hadith_answer(
        value,
        language="en",
        evidence=(
            _hadith("h1"),
            _hadith("h2"),
        ),
        used_ids=frozenset(
            {
                "h1",
                "h2",
            }
        ),
    )

    assert result is not None

    assert result.startswith(
        "According to the governed evidence:"
    )

    assert (
        "Hadith status / source verification "
        "(https://dorar.net/en/ahadith/45): "
        + source_claim
    ) in result

    # Verified claim content is untouched.
    assert source_claim in result

    assert (
        "Actions are but by intentions."
        in result
    )


def test_arabic_presentation_is_unchanged():
    value = (
        "وفق الأدلة المعتمدة:\n\n"
        "[1] حكم المحدّث: صحيح"
    )

    assert (
        _localized_hadith_answer(
            value,
            language="ar",
            evidence=(
                _hadith("h1"),
            ),
            used_ids=frozenset(
                {
                    "h1",
                }
            ),
        )
        == value
    )


def test_non_hadith_answer_is_not_rewritten():
    value = (
        "وفق الأدلة المعتمدة:\n\n"
        "[1] source claim"
    )

    assert (
        _localized_hadith_answer(
            value,
            language="en",
            evidence=(
                _quran("q1"),
            ),
            used_ids=frozenset(
                {
                    "q1",
                }
            ),
        )
        == value
    )


def test_claim_content_with_arabic_word_hukm_is_untouched():
    claim = (
        "[1] This source discusses حكم "
        "inside the verified claim."
    )

    result = _localized_hadith_answer(
        (
            "وفق الأدلة المعتمدة:\n\n"
            + claim
        ),
        language="en",
        evidence=(
            _hadith("h1"),
        ),
        used_ids=frozenset(
            {
                "h1",
            }
        ),
    )

    assert result is not None
    assert claim in result
