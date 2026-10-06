import pytest

from basira.competition.dorar_tafsir import (
    DorarTafsirSectionKind,
    parse_dorar_tafsir_passage,
)


def test_search_and_navigation_labels_are_not_sections() -> None:
    html = """
<html>
<body>

<form>
<label>المعنى الإجمالي</label>
<label>تفسير الآيات</label>
</form>

<div id="cntnt">

<nav>
<a>المعنى الإجمالي</a>
<a>تفسير الآيات</a>
</nav>

<div class="row amiri_custom_content">

<article id="tt9">
<h5>المعنى الإجمالي:</h5>
<p>هذا هو الشرح الحقيقي.</p>
</article>

</div>
</div>

</body>
</html>
"""

    result = parse_dorar_tafsir_passage(
        html=html,
        canonical_url=(
            "https://dorar.net/tafseer/1/1"
        ),
    )

    assert len(result.sections) == 1

    assert (
        result.sections[0].section_kind
        is DorarTafsirSectionKind.GENERAL_MEANING
    )


def test_quran_text_is_separated_from_explanation() -> None:
    html = """
<div id="cntnt">
<article id="tt4">

<h5>تفسير الآيات:</h5>

<p>
هذا شرح للمفسر.

<span class="aaya">
الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ
</span>

ثم يستمر الشرح.

<span class="sora">
<a>[الفاتحة: 2]</a>
</span>

</p>

</article>
</div>
"""

    result = parse_dorar_tafsir_passage(
        html=html,
        canonical_url=(
            "https://dorar.net/tafseer/1/1"
        ),
    )

    section = result.sections[0]

    assert (
        section.section_kind
        is DorarTafsirSectionKind.TAFSIR_AYAT
    )

    assert (
        "هذا شرح للمفسر"
        in section.explanation_text
    )

    assert (
        "الْحَمْدُ لِلَّهِ"
        not in section.explanation_text
    )

    assert section.quran_contexts == (
        "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
    )

    assert section.quran_references == (
        "[الفاتحة: 2]",
    )


def test_tip_is_source_evidence_not_explanation_text() -> None:
    html = """
<div id="cntnt">
<article id="tt4">

<h5>تفسير الآيات</h5>

<p>
شرح.

<span class="tip">
[1] رواه البخاري (1).
</span>

</p>

</article>
</div>
"""

    result = parse_dorar_tafsir_passage(
        html=html,
        canonical_url=(
            "https://dorar.net/tafseer/1/1"
        ),
    )

    section = result.sections[0]

    assert (
        "رواه البخاري"
        not in section.explanation_text
    )

    assert len(
        section.narration_citations
    ) == 1


def test_reported_grade_is_extracted_only_from_citation() -> None:
    html = """
<div id="cntnt">
<article id="tt4">

<h5>تفسير الآيات</h5>

<p>
حسن الافتتاح من البلاغة.

<span class="tip">
[48] رواه أحمد.
قال فلان: رجاله رجال الصحيح،
وحسن إسناده ابن حجر،
وصححه الألباني.
</span>

</p>

</article>
</div>
"""

    result = parse_dorar_tafsir_passage(
        html=html,
        canonical_url=(
            "https://dorar.net/tafseer/1/1"
        ),
    )

    section = result.sections[0]

    assert len(
        section.reported_grade_citations
    ) == 1

    claim = (
        section.reported_grade_citations[0]
    )

    assert (
        "authenticated"
        in claim.explicit_grade_language
    )

    assert (
        "graded_hasan"
        in claim.explicit_grade_language
    )

    assert (
        "rijal_sahih"
        in claim.explicit_grade_language
    )


def test_plain_word_hasan_does_not_become_grade() -> None:
    html = """
<div id="cntnt">
<article id="tt18">

<h5>بلاغة الآيات</h5>

<p>
حسن الافتتاح وبراعة المطلع.
</p>

</article>
</div>
"""

    result = parse_dorar_tafsir_passage(
        html=html,
        canonical_url=(
            "https://dorar.net/tafseer/1/1"
        ),
    )

    section = result.sections[0]

    assert (
        section.reported_grade_citations
        == ()
    )


