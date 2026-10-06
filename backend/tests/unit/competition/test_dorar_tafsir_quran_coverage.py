from __future__ import annotations

import pytest

from basira.competition.dorar_tafsir_retrieval import (
    DorarTafsirPayloadError,
    extract_quran_references,
)


def extract(
    html: str,
) -> tuple[
    str,
    ...,
]:
    return extract_quran_references(
        html=html,
        canonical_url=("https://dorar.net/tafseer/2/43"),
    )


def test_passage_id_is_not_quran_ayah():
    result = extract(
        """
        <h6>
          الآيات (254 - 257)
        </h6>
        """
    )

    assert result == (
        "2:254",
        "2:255",
        "2:256",
        "2:257",
    )

    assert "2:43" not in result


def test_title_is_structural_metadata():
    assert extract(
        """
        <html>
          <head>
            <title>
              سورة البقرة
              الآيات (254 - 257)
            </title>
          </head>
        </html>
        """
    ) == (
        "2:254",
        "2:255",
        "2:256",
        "2:257",
    )


def test_meta_title_can_supply_coverage():
    assert extract(
        """
        <meta
          property="og:title"
          content="سورة البقرة - الآيات (254 - 257)"
        >
        """
    ) == (
        "2:254",
        "2:255",
        "2:256",
        "2:257",
    )


def test_arabic_digits_diacritics_and_bidi():
    result = extract("<h6>الآيَات\u200f (٢٥٤ – ٢٥٧)</h6>")

    assert result == (
        "2:254",
        "2:255",
        "2:256",
        "2:257",
    )


def test_nested_heading_markup():
    result = extract(
        """
        <h6>
          <span>الآيات</span>
          <b>(254 - 257)</b>
        </h6>
        """
    )

    assert "2:255" in result


def test_single_ayah():
    assert extract("<h6>الآية (255)</h6>") == ("2:255",)


def test_multiple_distinct_ranges_fail_closed():
    with pytest.raises(
        DorarTafsirPayloadError,
        match="conflicting",
    ):
        extract(
            """
            <title>
              الآيات (254 - 257)
            </title>
            <h6>
              الآيات (1 - 5)
            </h6>
            """
        )


def test_missing_coverage_fails_closed():
    with pytest.raises(
        DorarTafsirPayloadError,
        match="coverage",
    ):
        extract("<html>no coverage</html>")


def test_absent_and_conflicting_coverage_are_distinct():
    from basira.competition.dorar_tafsir_retrieval import (
        DorarTafsirCoverageUnavailable,
    )

    with pytest.raises(DorarTafsirCoverageUnavailable):
        extract_quran_references(
            html="<html>canonical</html>",
            canonical_url=("https://dorar.net/tafseer/2/43"),
        )

    with pytest.raises(
        DorarTafsirPayloadError,
        match="conflicting",
    ):
        extract_quran_references(
            html=("<h6>الآيات (254 - 257)</h6><h5>الآيات (1 - 2)</h5>"),
            canonical_url=("https://dorar.net/tafseer/2/43"),
        )
