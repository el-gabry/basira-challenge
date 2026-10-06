from __future__ import annotations

import pytest

from basira.competition.jamhara import (
    canonicalize_jamhara_units,
    jamhara_source_url,
    parse_jamhara_word_page,
    validate_jamhara_response_url,
)

RICH_AR = """
<html>
<head>
<title>
معنى : التَّرْجَمَة - الترجمة - الجمهرة
</title>
</head>
<body>
<div class="entry-main-content wow fadeIn">
  <div>
    <h5 class="text-left">
      من معجم المصطلحات الشرعية
    </h5>
    <div>
      <p>
        <div class="alert alert-warning referral">
          يُحيل هذا المصطلح إلى مصطلح
          <strong>تَرْجَمَة الْقُرْآن</strong>
        </div>
      </p>
    </div>
  </div>
</div>

<div class="entry-main-content wow fadeIn">
  <div>
    <h5 class="text-left">
      من موسوعة المصطلحات الإسلامية
    </h5>
    <div>
      <p>
        <h2>التعريف اللغوي</h2>
        <p>البيان والتفسير.</p>

        <h2>المعنى الاصطلاحي</h2>
        <p>
          تفسير الكلام ونقله من لغة إلى أخرى.
        </p>

        <h2>الشرح المختصر</h2>
        <p>
          تنقسم الترجمة إلى ترجمة حرفية
          وترجمة للمعاني.
        </p>

        <h2>التعريف</h2>
        <p>
          نقل الكلام والأفكار من لغة إلى أخرى.
        </p>
      </p>
    </div>
  </div>
</div>
</body>
</html>
"""


RICH_EN = """
<html>
<head>
<title>
معنى : Translation - الترجمة - الجمهرة
</title>
</head>
<body>
<div class="entry-main-content wow fadeIn">
  <div>
    <h5 class="text-left">
      من موسوعة المصطلحات الإسلامية
    </h5>
    <div style="direction:ltr;text-align:left;">
      <p>
        <h2>المعنى الاصطلاحي</h2>
        <p>
          Interpreting words from one language
          to another.
        </p>

        <h2>الشرح المختصر</h2>
        <p>
          There are literal and meaning-based
          forms of translation.
        </p>

        <h2>التعريف</h2>
        <p>
          Expressing meaning in another language.
        </p>
      </p>
    </div>
  </div>
</div>
</body>
</html>
"""


DEFINITION_ONLY_EN = """
<html>
<head>
<title>
معنى : Islamic advocacy - الدعوة الإسلامية - الجمهرة
</title>
</head>
<body>
<div class="entry-main-content wow fadeIn">
  <div>
    <h5 class="text-left">
      من موسوعة المصطلحات الإسلامية
    </h5>
    <div style="direction:ltr;text-align:left;">
      <p>
        <h2>التعريف</h2>
        <p>
          A discipline concerned with conveying
          the message of Islam.
        </p>
      </p>
    </div>
  </div>
</div>
</body>
</html>
"""


IDENTITY_ONLY_EN = """
<html>
<head>
<title>
معنى : - بيان التأكيد - الجمهرة
</title>
</head>
<body>
<section id="related">
  <a href="/dictionary/word/2204/ar">العربية</a>
  <a href="/dictionary/word/2204/en">English</a>
</section>
</body>
</html>
"""


TITLE_ONLY_AR = """
<html>
<head>
<title>
معنى : يَوْمُ الـسَّبْت - يوم الـسبت - الجمهرة
</title>
</head>
<body>
<section id="related">
  <a href="/dictionary/word/12382/ar">العربية</a>
  <a href="/dictionary/word/12382/id">Indonesia</a>
</section>
</body>
</html>
"""


def test_source_url_is_deterministic() -> None:
    assert (
        jamhara_source_url(
            2704,
            "en",
        )
        == (
            "https://islamic-content.com/"
            "dictionary/word/2704/en"
        )
    )


def test_invalid_identity_is_rejected() -> None:
    with pytest.raises(
        ValueError
    ):
        jamhara_source_url(
            0,
            "en",
        )

    with pytest.raises(
        ValueError
    ):
        jamhara_source_url(
            2704,
            "EN",
        )


