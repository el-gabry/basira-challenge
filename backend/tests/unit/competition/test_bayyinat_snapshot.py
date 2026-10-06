from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[3]


SNAPSHOT = (
    ROOT
    / "data"
    / "competition"
    / "sources"
    / "shubuhat"
    / "bayyinat_units_v1.json"
)


CONTRACT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "bayyinat"
    / "content-contract.json"
)


def snapshot():
    return json.loads(
        SNAPSHOT.read_text(
            encoding="utf-8"
        )
    )


def contract():
    return json.loads(
        CONTRACT.read_text(
            encoding="utf-8"
        )
    )


def test_snapshot_has_263_units():
    d = snapshot()

    assert len(
        d["units"]
    ) == 263


def test_snapshot_artifact_identity():
    d = snapshot()

    assert (
        d["artifact"]["kind"]
        == "pdf"
    )

    assert (
        d["artifact"]["page_count"]
        == 1259
    )

    assert (
        d["artifact"]["sha256"]
        ==
        "619b7201833419b8fbf86c463208462b9a2a7f02ad2306a2667490f3b410ad4e"
    )


def test_every_unit_has_core_fields():
    d = snapshot()

    for unit in d["units"]:

        assert unit["title"]
        assert unit["question_text"]
        assert unit["short_answer"]
        assert unit["detailed_answer"]
        assert unit["provenance"]


def test_field_contract_counts():
    counts = snapshot()[
        "field_contract"
    ][
        "observed_counts"
    ]

    assert counts == {
        "similar":
            253,

        "gist":
            178,

        "short":
            263,

        "detailed":
            263,

        "conclusion":
            119,

        "keywords":
            243,

        "related":
            74,
    }


def test_four_anomalies_resolved():
    d = snapshot()

    units = {
        unit["ordinal"]:
            unit
        for unit in d["units"]
    }

    assert units[173]["short_answer"]
    assert units[182]["short_answer"]

    assert units[160]["detailed_answer"]
    assert units[260]["detailed_answer"]


def test_metadata_is_optional_and_independent():
    c = contract()[
        "metadata_model"
    ]

    assert c["keywords_optional"] is True
    assert c["related_questions_optional"] is True
    assert c["independent"] is True
    assert c["xor"] is False

    assert (
        c["neither_units"]
        == [
            95,
            227,
        ]
    )


def test_runtime_admission_is_deferred():
    d = snapshot()

    assert (
        d[
            "runtime_state"
        ][
            "router_admission"
        ]
        == "DEFERRED_TO_TRUST_SHIELD"
    )

    assert (
        d[
            "source_role"
        ][
            "internal_citation_contract_frozen"
        ]
        is False
    )
