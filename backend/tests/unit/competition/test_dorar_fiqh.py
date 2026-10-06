from basira.competition.dorar_fiqh import (
    parse_dorar_fiqh_article,
)
from basira.competition.fiqh_policy import (
    Madhhab,
)


def test_extracts_two_attributed_positions() -> None:
    html = """
<html>
<title>مسألة فقهية</title>
<body>
<h1>مسألة فقهية</h1>
اختلف أهل العلم على قولين:
القول الأول:
لا ينقض، وهو مذهب الحنفية
((كتاب أ)) (1/20).
القول الثاني:
ينقض، وهو مذهب الشافعية
((كتاب ب)) (2/30).
</body>
</html>
"""

    article = parse_dorar_fiqh_article(
        html=html,
        canonical_url=(
            "https://dorar.net/feqhia/1"
        ),
    )

    assert (
        article.explicit_disagreement
        is True
    )

    assert len(
        article.positions
    ) == 2

    assert (
        Madhhab.HANAFI
        in article.positions[0].madhhabs
    )

    assert (
        Madhhab.SHAFII
        in article.positions[1].madhhabs
    )

    assert article.positions[0].citations
    assert article.positions[1].citations


def test_no_disagreement_is_not_invented() -> None:
    html = """
<html>
<title>مسألة</title>
<body>
<h1>مسألة</h1>
هذا حكم فقهي منقول.
</body>
</html>
"""

    article = parse_dorar_fiqh_article(
        html=html,
        canonical_url=(
            "https://dorar.net/feqhia/2"
        ),
    )

    assert (
        article.explicit_disagreement
        is False
    )

    assert article.positions == ()


def test_consensus_is_only_explicitly_detected() -> None:
    html = """
<html>
<head>
<title>
مسألة اختبار الاتفاق - الموسوعة الفقهية - الدرر السنية
</title>
</head>
<body>
<h1>مسألة اختبار الاتفاق</h1>
وهذا باتفاق المذاهب الفقهية الأربعة.
</body>
</html>
"""

    article = parse_dorar_fiqh_article(
        html=html,
        canonical_url=(
            "https://dorar.net/feqhia/3"
        ),
    )

    assert (
        article.explicit_consensus_language
        is True
    )


def test_multiple_madhhab_mentions_do_not_imply_consensus() -> None:
    html = """
<html>
<head>
<title>
مسألة اختبار تعدد المذاهب - الموسوعة الفقهية - الدرر السنية
</title>
</head>
<body>
<h1>مسألة اختبار تعدد المذاهب</h1>
ذكر الحنفية قولًا، وذكر الشافعية قولًا آخر.
</body>
</html>
"""

    article = parse_dorar_fiqh_article(
        html=html,
        canonical_url=(
            "https://dorar.net/feqhia/4"
        ),
    )

    assert (
        article.explicit_consensus_language
        is False
    )



def test_parser_ignores_non_article_and_faq_position_repetitions() -> None:
    html = """
<html>
<head>
<title>
المطلب الثاني: مس المرأة فرجها - الموسوعة الفقهية - الدرر السنية
</title>
</head>
<body>

<div>
محتوى عام من الموقع:
القول الثاني: نص غير متعلق بالمادة.
</div>

<h1>المطلب الثاني: مس المرأة فرجها</h1>

<p>
اختلف أهل العلم في المسألة على قولين:
</p>

<p>
القول الأول:
لا ينقض الوضوء، وهو مذهب الحنفية والمالكية.
((كتاب أ)) (1/20).
</p>

<p>
القول الثاني:
ينقض الوضوء، وهو مذهب الشافعية والحنابلة.
((كتاب ب)) (2/30).
</p>

<div>
المادة في سؤال وجواب

السؤال:
ما الأقوال؟

الجواب:
القول الأول كذا، والقول الثاني كذا.
</div>

</body>
</html>
"""

    article = parse_dorar_fiqh_article(
        html=html,
        canonical_url=(
            "https://dorar.net/feqhia/424"
        ),
    )

    assert [
        item.ordinal
        for item in article.positions
    ] == [1, 2]

    assert len(article.positions) == 2

    assert (
        "المادة في سؤال وجواب"
        not in article.full_text
    )



def test_real_dorar_diacritized_position_marker_is_detected() -> None:
    html = """
<html>
<head>
<title>
المطلب الثاني: مس المرأة فرجها - الموسوعة الفقهية - الدرر السنية
</title>
</head>
<body>

<h1>المطلب الثاني: مس المرأة فرجها</h1>

اختلف أهل العلم في المسألة على قولين:

القول الأوّل:
لا ينقض الوضوء، وهو مذهب الحنفية والمالكية.
((كتاب أول)) (1/20).

القول الثاني:
ينقض الوضوء، وهو مذهب الشافعية والحنابلة.
((كتاب ثان)) (2/30).

المادة في سؤال وجواب

القول الأول مختصر.
القول الثاني مختصر.

</body>
</html>
"""

    article = parse_dorar_fiqh_article(
        html=html,
        canonical_url=(
            "https://dorar.net/feqhia/424"
        ),
    )

    assert [
        position.ordinal
        for position in article.positions
    ] == [1, 2]

    assert len(article.positions) == 2

    assert (
        "المادة في سؤال وجواب"
        not in article.full_text
    )



def test_diacritized_madhhab_names_preserve_shafii_and_hanbali() -> None:
    html = """
<html>
<head>
<title>
المطلب الثاني: اختبار - الموسوعة الفقهية - الدرر السنية
</title>
</head>
<body>

<h1>المطلب الثاني: اختبار</h1>

اختلف أهل العلم على قولين:

القول الأوّل:
وهو مذهَبُ الحنفيَّة والمالكيَّة.
((كتاب أ)) (1/10).

القول الثاني:
وهو مذهَبُ الشَّافعيَّة والحنابلة.
((كتاب ب)) (2/20).

</body>
</html>
"""

    article = parse_dorar_fiqh_article(
        html=html,
        canonical_url=(
            "https://dorar.net/feqhia/999"
        ),
    )

    assert len(article.positions) == 2

    first = {
        item.value
        for item
        in article.positions[0].madhhabs
    }

    second = {
        item.value
        for item
        in article.positions[1].madhhabs
    }

    assert first == {
        "hanafi",
        "maliki",
    }

    assert second == {
        "shafii",
        "hanbali",
    }
