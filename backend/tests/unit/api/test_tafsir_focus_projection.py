from basira.api.governed_runtime import (
    _explicit_tafsir_focus,
    _focused_excerpt,
    _tafsir_focus_score,
)


def test_explicit_meaning_target_isolated() -> None:
    terms = _explicit_tafsir_focus(
        "ما معنى الكرسي في قوله تعالى "
        "وسع كرسيه السماوات والأرض"
    )

    assert terms is not None
    assert "الكرسي" in terms
    assert "كرسي" in terms
    assert "السماوات" not in terms


def test_focused_excerpt_drops_preceding_glossary_noise() -> None:
    text = (
        "السنة: نعاس من غير نوم، والغفوة أيضًا. : "
        "الكرسي: جسم عظيم، مخلوق بين يدي العرش، "
        "وهو موضع القدمين. : "
        "يؤوده: يثقله."
    )

    excerpt = _focused_excerpt(
        text,
        ("الكرسي", "كرسي"),
    )

    assert excerpt is not None
    assert "الكرسي" in excerpt
    assert "نعاس" not in excerpt
    assert "السنة" not in excerpt


def test_direct_explanation_outranks_contextual_mention() -> None:
    terms = (
        "الكرسي",
        "كرسي",
    )

    direct = (
        "الكرسي: جسم عظيم مخلوق، "
        "وهو موضع القدمين."
    )

    contextual = (
        "لما اشتملت آية الكرسي السابقة "
        "على دلائل الوحدانية وعظمة الخالق."
    )

    assert (
        _tafsir_focus_score(
            direct,
            terms,
        )
        >
        _tafsir_focus_score(
            contextual,
            terms,
        )
    )



def test_quran_named_focus_recovers_one_edit_typo() -> None:
    from types import SimpleNamespace

    from basira.api.governed_runtime import (
        _canonicalize_verified_quran_focus,
        _explicit_tafsir_focus,
    )

    terms = _explicit_tafsir_focus(
        "ما معنى الكرصى في قوله تعالى "
        "وسع كرسيه السماوات والأرض؟"
    )

    assert terms == (
        "الكرصي",
        "كرصي",
    )

    corrected = (
        _canonicalize_verified_quran_focus(
            terms,
            SimpleNamespace(
                targets=(),
            ),
        )
    )

    assert corrected == (
        "الكرسي",
        "كرسي",
    )


def test_quran_named_focus_does_not_rewrite_unrelated_word() -> None:
    from types import SimpleNamespace

    from basira.api.governed_runtime import (
        _canonicalize_verified_quran_focus,
    )

    original = (
        "الصلاة",
        "صلاة",
    )

    assert (
        _canonicalize_verified_quran_focus(
            original,
            SimpleNamespace(
                targets=(),
            ),
        )
        == original
    )
