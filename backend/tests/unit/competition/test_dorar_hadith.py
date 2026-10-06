from basira.competition.dorar_hadith import (
    parse_dorar_api_payload,
)


def test_parse_two_distinct_hadith_results() -> None:
    payload = {
        "ahadith": {
            "result": """
<div class="hadith">
1 - إنما الأعمال بالنيات .
</div>
<div class="hadith-info">
<span>الراوي:</span> عمر بن الخطاب
<span>المحدث:</span> النووي
<span>المصدر:</span> كتاب أ
<span>الصفحة أو الرقم:</span> 10
<span>خلاصة حكم المحدث:</span> صحيح
</div>

<div class="hadith">
2 - إنما الأعمال بالنيات .
</div>
<div class="hadith-info">
<span>الراوي:</span> علي بن أبي طالب
<span>المحدث:</span> محدث آخر
<span>المصدر:</span> كتاب ب
<span>الصفحة أو الرقم:</span> 20
<span>خلاصة حكم المحدث:</span> إسناده ضعيف
</div>
"""
        }
    }

    records = parse_dorar_api_payload(
        payload
    )

    assert len(records) == 2

    assert records[0].rank == 1
    assert (
        records[0].narrator
        == "عمر بن الخطاب"
    )
    assert records[0].verdict == "صحيح"

    assert records[1].rank == 2
    assert (
        records[1].narrator
        == "علي بن أبي طالب"
    )
    assert (
        records[1].verdict
        == "إسناده ضعيف"
    )


def test_parser_does_not_collapse_conflicting_results() -> None:
    payload = {
        "ahadith": {
            "result": """
<div class="hadith">
1 - نص واحد
</div>
<div class="hadith-info">
الراوي: راو أ
المحدث: محدث أ
المصدر: مصدر أ
الصفحة أو الرقم: 1
خلاصة حكم المحدث: صحيح
</div>

<div class="hadith">
2 - نص واحد
</div>
<div class="hadith-info">
الراوي: راو ب
المحدث: محدث ب
المصدر: مصدر ب
الصفحة أو الرقم: 2
خلاصة حكم المحدث: ضعيف
</div>
"""
        }
    }

    records = parse_dorar_api_payload(
        payload
    )

    assert len(records) == 2

    assert (
        records[0].verdict
        != records[1].verdict
    )


def test_missing_result_fails_closed() -> None:
    payload = {
        "ahadith": {}
    }

    try:
        parse_dorar_api_payload(
            payload
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "parser must fail closed"
        )


def test_empty_search_result_returns_no_records() -> None:
    payload = {
        "ahadith": {
            "result": (
                "<div>لا توجد نتائج</div>"
            )
        }
    }

    records = parse_dorar_api_payload(
        payload
    )

    assert records == []


def test_result_without_attribution_is_not_invented() -> None:
    payload = {
        "ahadith": {
            "result": """
<div class="hadith">
1 - نص تجريبي بلا بيانات نسبة
</div>
"""
        }
    }

    records = parse_dorar_api_payload(
        payload
    )

    # A matn block without its attribution block is not
    # converted into a usable hadith evidence record.
    assert records == []



def test_parse_dorar_hadith_search_html_keeps_full_article():
    from basira.competition.dorar_hadith import (
        parse_dorar_hadith_search_html,
    )

    html = """
    <section>
      <article>
        8 - إنما الأعمال بالنيات وإنما لكل امرئ ما نوى،
        فمن كانت هجرته إلى الله ورسوله فهجرته إلى الله ورسوله،
        ومن كانت هجرته إلى دنيا يصيبها أو امرأة يتزوجها
        فهجرته إلى ما هاجر إليه.
      </article>
    </section>
    """

    parsed = parse_dorar_hadith_search_html(
        html
    )

    assert 8 in parsed
    assert "فمن كانت هجرته" in parsed[8]
    assert "فهجرته إلى ما هاجر إليه" in parsed[8]



def test_full_text_matcher_does_not_use_rank():
    from basira.competition.dorar_hadith import (
        match_dorar_hadith_full_text,
    )

    candidates = (
        "حديث مختلف تمامًا لا يخص السجل المطلوب",
        (
            "إنما الأعمال بالنيات وإنما لكل امرئ ما نوى، "
            "فمن كانت هجرته إلى الله ورسوله فهجرته إلى الله ورسوله."
        ),
    )

    matched = match_dorar_hadith_full_text(
        (
            "إنما الأعمال بالنيات وإنما لكل امرئ ما نوى، "
            "فمن كانت هجرته إلى الله ورسوله فهجرته إلى الله ورسوله."
        ),
        candidates,
    )

    assert matched == candidates[1]


def test_full_text_matcher_rejects_explicit_truncation():
    from basira.competition.dorar_hadith import (
        match_dorar_hadith_full_text,
    )

    matched = match_dorar_hadith_full_text(
        "إنما الأعمال بالنيات ... الحديث",
        (
            (
                "إنما الأعمال بالنيات وإنما لكل امرئ ما نوى، "
                "فمن كانت هجرته إلى الله ورسوله."
            ),
        ),
    )

    assert matched is None


def test_full_text_matcher_rejects_ambiguous_prefix():
    from basira.competition.dorar_hadith import (
        match_dorar_hadith_full_text,
    )

    matched = match_dorar_hadith_full_text(
        "إنما الأعمال بالنيات",
        (
            (
                "إنما الأعمال بالنيات وإنما لكل امرئ ما نوى، "
                "فمن كانت هجرته إلى الله ورسوله."
            ),
            (
                "إنما الأعمال بالنيات وإنما لكل امرئ ما نوى، "
                "ومن نوى الخير فله ما نوى."
            ),
        ),
    )

    assert matched is None



def test_parse_dorar_hadith_search_articles_preserves_duplicate_visible_ranks():
    from basira.competition.dorar_hadith import (
        parse_dorar_hadith_search_articles,
    )

    html = """
    <article>
      1 - إنما الأعمال بالنيات وإنما لكل امرئ ما نوى.
    </article>
    <section>
      <article>
        1 - الدين النصيحة.
      </article>
    </section>
    """

    parsed = parse_dorar_hadith_search_articles(
        html
    )

    assert len(parsed) == 2
    assert "إنما الأعمال" in parsed[0]
    assert "الدين النصيحة" in parsed[1]
