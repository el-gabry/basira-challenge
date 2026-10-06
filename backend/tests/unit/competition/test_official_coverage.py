from pathlib import Path

from basira.competition.official_coverage import (
    CoverageStatus,
    OfficialDomain,
    load_official_coverage_matrix,
)

ROOT = Path(
    __file__
).resolve().parents[3]


MATRIX = (
    ROOT
    / "data/competition/coverage/"
    "official-domain-coverage-v1.json"
)


def matrix():
    return load_official_coverage_matrix(
        MATRIX
    )


def test_all_required_official_domains_are_explicit() -> None:
    actual = {
        item.domain
        for item in matrix().domains
    }

    required = {
        OfficialDomain.QURAN,
        OfficialDomain.TAFSIR,
        OfficialDomain.HADITH,
        OfficialDomain.AQEEDAH_INTRO_TO_ISLAM,
        OfficialDomain.GENERAL_FIQH,
        OfficialDomain.SEERAH_HISTORY,
        OfficialDomain.SHUBUHAT_FAQ,
        OfficialDomain.TRANSLATION_TERMINOLOGY,
        OfficialDomain.DAWAH_GENERAL_CONTENT,
        OfficialDomain.AKHLAQ_VALUES_ADAB,
        OfficialDomain.RELIGIONS_SECTS_COMPARATIVE,
    }

    assert actual == required


def test_generic_shamela_fallback_is_prohibited_everywhere() -> None:
    assert all(
        item.generic_shamela_fallback_allowed
        is False
        for item in matrix().domains
    )


def test_existing_closed_foundations_are_runtime_governed() -> None:
    m = matrix()

    for domain in (
        OfficialDomain.QURAN,
        OfficialDomain.TAFSIR,
        OfficialDomain.HADITH,
        OfficialDomain.GENERAL_FIQH,
    ):
        assert (
            m.get(domain).status
            is CoverageStatus.GOVERNED_RUNTIME
        )


def test_remaining_official_directions_are_not_silently_claimed_runtime() -> None:
    m = matrix()

    assert (
        m.get(
            OfficialDomain
            .AQEEDAH_INTRO_TO_ISLAM
        ).status
        is CoverageStatus
        .GOVERNED_RUNTIME
    )

    assert (
        m.get(
            OfficialDomain.SEERAH_HISTORY
        ).status
        is CoverageStatus
        .GOVERNED_RUNTIME
    )

    assert (
        m.get(
            OfficialDomain.SHUBUHAT_FAQ
        ).status
        is CoverageStatus
        .GOVERNED_RUNTIME
    )

    for domain in (
        OfficialDomain.DAWAH_GENERAL_CONTENT,
        OfficialDomain.AKHLAQ_VALUES_ADAB,
        OfficialDomain.RELIGIONS_SECTS_COMPARATIVE,
    ):
        assert (
            m.get(domain).status
            is CoverageStatus
            .APPROVED_FAMILY_NOT_IMPLEMENTED
        )


def test_coverage_v1_is_not_prematurely_closed() -> None:
    m = matrix()

    assert m.coverage_v1_ready is False

    incomplete = {
        item.domain
        for item
        in m.incomplete_required_domains()
    }

    assert (
        OfficialDomain.AQEEDAH_INTRO_TO_ISLAM
        not in incomplete
    )

    assert (
        OfficialDomain.SEERAH_HISTORY
        not in incomplete
    )

    assert (
        OfficialDomain.SHUBUHAT_FAQ
        not in incomplete
    )



def test_personal_fatwa_is_explicitly_out_of_scope() -> None:
    m = matrix()

    assert (
        "independent_personal_fatwa"
        in m.out_of_scope
    )


def test_no_required_domain_is_marked_not_covered() -> None:
    """
    Every official direction must at least have an explicit
    approved-source rule, even where implementation is pending.
    """

    for item in matrix().required_domains():

        assert (
            item.status
            is not CoverageStatus.NOT_COVERED
        )

        assert item.official_source_rule.strip()


def test_aqeedah_period_rule_does_not_propagate_to_fiqh() -> None:
    m = matrix()

    aqeedah_rule = (
        m.get(
            OfficialDomain
            .AQEEDAH_INTRO_TO_ISLAM
        ).official_source_rule
    )

    fiqh_rule = (
        m.get(
            OfficialDomain
            .GENERAL_FIQH
        ).official_source_rule
    )

    assert (
        "FIRST_THREE_CENTURIES"
        in aqeedah_rule
    )

    assert (
        "FIRST_THREE_CENTURIES"
        not in fiqh_rule
    )

    assert (
        "MADHHAB_FIQH_BOOK"
        in fiqh_rule
    )

    assert (
        "DORAR_FIQH"
        in fiqh_rule
    )
