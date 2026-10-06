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
    / "jamhara.json"
)


def passport() -> dict:
    return json.loads(
        PASSPORT.read_text(
            encoding="utf-8"
        )
    )


def test_jamhara_live_passport_is_issued() -> None:
    p = passport()

    assert (
        p["runtime_source_id"]
        == "jamhara-live-v1"
    )

    assert (
        p["runtime_admission"]
        == "GOVERNED_TERMINOLOGY_RUNTIME"
    )

    assert (
        p["authority_role"]
        == "PRIMARY_TERMINOLOGY_SOURCE"
    )


def test_jamhara_official_origin_is_pinned() -> None:
    p = passport()

    assert (
        p["official_origin"]
        == "https://islamic-content.com"
    )

    assert (
        p["route_template"]
        == (
            "https://islamic-content.com/"
            "dictionary/word/"
            "{word_id}/{language}"
        )
    )

    delivery = p[
        "runtime_delivery"
    ]

    assert (
        delivery[
            "official_origin_is_trust_anchor"
        ]
        is True
    )

    assert (
        delivery[
            "cache_is_trust_anchor"
        ]
        is False
    )

    assert (
        delivery[
            "cross_origin_redirects_allowed"
        ]
        is False
    )


def test_jamhara_authority_is_terminology_only() -> None:
    boundary = passport()[
        "authority_boundary"
    ]

    assert (
        boundary[
            "terminology_authority"
        ]
        is True
    )

    assert (
        boundary[
            "universal_primary_evidence"
        ]
        is False
    )

    assert (
        boundary[
            "cross_domain_primary_evidence"
        ]
        is False
    )


def test_machine_translation_cannot_replace_governed_term() -> None:
    policy = passport()[
        "translation_policy"
    ]

    assert (
        policy[
            "approved_terminology_precedes_machine_translation"
        ]
        is True
    )

    assert (
        policy[
            "machine_translation_may_replace_governed_term"
        ]
        is False
    )

    assert (
        policy[
            "unavailable_sensitive_term_may_be_silently_machine_translated"
        ]
        is False
    )


def test_live_admission_does_not_fake_snapshot_completion() -> None:
    snapshot = passport()[
        "snapshot_policy"
    ]

    assert (
        snapshot[
            "required_for_runtime"
        ]
        is False
    )

    assert (
        snapshot[
            "live_runtime_may_claim_snapshot_complete"
        ]
        is False
    )

    assert (
        snapshot[
            "background_snapshot_state"
        ]
        == "OPTIONAL_HARDENING_IN_PROGRESS"
    )