def test_rich_arabic_entry_is_extracted() -> None:
    unit = parse_jamhara_word_page(
        RICH_AR,
        word_id=2704,
        language="ar",
    )

    assert unit is not None

    assert (
        unit["word_id"]
        == 2704
    )

    assert (
        unit["language"]
        == "ar"
    )

    assert (
        unit["localized_term"]
        == "التَّرْجَمَة"
    )

    assert (
        unit["canonical_arabic_term"]
        == "الترجمة"
    )

    assert (
        unit["definition"]
        == (
            "نقل الكلام والأفكار "
            "من لغة إلى أخرى."
        )
    )

    assert unit[
        "linguistic_definition"
    ] == "البيان والتفسير."

    assert unit[
        "terminological_meaning"
    ] == (
        "تفسير الكلام ونقله "
        "من لغة إلى أخرى."
    )

    assert unit[
        "short_explanation"
    ]

    assert (
        "تَرْجَمَة الْقُرْآن"
        in unit["cross_reference"]
    )


def test_rich_english_entry_keeps_arabic_identity() -> None:
    unit = parse_jamhara_word_page(
        RICH_EN,
        word_id=2704,
        language="en",
    )

    assert unit is not None

    assert (
        unit["localized_term"]
        == "Translation"
    )

    assert (
        unit["canonical_arabic_term"]
        == "الترجمة"
    )

    assert (
        unit["definition"]
        == (
            "Expressing meaning "
            "in another language."
        )
    )


def test_definition_only_view_is_valid() -> None:
    unit = parse_jamhara_word_page(
        DEFINITION_ONLY_EN,
        word_id=4892,
        language="en",
    )

    assert unit is not None

    assert (
        unit["localized_term"]
        == "Islamic advocacy"
    )

    assert unit[
        "definition"
    ]

    assert (
        unit["short_explanation"]
        is None
    )


def test_identity_only_english_view_fails_closed() -> None:
    unit = parse_jamhara_word_page(
        IDENTITY_ONLY_EN,
        word_id=2204,
        language="en",
    )

    assert unit is None


def test_arabic_title_term_is_usable_lexical_payload() -> None:
    unit = parse_jamhara_word_page(
        TITLE_ONLY_AR,
        word_id=12382,
        language="ar",
    )

    assert unit is not None

    assert (
        unit["localized_term"]
        == "يَوْمُ الـسَّبْت"
    )

    assert (
        unit["canonical_arabic_term"]
        == "يوم الـسبت"
    )

    assert unit[
        "definition"
    ] is None


def test_authority_is_terminology_only() -> None:
    unit = parse_jamhara_word_page(
        RICH_EN,
        word_id=2704,
        language="en",
    )

    assert unit is not None

    role = unit[
        "source_role"
    ]

    assert (
        role["terminology_authority"]
        is True
    )

    assert (
        role["universal_primary_evidence"]
        is False
    )

    assert (
        role["cross_domain_primary_evidence"]
        is False
    )


def test_canonical_order_is_word_then_language() -> None:
    units = [
        {
            "word_id": 4892,
            "language": "en",
        },
        {
            "word_id": 2704,
            "language": "en",
        },
        {
            "word_id": 2704,
            "language": "ar",
        },
    ]

    result = canonicalize_jamhara_units(
        units
    )

    assert [
        (
            unit["word_id"],
            unit["language"],
        )
        for unit in result
    ] == [
        (2704, "ar"),
        (2704, "en"),
        (4892, "en"),
    ]


def test_duplicate_view_identity_is_rejected() -> None:
    with pytest.raises(
        ValueError
    ):
        canonicalize_jamhara_units(
            [
                {
                    "word_id": 2704,
                    "language": "en",
                },
                {
                    "word_id": 2704,
                    "language": "en",
                },
            ]
        )



def test_jamhara_live_response_cannot_leave_official_origin() -> None:
    requested = (
        "https://islamic-content.com/"
        "dictionary/word/2704/en"
    )

    validate_jamhara_response_url(
        requested,
        (
            "https://islamic-content.com/"
            "dictionary/word/2704/en"
        ),
    )

    with pytest.raises(
        ValueError
    ):
        validate_jamhara_response_url(
            requested,
            (
                "https://example.com/"
                "dictionary/word/2704/en"
            ),
        )

    with pytest.raises(
        ValueError
    ):
        validate_jamhara_response_url(
            requested,
            (
                "http://islamic-content.com/"
                "dictionary/word/2704/en"
            ),
        )
