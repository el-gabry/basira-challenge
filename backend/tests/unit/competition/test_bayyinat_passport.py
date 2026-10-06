from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(
    __file__
).resolve().parents[3]


PASSPORT = (
    ROOT
    / "data"
    / "competition"
    / "passports"
    / "bayyinat.json"
)


MANIFEST = (
    ROOT
    / "data"
    / "competition"
    / "manifests"
    / "shubuhat"
    / "official-shubuhat-policy-v1.json"
)


COVERAGE = (
    ROOT
    / "data"
    / "competition"
    / "coverage"
    / "official-domain-coverage-v1.json"
)


def load(path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def test_bayyinat_passport_is_issued():
    p = load(
        PASSPORT
    )

    assert (
        p[
            "runtime_admission"
        ]
        == "GOVERNED_CONVERSATIONAL_RUNTIME"
    )

    assert (
        p[
            "authority_role"
        ]
        == "PRIMARY_CONVERSATIONAL_SOURCE"
    )

    assert (
        p[
            "runtime_source_id"
        ]
        == "bayyinat-v1"
    )


def test_exact_official_artifact_is_pinned():
    p = load(
        PASSPORT
    )

    a = p[
        "artifact"
    ]

    assert (
        a[
            "kind"
        ]
        == "pdf"
    )

    assert (
        a[
            "page_count"
        ]
        == 1259
    )

    assert (
        a[
            "sha256"
        ]
        == (
            "619b7201833419b8fbf86c463208462b"
            "9a2a7f02ad2306a2667490f3b410ad4e"
        )
    )


def test_canonical_unit_contract():
    p = load(
        PASSPORT
    )

    c = p[
        "canonical_units"
    ]

    assert (
        c[
            "count"
        ]
        == 263
    )

    assert (
        c[
            "unit_boundary_contract"
        ]
        == "FROZEN"
    )


def test_bayyinat_is_not_universal_primary_evidence():
    p = load(
        PASSPORT
    )

    assert (
        "UNIVERSAL_PRIMARY_EVIDENCE"
        in p[
            "prohibited_inferences"
        ]
    )

    assert (
        p[
            "citation_policy"
        ][
            "cross_domain_claims_require_primary_domain_evidence"
        ]
        is True
    )


def test_manifest_runtime_admitted():
    m = load(
        MANIFEST
    )

    assert (
        m[
            "runtime_state"
        ][
            "bayyinat"
        ]
        == "GOVERNED_CONVERSATIONAL_RUNTIME"
    )

    assert (
        m[
            "runtime_state"
        ][
            "adapter"
        ]
        == "IMPLEMENTED"
    )

    assert (
        m[
            "runtime_state"
        ][
            "source_trust_passport"
        ]
        == "ISSUED"
    )


def test_official_coverage_is_governed_runtime():
    c = load(
        COVERAGE
    )

    item = next(
        x
        for x in c[
            "domains"
        ]
        if (
            x[
                "domain"
            ]
            == "shubuhat_faq"
        )
    )

    assert (
        item[
            "status"
        ]
        == "governed_runtime"
    )

    assert (
        item[
            "runtime_source"
        ]
        == "BAYYINAT"
    )

    assert (
        item[
            "cross_domain_primary_evidence"
        ]
        is False
    )
