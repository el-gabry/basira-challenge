import pytest

from basira.evidence.fiqh_units import (
    FiqhStructuralUnitBuilder,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)


def _projected_passage(
    *,
    text: str,
    metadata: dict[
        str,
        str,
    ] | None = None,
) -> ScholarlyPassage:
    base_metadata = {
        "projection_kind":
            "fiqh_targeted_exact_slice",
        "parent_passage_id":
            "book:1:page:10",
        "projection_char_start":
            "20",
        "projection_char_end":
            str(20 + len(text)),
        "madhhab":
            "shafii",
    }

    if metadata:
        base_metadata.update(
            metadata
        )

    return ScholarlyPassage(
        passage_id=(
            "book:1:page:10:"
            "fiqh-projection:20:99"
        ),
        source_id="shamela-test",
        domain=ScholarlyDomain.FIQH,
        work_id="book-1",
        work_title="كتاب فقهي",
        text=text,
        section_title=(
            "باب نواقض الوضوء"
        ),
        page="10",
        metadata=base_metadata,
    )


def test_structural_unit_preserves_exact_projected_text():
    text = (
        "وينتقض الوضوء بلمس المرأة "
        "عند تحقق شروطه."
    )

    unit = (
        FiqhStructuralUnitBuilder()
        .from_projected_passage(
            _projected_passage(
                text=text
            )
        )
    )

    assert (
        unit.exact_text
        == text
    )

    assert (
        unit.parent_passage_id
        == "book:1:page:10"
    )

    assert (
        unit.madhhab
        == "shafii"
    )

    assert (
        unit.issue
        == "باب نواقض الوضوء"
    )


def test_missing_semantic_structure_stays_missing():
    unit = (
        FiqhStructuralUnitBuilder()
        .from_projected_passage(
            _projected_passage(
                text=(
                    "وينتقض الوضوء "
                    "بلمس المرأة."
                )
            )
        )
    )

    assert unit.ruling is None
    assert unit.dalil is None
    assert (
        unit.wajh_al_dalala
        is None
    )
    assert unit.conditions == ()
    assert unit.exceptions == ()
    assert (
        unit.disagreement
        is None
    )

    assert (
        not unit.has_explicit_ruling
    )

    assert (
        not unit.has_explicit_dalil
    )


def test_explicit_structural_fields_must_be_literal_source_text():
    text = (
        "الحكم: ينتقض الوضوء باللمس. "
        "والشرط: أن يكون بلا حائل. "
        "والدليل: قوله تعالى كذا."
    )

    unit = (
        FiqhStructuralUnitBuilder()
        .from_projected_passage(
            _projected_passage(
                text=text,
                metadata={
                    "fiqh_ruling":
                        (
                            "ينتقض الوضوء "
                            "باللمس"
                        ),
                    "fiqh_conditions":
                        (
                            "أن يكون بلا حائل"
                        ),
                    "fiqh_dalil":
                        (
                            "قوله تعالى كذا"
                        ),
                },
            )
        )
    )

    assert (
        unit.ruling
        == "ينتقض الوضوء باللمس"
    )

    assert (
        unit.conditions
        == (
            "أن يكون بلا حائل",
        )
    )

    assert (
        unit.dalil
        == "قوله تعالى كذا"
    )


def test_multiple_conditions_remain_separate_exact_units():
    text = (
        "يشترط القبض في المجلس، "
        "ويشترط انتفاء التأجيل."
    )

    unit = (
        FiqhStructuralUnitBuilder()
        .from_projected_passage(
            _projected_passage(
                text=text,
                metadata={
                    "fiqh_conditions": (
                        "القبض في المجلس"
                        "||"
                        "انتفاء التأجيل"
                    ),
                },
            )
        )
    )

    assert (
        unit.conditions
        == (
            "القبض في المجلس",
            "انتفاء التأجيل",
        )
    )


def test_builder_rejects_manufactured_ruling():
    passage = _projected_passage(
        text=(
            "ذكر المصنف مسألة "
            "في البيوع."
        ),
        metadata={
            "fiqh_ruling":
                "البيتكوين حرام",
        },
    )

    with pytest.raises(
        ValueError,
        match=(
            "fiqh_ruling must be "
            "an exact substring"
        ),
    ):
        (
            FiqhStructuralUnitBuilder()
            .from_projected_passage(
                passage
            )
        )


def test_builder_rejects_manufactured_dalil():
    passage = _projected_passage(
        text=(
            "الحكم مذكور هنا دون "
            "نقل دليل."
        ),
        metadata={
            "fiqh_dalil":
                "قال الله تعالى كذا",
        },
    )

    with pytest.raises(
        ValueError,
        match=(
            "fiqh_dalil must be "
            "an exact substring"
        ),
    ):
        (
            FiqhStructuralUnitBuilder()
            .from_projected_passage(
                passage
            )
        )


def test_builder_requires_targeted_projection():
    passage = ScholarlyPassage(
        passage_id="book:1:10",
        source_id="source",
        domain=ScholarlyDomain.FIQH,
        work_id="book-1",
        work_title="كتاب فقهي",
        text="صفحة كاملة في الفقه.",
        metadata={
            "madhhab": "maliki",
        },
    )

    with pytest.raises(
        ValueError,
        match=(
            "targeted governed "
            "projection"
        ),
    ):
        (
            FiqhStructuralUnitBuilder()
            .from_projected_passage(
                passage
            )
        )


def test_disagreement_is_not_inferred_from_multiple_madhhabs():
    text = (
        "هذا نص منقول في المسألة."
    )

    unit = (
        FiqhStructuralUnitBuilder()
        .from_projected_passage(
            _projected_passage(
                text=text,
                metadata={
                    "madhhab":
                        "hanafi",
                },
            )
        )
    )

    assert (
        unit.madhhab
        == "hanafi"
    )

    assert (
        unit.disagreement
        is None
    )

    assert (
        not unit
        .has_explicit_disagreement
    )


def test_explicit_disagreement_must_be_source_derived():
    text = (
        "واختلف أهل العلم في المسألة "
        "على قولين."
    )

    unit = (
        FiqhStructuralUnitBuilder()
        .from_projected_passage(
            _projected_passage(
                text=text,
                metadata={
                    "fiqh_disagreement":
                        (
                            "واختلف أهل العلم "
                            "في المسألة على قولين"
                        ),
                },
            )
        )
    )

    assert (
        unit.disagreement
        == (
            "واختلف أهل العلم "
            "في المسألة على قولين"
        )
    )
