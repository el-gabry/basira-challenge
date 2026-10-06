from __future__ import annotations

from basira.competition.bayyinat import (
    get_bayyinat_unit,
    search_bayyinat,
)


def test_direct_unit_access():
    unit = get_bayyinat_unit(
        50
    )

    assert (
        unit["ordinal"]
        == 50
    )

    assert unit[
        "short_answer"
    ]

    assert unit[
        "detailed_answer"
    ]


def assert_target_in_top_five(
    query: str,
    target: int,
) -> None:

    hits = search_bayyinat(
        query,
        limit=5,
    )

    ids = [
        hit[
            "ordinal"
        ]
        for hit in hits
    ]

    assert target in ids, (
        query,
        target,
        ids,
    )


def test_retrieval_quran_corruption():
    assert_target_in_top_five(
        "حذف بعض آيات القرآن عثمان",
        50,
    )


def test_retrieval_universality_of_islam():
    assert_target_in_top_five(
        "هل الإسلام خاص بالعرب",
        100,
    )


def test_retrieval_mercy_and_punishment():
    assert_target_in_top_five(
        "رحمة الله وعقاب العصاة",
        173,
    )


def test_retrieval_angels_recording_deeds():
    assert_target_in_top_five(
        "الملائكة وكتابة أعمال العباد",
        182,
    )


def test_retrieval_rights_of_dhimmi():
    assert_target_in_top_five(
        "حقوق أهل الذمة",
        260,
    )


def test_adapter_never_claims_universal_primary_evidence():
    hit = search_bayyinat(
        "تحريف القرآن",
        limit=1,
    )[0]

    role = hit[
        "source_role"
    ]

    assert (
        role[
            "primary_conversational_source"
        ]
        is True
    )

    assert (
        role[
            "universal_primary_evidence"
        ]
        is False
    )

    assert (
        role[
            "cross_domain_primary_routing_required"
        ]
        is True
    )

    assert (
        role[
            "internal_citation_contract_frozen"
        ]
        is False
    )
