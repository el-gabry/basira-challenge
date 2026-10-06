from basira.verification.quran_orthography import (
    QuranOrthographyComparator,
    QuranOrthographyRelation,
    QuranScriptType,
    QuranSourceProfile,
)
from basira.verification.quran_orthography_rules import (
    QuranOrthographyRuleId,
)

UTHMANI = QuranSourceProfile(
    source_id="quran-uthmani-test",
    source_name="Uthmani Test Source",
    script=QuranScriptType.UTHMANI,
)

IMLAEI = QuranSourceProfile(
    source_id="quran-imlaei-test",
    source_name="Imla'i Test Source",
    script=QuranScriptType.IMLAEI,
)


def test_exact_match() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="إن الله مع الصابرين",
            right_text="إن الله مع الصابرين",
            left_profile=UTHMANI,
            right_profile=UTHMANI,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation.EXACT_MATCH
    )

    assert result.is_textual_error is False


def test_diacritics_only_variant() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="إِنَّ ٱللَّهَ",
            right_text="إن الله",
            left_profile=UTHMANI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation
        .DIACRITIC_VARIANT
    )

    assert (
        result.normalized_left
        == result.normalized_right
    )

    assert result.is_textual_error is False


def test_vocative_ya_ayyuhā_uthmani_variant() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="يَـٰٓأَيُّهَا",
            right_text="يا أيها",
            left_profile=UTHMANI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation
        .UTHMANI_RASM_VARIANT
    )

    assert (
        result.rule_id
        == QuranOrthographyRuleId
        .VOCATIVE_YA_ALIF_OMISSION
    )

    assert result.is_textual_error is False


def test_vocative_ya_bani_uthmani_variant() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="يَـٰبَنِىٓ",
            right_text="يا بني",
            left_profile=UTHMANI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation
        .UTHMANI_RASM_VARIANT
    )

    assert (
        result.rule_id
        == QuranOrthographyRuleId
        .VOCATIVE_YA_ALIF_OMISSION
    )

    assert result.is_textual_error is False


def test_vocative_ya_musa_uthmani_variant() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="يَـٰمُوسَىٰ",
            right_text="يا موسى",
            left_profile=UTHMANI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation
        .UTHMANI_RASM_VARIANT
    )

    assert (
        result.rule_id
        == QuranOrthographyRuleId
        .VOCATIVE_YA_ALIF_OMISSION
    )

    assert result.is_textual_error is False


def test_generic_word_boundary_variant() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="عبدالله",
            right_text="عبد الله",
            left_profile=IMLAEI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation
        .TOKEN_BOUNDARY_VARIANT
    )

    assert result.is_textual_error is False


def test_basmala_layout_variant() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="الٓمٓ",
            right_text=(
                "بِسْمِ ٱللَّهِ "
                "ٱلرَّحْمَـٰنِ "
                "ٱلرَّحِيمِ "
                "الٓمٓ"
            ),
            left_profile=UTHMANI,
            right_profile=UTHMANI,
            surah_number=2,
            ayah_number=1,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation
        .BASMALA_LAYOUT_VARIANT
    )

    assert result.is_textual_error is False


def test_basmala_layout_not_applied_outside_first_ayah() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="الحمد لله",
            right_text=(
                "بسم الله الرحمن الرحيم "
                "الحمد لله"
            ),
            left_profile=UTHMANI,
            right_profile=UTHMANI,
            surah_number=2,
            ayah_number=2,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation.UNRESOLVED
    )

    assert result.is_textual_error is None


def test_real_word_change_stays_unresolved() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="إن الله مع الصابرين",
            right_text="إن الله يحب الصابرين",
            left_profile=IMLAEI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation.UNRESOLVED
    )

    assert result.is_textual_error is None


def test_vocative_rule_requires_uthmani_and_imlaei() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="يبني",
            right_text="يا بني",
            left_profile=IMLAEI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        != QuranOrthographyRelation
        .UTHMANI_RASM_VARIANT
    )


