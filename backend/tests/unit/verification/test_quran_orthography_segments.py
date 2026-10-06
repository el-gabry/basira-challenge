from basira.verification.quran_orthography import (
    QuranOrthographyRelation,
    QuranScriptType,
    QuranSourceProfile,
)
from basira.verification.quran_orthography_rules import (
    QuranOrthographyRuleId,
)
from basira.verification.quran_orthography_segments import (
    QuranOrthographySegmentComparator,
    QuranOrthographySequenceRelation,
)

UTHMANI = QuranSourceProfile(
    source_id="tanzil-uthmani-test",
    source_name="Tanzil Uthmani",
    script=QuranScriptType.UTHMANI,
)

IMLAEI = QuranSourceProfile(
    source_id="tanzil-imlaei-test",
    source_name="Tanzil Simple Plain",
    script=QuranScriptType.IMLAEI,
)


def test_exact_text_is_exact() -> None:
    result = (
        QuranOrthographySegmentComparator()
        .compare(
            left_text=(
                "إن الله مع الصابرين"
            ),
            right_text=(
                "إن الله مع الصابرين"
            ),
            left_profile=IMLAEI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographySequenceRelation
        .EXACT_MATCH
    )

    assert result.all_resolved
    assert result.unresolved_count == 0
    assert result.is_textual_error is False


def test_vocative_and_israil_rules_can_coexist() -> None:
    result = (
        QuranOrthographySegmentComparator()
        .compare(
            left_text=(
                "يَـٰبَنِىٓ إِسْرَٰٓءِيلَ"
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
        == QuranOrthographySequenceRelation
        .ORTHOGRAPHICALLY_EQUIVALENT
    )

    assert result.all_resolved
    assert result.unresolved_count == 0

    assert result.is_textual_error is False

    assert (
        QuranOrthographyRuleId
        .VOCATIVE_YA_ALIF_OMISSION
        in result.rule_ids
    )

    assert (
        QuranOrthographyRuleId
        .ISRAIL_ALIF_RASM_VARIANT
        in result.rule_ids
    )


def test_vocative_segment_is_aligned_one_to_two() -> None:
    result = (
        QuranOrthographySegmentComparator()
        .compare(
            left_text=(
                "يَـٰبَنِىٓ إِسْرَٰٓءِيلَ"
            ),
            right_text=(
                "يا بني إسرائيل"
            ),
            left_profile=UTHMANI,
            right_profile=IMLAEI,
        )
    )

    vocative = next(
        segment
        for segment in result.segments
        if (
            segment.rule_id
            == QuranOrthographyRuleId
            .VOCATIVE_YA_ALIF_OMISSION
        )
    )

    assert (
        vocative.left_text
        == "يَـٰبَنِىٓ"
    )

    assert (
        vocative.right_text
        == "يا بني"
    )

    assert (
        vocative.left_token_end
        - vocative.left_token_start
        == 1
    )

    assert (
        vocative.right_token_end
        - vocative.right_token_start
        == 2
    )


def test_israil_segment_has_source_backed_rule() -> None:
    result = (
        QuranOrthographySegmentComparator()
        .compare(
            left_text=(
                "يَـٰبَنِىٓ إِسْرَٰٓءِيلَ"
            ),
            right_text=(
                "يا بني إسرائيل"
            ),
            left_profile=UTHMANI,
            right_profile=IMLAEI,
        )
    )

    israil = next(
        segment
        for segment in result.segments
        if (
            segment.rule_id
            == QuranOrthographyRuleId
            .ISRAIL_ALIF_RASM_VARIANT
        )
    )

    assert (
        israil.relation
        == QuranOrthographyRelation
        .UTHMANI_RASM_VARIANT
    )

    assert (
        israil.assessment
        .is_textual_error
        is False
    )

    assert (
        israil.assessment
        .rule_evidence_ids
    )

    assert (
        israil.assessment
        .rule_evidence_urls
    )


def test_known_rule_does_not_hide_lexical_change() -> None:
    result = (
        QuranOrthographySegmentComparator()
        .compare(
            left_text=(
                "يَـٰبَنِىٓ مَعَ"
            ),
            right_text=(
                "يا بني يحب"
            ),
            left_profile=UTHMANI,
            right_profile=IMLAEI,
        )
    )

    assert (
        QuranOrthographyRuleId
        .VOCATIVE_YA_ALIF_OMISSION
        in result.rule_ids
    )

    assert (
        result.relation
        == QuranOrthographySequenceRelation
        .UNRESOLVED
    )

    assert (
        result.unresolved_count
        >= 1
    )

    assert (
        result.is_textual_error
        is None
    )

    unresolved = (
        result.unresolved_segments
    )

    assert any(
        segment.left_text == "مَعَ"
        and segment.right_text == "يحب"
        for segment in unresolved
    )


def test_generic_word_boundary_alignment() -> None:
    result = (
        QuranOrthographySegmentComparator()
        .compare(
            left_text="عبدالله",
            right_text="عبد الله",
            left_profile=IMLAEI,
            right_profile=IMLAEI,
        )
    )

    assert (
        result.relation
        == QuranOrthographySequenceRelation
        .ORTHOGRAPHICALLY_EQUIVALENT
    )

    assert result.all_resolved

    assert any(
        segment.relation
        == QuranOrthographyRelation
        .TOKEN_BOUNDARY_VARIANT
        for segment in result.segments
    )


def test_basmala_layout_is_structurally_resolved() -> None:
    result = (
        QuranOrthographySegmentComparator()
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
        == QuranOrthographySequenceRelation
        .ORTHOGRAPHICALLY_EQUIVALENT
    )

    assert result.all_resolved

    assert len(
        result.segments
    ) == 1

    assert (
        result.segments[0].relation
        == QuranOrthographyRelation
        .BASMALA_LAYOUT_VARIANT
    )


def test_reverse_source_direction_works() -> None:
    result = (
        QuranOrthographySegmentComparator()
        .compare(
            left_text=(
                "يا بني إسرائيل"
            ),
            right_text=(
                "يَـٰبَنِىٓ إِسْرَٰٓءِيلَ"
            ),
            left_profile=IMLAEI,
            right_profile=UTHMANI,
        )
    )

    assert (
        result.relation
        == QuranOrthographySequenceRelation
        .ORTHOGRAPHICALLY_EQUIVALENT
    )

    assert result.all_resolved

    assert (
        QuranOrthographyRuleId
        .VOCATIVE_YA_ALIF_OMISSION
        in result.rule_ids
    )

    assert (
        QuranOrthographyRuleId
        .ISRAIL_ALIF_RASM_VARIANT
        in result.rule_ids
    )