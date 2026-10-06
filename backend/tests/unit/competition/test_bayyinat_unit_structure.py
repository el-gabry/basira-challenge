from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[3]


AUDIT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "bayyinat"
    / "unit-structure.json"
)


def audit():
    return json.loads(
        AUDIT.read_text(
            encoding="utf-8"
        )
    )


def test_frozen_bayyinat_artifact():
    d = audit()

    assert (
        d[
            "artifact"
        ][
            "kind"
        ]
        == "pdf"
    )

    assert (
        d[
            "artifact"
        ][
            "page_count"
        ]
        == 1259
    )

    assert (
        d[
            "artifact"
        ][
            "sha256"
        ]
        == "619b7201833419b8fbf86c463208462b9a2a7f02ad2306a2667490f3b410ad4e"
    )


def test_numbered_marker_contract():
    c = audit()[
        "title_marker_contract"
    ]

    assert (
        c[
            "global_hit_count"
        ]
        == 263
    )

    assert (
        c[
            "ordinal_sequence"
        ]
        == "1..263"
    )

    assert (
        c[
            "unique"
        ]
        is True
    )


def test_exact_mqa_cycle():
    c = audit()[
        "qa_contract"
    ]

    assert (
        c[
            "question_heading_count"
        ]
        == 263
    )

    assert (
        c[
            "answer_heading_count"
        ]
        == 263
    )

    assert (
        c[
            "m_to_q"
        ]
        == 263
    )

    assert (
        c[
            "q_to_a"
        ]
        == 263
    )

    assert (
        c[
            "a_to_next_m"
        ]
        == 262
    )


def test_keyword_footer_is_not_universal():
    c = audit()[
        "keyword_footer_hypothesis"
    ]

    assert (
        c[
            "global_contract"
        ]
        is False
    )

    assert (
        c[
            "units_with_detected_footer"
        ]
        == 243
    )

    assert (
        c[
            "units_without_detected_footer"
        ]
        == 20
    )

    assert (
        c[
            "allowed_as_universal_terminator"
        ]
        is False
    )


def test_nonfinal_units_end_at_next_marker():
    c = audit()[
        "unit_boundary_contract"
    ][
        "nonfinal_units"
    ]

    assert (
        c[
            "ordinals"
        ]
        == "1..262"
    )

    assert (
        c[
            "end_boundary"
        ]
        == "NEXT_NUMBERED_TITLE_MARKER_EXCLUSIVE"
    )

    assert (
        c[
            "validated"
        ]
        == "262/262"
    )


def test_final_unit_has_explicit_semantic_end():
    c = audit()[
        "unit_boundary_contract"
    ][
        "final_unit"
    ]

    assert (
        c[
            "ordinal"
        ]
        == 263
    )

    assert (
        c[
            "end_boundary"
        ]
        == "FINAL_KEYWORD_FOOTER_INCLUSIVE"
    )

    assert (
        c[
            "footer_page"
        ]
        == 1253
    )

    assert (
        c[
            "footer_line"
        ]
        == 8
    )

    assert (
        c[
            "references_begin_page"
        ]
        == 1255
    )

    assert (
        c[
            "survey_begin_page"
        ]
        == 1257
    )

    assert (
        c[
            "uses_eof_as_semantic_boundary"
        ]
        is False
    )


def test_full_unit_boundary_contract_is_frozen():
    d = audit()

    assert (
        d[
            "unit_boundary_contract"
        ][
            "status"
        ]
        == "FROZEN"
    )

    assert (
        len(
            d[
                "units"
            ]
        )
        == 263
    )


def test_freezing_boundaries_does_not_admit_runtime():
    state = audit()[
        "runtime_state"
    ]

    assert (
        state[
            "runtime_admission"
        ]
        == "PENDING_AUDIT"
    )

    assert (
        state[
            "adapter"
        ]
        == "NOT_IMPLEMENTED"
    )

    assert (
        state[
            "source_trust_passport"
        ]
        == "NOT_ISSUED"
    )