def test_vocative_rule_does_not_delete_arbitrary_alif() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="قال موسى",
            right_text="قل موسى",
            left_profile=UTHMANI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation.UNRESOLVED
    )

    assert result.is_textual_error is None


def test_known_vocative_rule_does_not_hide_other_difference() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text=(
                "يَـٰبَنِىٓ "
                "إِسْرَٰٓءِيلَ"
            ),
            right_text=(
                "يا بني إسرائيل"
            ),
            left_profile=UTHMANI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation.UNRESOLVED
    )

    assert result.is_textual_error is None


def test_israil_rule_on_atomic_lexeme() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="إِسْرَٰٓءِيلَ",
            right_text="إسرائيل",
            left_profile=UTHMANI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographyRelation
        .UTHMANI_RASM_VARIANT
    )

    assert (
        result.rule_id
        == QuranOrthographyRuleId
        .ISRAIL_ALIF_RASM_VARIANT
    )

    assert result.is_textual_error is False


def test_combining_hamza_matches_precomposed_yeh_hamza() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="تِلۡقَآيِٕ",
            right_text="تِلْقَآئِ",
            left_profile=UTHMANI,
            right_profile=UTHMANI,
        )
    )

    assert (
        result.normalized_left
        == result.normalized_right
    )

    assert (
        result.relation
        == QuranOrthographyRelation
        .DIACRITIC_VARIANT
    )

    assert result.is_textual_error is False


def test_combining_hamza_matches_standalone_hamza() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="فَٱدَّٰرَٰءۡتُمۡ",
            right_text="فَٱدَّٰرَْٰٔتُمْ",
            left_profile=UTHMANI,
            right_profile=UTHMANI,
        )
    )

    assert (
        result.normalized_left
        == result.normalized_right
    )

    assert (
        result.relation
        == QuranOrthographyRelation
        .DIACRITIC_VARIANT
    )

    assert result.is_textual_error is False


def test_small_waw_annotation_does_not_create_lexical_mismatch() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="لِيَسُـُٔواْ",
            right_text="لِيَسُـۥٓـُٔوا۟",
            left_profile=UTHMANI,
            right_profile=UTHMANI,
        )
    )

    assert (
        result.normalized_left
        == result.normalized_right
    )

    assert result.is_textual_error is False


def test_quranic_tatweel_hamza_before_alef_matches_alef_hamza() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="ٱلۡأٓخِرَةِ",
            right_text="ٱلْـَٔاخِرَةِ",
            left_profile=UTHMANI,
            right_profile=UTHMANI,
        )
    )

    assert (
        result.normalized_left
        == result.normalized_right
    )

    assert (
        result.relation
        == QuranOrthographyRelation
        .DIACRITIC_VARIANT
    )

    assert result.is_textual_error is False


def test_quranic_tatweel_hamza_before_alef_with_prefix() -> None:
    result = (
        QuranOrthographyComparator()
        .compare(
            left_text="لَأٓيَةٗ",
            right_text="لَـَٔايَةً",
            left_profile=UTHMANI,
            right_profile=UTHMANI,
        )
    )

    assert (
        result.normalized_left
        == result.normalized_right
    )

    assert result.is_textual_error is False


def test_quranic_tatweel_hamza_without_alef_is_preserved() -> None:
    normalized = (
        QuranOrthographyComparator
        ._normalize_letters(
            "يَسْـَٔلُونَ"
        )
    )

    assert "ء" in normalized


def test_arbitrary_combining_hamza_is_not_silently_removed() -> None:
    normalized = (
        QuranOrthographyComparator
        ._normalize_letters(
            "رَٔ"
        )
    )

    assert normalized == "رء"


def test_alef_hamza_comparison_policy_is_preserved() -> None:
    assert (
        QuranOrthographyComparator
        ._normalize_letters("أ")
        == "ا"
    )

    assert (
        QuranOrthographyComparator
        ._normalize_letters("إ")
        == "ا"
    )


def test_precomposed_yeh_hamza_remains_lexically_significant() -> None:
    normalized = (
        QuranOrthographyComparator
        ._normalize_letters(
            "امرئ"
        )
    )

    assert "ئ" in normalized