def test_duplicate_canonical_sections_fail_closed() -> None:
    html = """
<div id="cntnt">

<article id="tt9">
<h5>المعنى الإجمالي</h5>
<p>الأول</p>
</article>

<article id="copy">
<h5>المعنى الإجمالي</h5>
<p>الثاني</p>
</article>

</div>
"""

    with pytest.raises(
        ValueError,
        match="duplicate",
    ):
        parse_dorar_tafsir_passage(
            html=html,
            canonical_url=(
                "https://dorar.net/tafseer/1/1"
            ),
        )


def test_non_dorar_tafsir_url_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="canonical",
    ):
        parse_dorar_tafsir_passage(
            html="<html></html>",
            canonical_url=(
                "https://example.com/1"
            ),
        )



def test_void_br_tags_do_not_swallow_later_canonical_sections() -> None:
    html = """
<div id="cntnt">

<article id="tt9">
<h5>المعنى الإجمالي:</h5>
<p>
شرح أول.
<br><br><br><br><br><br>
</p>
</article>

<article id="tt7">
<h5>غريب الكلمات:</h5>
<p>
شرح الغريب.
<br><br><br>
</p>
</article>

<article id="tt8">
<h5>مشكل الإعراب:</h5>
<p>
شرح الإعراب.
<br><br><br><br><br><br><br><br>
</p>
</article>

<article id="tt4">
<h5>تفسير الآيات:</h5>
<p>
شرح الآية.

<br><br><br><br><br><br><br><br><br>

<span class="aaya">
الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ
</span>

<span class="sora">
<a href="/quran/1/2">[الفاتحة: 2]</a>
</span>

<span class="tip">
<a href="/hadith/test">
[1] رواه أحمد، وصححه فلان.
</a>
</span>
</p>
</article>

<article id="tt16">
<h5>الفوائد التربويَّة:</h5>
<p>فائدة تربوية.</p>
</article>

<article id="tt17">
<h5>الفوائد العلميَّة واللَّطائف:</h5>
<p>فائدة علمية.</p>
</article>

<article id="tt18">
<h5>بلاغة الآيات:</h5>
<p>بلاغة.</p>
</article>

</div>
"""

    result = parse_dorar_tafsir_passage(
        html=html,
        canonical_url=(
            "https://dorar.net/tafseer/1/1"
        ),
    )

    assert {
        section.section_kind
        for section in result.sections
    } == {
        DorarTafsirSectionKind.GENERAL_MEANING,
        DorarTafsirSectionKind.WORD_MEANING,
        DorarTafsirSectionKind.GRAMMAR,
        DorarTafsirSectionKind.TAFSIR_AYAT,
        DorarTafsirSectionKind.EDUCATIONAL_BENEFITS,
        DorarTafsirSectionKind.SCHOLARLY_BENEFITS,
        DorarTafsirSectionKind.RHETORIC,
    }

    tafsir = next(
        section
        for section in result.sections
        if (
            section.section_kind
            is DorarTafsirSectionKind.TAFSIR_AYAT
        )
    )

    assert tafsir.quran_contexts == (
        "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
    )

    assert tafsir.quran_references == (
        "[الفاتحة: 2]",
    )

    assert len(
        tafsir.narration_citations
    ) == 1

    assert len(
        tafsir.reported_grade_citations
    ) == 1



def test_same_quran_string_in_explanation_is_not_a_provenance_leak() -> None:
    html = """
<div id="cntnt">

<article id="tt4">

<h5>تفسير الآيات:</h5>

<p>

في قوله:

<span class="aaya">
مالِك
</span>

تفسير القراءة:

مالِك هو المتصرف في ملكه.

وفي قوله:

<span class="aaya">
إِيَّاكَ
</span>

ثم يذكر المفسر لفظ إِيَّاكَ مرة أخرى أثناء الشرح.

</p>

</article>

</div>
"""

    result = parse_dorar_tafsir_passage(
        html=html,
        canonical_url=(
            "https://dorar.net/tafseer/1/1"
        ),
    )

    section = result.sections[0]

    # Same characters legitimately exist in both semantic
    # roles.
    assert "مالِك" in section.quran_contexts
    assert "مالِك" in section.explanation_text

    assert "إِيَّاكَ" in section.quran_contexts
    assert "إِيَّاكَ" in section.explanation_text

    # Provenance, not substring equality, is the invariant.
    assert (
        section.quran_context_text_node_count
        >= 2
    )

    assert (
        section
        .quran_context_text_nodes_routed_to_explanation
        == 0
    )
