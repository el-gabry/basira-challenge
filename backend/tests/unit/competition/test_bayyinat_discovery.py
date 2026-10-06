from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[3]


DISCOVERY = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "bayyinat"
    / "discovery.json"
)


def discovery():
    return json.loads(
        DISCOVERY.read_text(
            encoding="utf-8"
        )
    )


def test_exact_official_artifact_identity():
    a = discovery()[
        "artifact"
    ]

    assert (
        a["page_count"]
        == 1259
    )

    assert (
        a["sha256"]
        == "619b7201833419b8fbf86c463208462b9a2a7f02ad2306a2667490f3b410ad4e"
    )


def test_exact_qa_headings_are_stable():
    s = discovery()[
        "structure"
    ]

    assert (
        s[
            "question_heading_count"
        ]
        == 263
    )

    assert (
        s[
            "answer_heading_count"
        ]
        == 263
    )

    assert (
        s[
            "explicit_qa_heading_contract"
        ]
        == "STRUCTURALLY_STABLE"
    )


def test_every_question_heading_pairs_with_answer():
    s = discovery()[
        "structure"
    ]

    assert (
        s[
            "qa_pair_count"
        ]
        == 263
    )

    assert (
        s[
            "qa_pair_failure_count"
        ]
        == 0
    )

    assert (
        s[
            "qa_pairing_ratio"
        ]
        == 1.0
    )


def test_qa_event_stream_alternates():
    t = discovery()[
        "structure"
    ][
        "qa_transition_counts"
    ]

    assert (
        t["Q_TO_A"]
        == 263
    )

    assert (
        t["A_TO_Q"]
        == 262
    )

    assert (
        t["Q_TO_Q"]
        == 0
    )

    assert (
        t["A_TO_A"]
        == 0
    )


def test_numbered_question_boundary_is_not_frozen():
    d = discovery()

    assert (
        d[
            "structure"
        ][
            "question_boundary_contract"
        ]
        == "NOT_YET_FROZEN"
    )

    role = d[
        "source_role_findings"
    ]

    assert (
        role[
            "question_boundary_contract_frozen"
        ]
        is False
    )

    assert (
        role[
            "numbered_question_boundary_contract_frozen"
        ]
        is False
    )


def test_bayyinat_is_conversational_not_universal_evidence():
    role = discovery()[
        "source_role_findings"
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
            "cross_domain_claims_require_primary_domain_routing"
        ]
        is True
    )


def test_cross_domain_signals_exist():
    signals = discovery()[
        "cross_domain_signals"
    ]

    for domain in (
        "quran",
        "hadith",
        "aqeedah",
        "fiqh",
        "history",
    ):

        assert (
            signals[
                domain
            ]
            > 0
        )


def test_citation_channel_is_still_unfrozen():
    role = discovery()[
        "source_role_findings"
    ]

    assert (
        role[
            "citation_channel_contract_frozen"
        ]
        is False
    )

    assert (
        role[
            "lexical_citation_equals_verified_primary_evidence"
        ]
        is False
    )


def test_runtime_remains_pending():
    d = discovery()

    assert (
        d[
            "runtime_admission"
        ]
        == "PENDING_AUDIT"
    )

    assert (
        d[
            "adapter"
        ]
        == "NOT_IMPLEMENTED"
    )

    assert (
        d[
            "source_trust_passport"
        ]
        == "NOT_ISSUED"
    )


def test_artifact_kind_remains_pdf_after_qa_characterization():
    """
    Regression guard for the artifact/Q-A variable collision.
    """

    a = discovery()[
        "artifact"
    ]

    assert (
        a["kind"]
        == "pdf"
    )
