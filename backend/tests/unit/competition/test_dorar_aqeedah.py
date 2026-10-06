from __future__ import annotations

import pytest

from basira.competition.dorar_aqeedah import (
    DorarAqeedahParseError,
    DorarAqeedahSourceNoteKind,
    parse_dorar_aqeedah_passage,
)


URL = "https://dorar.net/aqeeda/999"


def wrap(
    body: str,
    *,
    title: str = "عنوان عقدي",
) -> str:

    return f"""
<html>
<body>

<div id="cntnt" class="card-body">

<div class="card-title text-center py-2">
<h1>{title}</h1>
</div>

<div class="dorar-bg-lightGreen">
محتويات الصفحة
</div>

<div>
الرابط المختصر
</div>

<div class="w-100 mt-4">
{body}
</div>

<h3 id="more-titles">
انظر أيضا:
</h3>

<ul>
<li>موضوع جانبي</li>
</ul>

<div class="d-flex justify-content-between">
السابق التالي
</div>

</div>

</body>
</html>
"""


def test_parses_exact_canonical_root_title_and_body() -> None:
    passage = parse_dorar_aqeedah_passage(
        html=wrap(
            "شرح عقدي مباشر."
        ),
        canonical_url=URL,
    )

    assert passage.title == "عنوان عقدي"

    assert passage.explanation_text == (
        "شرح عقدي مباشر."
    )

    assert (
        passage.routing.canonical_root_count
        == 1
    )

    assert (
        passage.routing
        .direct_article_body_count
        == 1
    )


def test_ui_text_outside_article_body_is_excluded() -> None:
    passage = parse_dorar_aqeedah_passage(
        html=wrap(
            "المادة العلمية."
        ),
        canonical_url=URL,
    )

    for ui_text in (
        "محتويات الصفحة",
        "الرابط المختصر",
        "انظر أيضا",
        "السابق",
        "التالي",
        "موضوع جانبي",
    ):
        assert (
            ui_text
            not in passage.explanation_text
        )


def test_source_node_provenance_prevents_special_text_leak() -> None:
    passage = parse_dorar_aqeedah_passage(
        html=wrap(
            """
شرح قبل.

<span class="aaya">
QURAN_UNIQUE_TOKEN
</span>

<span class="sora">
<a href="/tafseer/1/1">
[الفاتحة: 1]
</a>
</span>

<span class="tip">
[9] SOURCE_UNIQUE_TOKEN
</span>

شرح بعد.
"""
        ),
        canonical_url=URL,
    )

    assert (
        "QURAN_UNIQUE_TOKEN"
        not in passage.explanation_text
    )

    assert (
        "SOURCE_UNIQUE_TOKEN"
        not in passage.explanation_text
    )

    assert (
        passage.quran_contexts[
            0
        ].text
        == "QURAN_UNIQUE_TOKEN"
    )

    assert (
        passage.source_notes[
            0
        ].text
        == "[9] SOURCE_UNIQUE_TOKEN"
    )

    assert (
        passage.routing
        .provenance_violation_count
        == 0
    )


def test_same_string_may_exist_in_explanation_and_quran_without_leak() -> None:
    passage = parse_dorar_aqeedah_passage(
        html=wrap(
            """
لفظ مشترك في الشرح.

<span class="aaya">
لفظ مشترك
</span>
"""
        ),
        canonical_url=URL,
    )

    assert (
        "لفظ مشترك"
        in passage.explanation_text
    )

    assert (
        passage.quran_contexts[
            0
        ].text
        == "لفظ مشترك"
    )

    assert (
        passage.routing
        .provenance_violation_count
        == 0
    )


