from __future__ import annotations

import json
from pathlib import Path

from basira.competition.jamhara_admission import (
    SOURCE_ID,
    load_jamhara_runtime_state,
)

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

MANIFEST = (
    ROOT
    / "data"
    / "competition"
    / "manifests"
    / "terminology"
    / "jamhara-runtime-v1.json"
)

REGISTRY = (
    ROOT
    / "data"
    / "competition"
    / "sources"
    / "terminology"
    / "terminology_source_registry.json"
)

COVERAGE = (
    ROOT
    / "data"
    / "competition"
    / "coverage"
    / "official-domain-coverage-v1.json"
)

SNAPSHOT_CONTRACT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "jamhara"
    / "snapshot-contract.json"
)


def load(
    path: Path,
) -> dict:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def test_jamhara_runtime_chain_is_ready() -> None:
    state = (
        load_jamhara_runtime_state()
    )

    assert (
        state.source_id
        == SOURCE_ID
    )

    assert state.eligible is True

    assert (
        state.source_identity_verified
        is True
    )

    assert (
        state.implementation_governed
        is True
    )

    assert (
        state.terminology_only
        is True
    )

    assert (
        state.cross_domain_primary_evidence
        is False
    )

    assert (
        state.machine_translation_may_replace_governed_term
        is False
    )

    assert (
        state.snapshot_required
        is False
    )

    assert state.ready is True


def test_manifest_registry_and_passport_agree() -> None:
    passport = load(
        PASSPORT
    )

    manifest = load(
        MANIFEST
    )

    registry = load(
        REGISTRY
    )

    source = next(
        item
        for item in registry[
            "sources"
        ]
        if (
            item["source_id"]
            == SOURCE_ID
        )
    )

    assert (
        manifest["passport_id"]
        == passport["passport_id"]
        == source["passport_id"]
    )

    assert (
        manifest["source_family"]
        == passport["source_family"]
        == source["source_family"]
        == "AL_JAMHARA_ISLAMIC_TERMINOLOGY"
    )

    assert (
        manifest["runtime_role"]
        == passport["authority_role"]
        == source["authority_role"]
        == "PRIMARY_TERMINOLOGY_SOURCE"
    )

    assert (
        manifest[
            "implementation_integrity"
        ]
        == passport[
            "implementation_integrity"
        ]
        == source[
            "implementation_integrity"
        ]
    )

    assert (
        manifest[
            "policy_integrity"
        ]
        == passport[
            "policy_integrity"
        ]
        == source[
            "policy_integrity"
        ]
    )


def test_translation_coverage_names_admitted_live_source() -> None:
    coverage = load(
        COVERAGE
    )

    item = next(
        domain
        for domain in coverage[
            "domains"
        ]
        if (
            domain["domain"]
            == "translation_terminology"
        )
    )

    assert (
        item["status"]
        == "governed_runtime"
    )

    assert (
        item[
            "runtime_source_ids"
        ]
        == [
            SOURCE_ID
        ]
    )

    assert (
        item["runtime_source"]
        == "AL_JAMHARA_ISLAMIC_TERMINOLOGY"
    )

    assert (
        item[
            "cross_domain_primary_evidence"
        ]
        is False
    )

    assert (
        item[
            "machine_translation_may_replace_governed_term"
        ]
        is False
    )

    assert (
        item[
            "snapshot_required_for_runtime"
        ]
        is False
    )


def test_live_admission_and_snapshot_state_are_distinct() -> None:
    snapshot = load(
        SNAPSHOT_CONTRACT
    )

    # Historical/future frozen-snapshot admission
    # remains unfinished. That does not invalidate
    # the separately governed official live runtime.
    assert (
        snapshot["build_state"]
        == "NOT_BUILT"
    )

    assert (
        snapshot[
            "runtime_admission"
        ]
        == "PENDING_AUDIT"
    )

    state = (
        load_jamhara_runtime_state()
    )

    assert state.ready is True
    assert (
        state.snapshot_required
        is False
    )