def test_sora_anchor_is_one_reference_not_duplicate() -> None:
    passage = parse_dorar_aqeedah_passage(
        html=wrap(
            """
شرح.

<span class="sora">
<a href="/tafseer/53/1">
[النجم: 3-4]
</a>
</span>
"""
        ),
        canonical_url=URL,
    )

    assert len(
        passage.quran_references
    ) == 1

    reference = (
        passage.quran_references[
            0
        ]
    )

    assert reference.text == (
        "[النجم: 3-4]"
    )

    assert reference.href == (
        "/tafseer/53/1"
    )

    assert (
        reference
        .automatically_paired_to_context
        is False
    )


def test_quran_context_is_never_canonical_quran_witness() -> None:
    passage = parse_dorar_aqeedah_passage(
        html=wrap(
            """
شرح عقدي يسبق الاستشهاد.

<span class="aaya">
آية اختبارية
</span>
"""
        ),
        canonical_url=URL,
    )

    assert (
        passage.quran_contexts[
            0
        ].canonical_quran_witness
        is False
    )


def test_hadith_source_and_reported_grading_are_preserved_not_recomputed() -> None:
    passage = parse_dorar_aqeedah_passage(
        html=wrap(
            """
شرح.

<span class="tip">
[1016] أخرجه الترمذي (2658).
صححه ابن حجر، وصحح إسناده فلان.
</span>
"""
        ),
        canonical_url=URL,
    )

    note = passage.source_notes[
        0
    ]

    assert (
        DorarAqeedahSourceNoteKind
        .HADITH_SOURCE_NOTE
        in note.kinds
    )

    assert (
        DorarAqeedahSourceNoteKind
        .REPORTED_HADITH_GRADING
        in note.kinds
    )

    assert (
        note.requires_hadith_foundation
        is True
    )

    assert (
        note.independent_authenticity_judgment
        is False
    )


def test_grade_like_word_in_explanation_does_not_create_grading_note() -> None:
    passage = parse_dorar_aqeedah_passage(
        html=wrap(
            """
هذا حُسنُ بيانٍ في الشرح،
وليس حكمًا على حديث.
"""
        ),
        canonical_url=URL,
    )

    assert (
        passage.source_notes
        == ()
    )


def test_bibliographic_reference_never_promotes_aqeedah_authority() -> None:
    passage = parse_dorar_aqeedah_passage(
        html=wrap(
            """
شرح.

<span class="tip">
[1024] يُنظر: ((التمهيد)) (1/8).
</span>
"""
        ),
        canonical_url=URL,
    )

    note = passage.source_notes[
        0
    ]

    assert (
        DorarAqeedahSourceNoteKind
        .BIBLIOGRAPHIC_REFERENCE
        in note.kinds
    )

    assert note.cited_titles == (
        "التمهيد",
    )

    assert (
        note.aqeedah_authority_promotion
        is False
    )


def test_adapter_does_not_fabricate_structural_hadith_matn_channel() -> None:
    passage = parse_dorar_aqeedah_passage(
        html=wrap(
            """
قال النبي في النص السردي: مثال غير مهيكل.

<span class="tip">
[1] أخرجه مسلم (1).
</span>
"""
        ),
        canonical_url=URL,
    )

    assert (
        passage
        .hadith_matn_structurally_extractable
        is False
    )

    assert (
        "قال النبي"
        in passage.explanation_text
    )


def test_missing_canonical_root_fails_closed() -> None:
    with pytest.raises(
        DorarAqeedahParseError,
        match="canonical",
    ):
        parse_dorar_aqeedah_passage(
            html=(
                "<div class='w-100 mt-4'>"
                "نص"
                "</div>"
            ),
            canonical_url=URL,
        )


def test_multiple_direct_article_bodies_fail_closed() -> None:
    html = """
<div id="cntnt" class="card-body">

<div class="card-title">
<h1>عنوان</h1>
</div>

<div class="w-100 mt-4">
الأول
</div>

<div class="w-100 mt-4">
الثاني
</div>

</div>
"""

    with pytest.raises(
        DorarAqeedahParseError,
        match="exactly one direct",
    ):
        parse_dorar_aqeedah_passage(
            html=html,
            canonical_url=URL,
        )
