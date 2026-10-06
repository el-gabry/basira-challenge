from __future__ import annotations

import json
from pathlib import Path

from basira.competition.bayyinat_admission import (
    SOURCE_ID,
    load_bayyinat_runtime_state,
)
from basira.competition.shubuhat_policy import (
    ShubuhatSourceEligibility,
    _bayyinat_runtime_ready,
)

ROOT = Path(
    __file__
).resolve().parents[3]

RUNTIME_MANIFEST = (
    ROOT
    / "data"
    / "competition"
    / "manifests"
    / "shubuhat"
    / "bayyinat-runtime-v1.json"
)

REGISTRY = (
    ROOT
    / "data"
    / "competition"
    / "sources"
    / "shubuhat"
    / "shubuhat_source_registry.json"
)

COVERAGE = (
    ROOT
    / "data"
    / "competition"
    / "coverage"
    / "official-domain-coverage-v1.json"
)


def load(
    path: Path,
) -> dict:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def test_bayyinat_runtime_manifest_is_eligible():
    manifest = load(
        RUNTIME_MANIFEST
    )

    assert (
        manifest["source_id"]
        == SOURCE_ID
    )

    assert (
        manifest[
            "runtime_eligibility"
        ]
        == "eligible"
    )

    assert (
        manifest[
            "passport_id"
        ]
        == "bayyinat-official-v1"
    )


def test_bayyinat_registry_matches_runtime_manifest():
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
        source[
            "runtime_eligibility"
        ]
        == "eligible"
    )

    assert (
        source[
            "source_family"
        ]
        == "bayyinat"
    )


def test_runtime_admission_builds_policy_ready_state():
    state = (
        load_bayyinat_runtime_state()
    )

    assert (
        state.eligibility
        is ShubuhatSourceEligibility
        .ELIGIBLE
    )

    assert (
        state.exact_artifact_governed
        is True
    )

    assert (
        state.source_identity_verified
        is True
    )

    assert (
        _bayyinat_runtime_ready(
            state
        )
        is True
    )


def test_coverage_names_exact_admitted_source():
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
            == "shubuhat_faq"
        )
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
        item["status"]
        == "governed_runtime"
    )



def test_runtime_manifest_registry_and_passport_agree():
    passport = load(
        ROOT
        / "data"
        / "competition"
        / "passports"
        / "bayyinat.json"
    )

    manifest = load(
        RUNTIME_MANIFEST
    )

    registry = load(
        REGISTRY
    )

    source = next(
        item
        for item in registry["sources"]
        if item["source_id"] == SOURCE_ID
    )

    assert (
        manifest["artifact_sha256"]
        == passport["artifact"]["sha256"]
        == source["artifact_sha256"]
    )

    assert (
        manifest["snapshot_sha256"]
        == passport[
            "canonical_units"
        ]["snapshot_sha256"]
        == source["snapshot_sha256"]
    )

    assert (
        manifest["snapshot_path"]
        == passport[
            "canonical_units"
        ]["snapshot_path"]
        == source["snapshot_path"]
    )

    assert (
        manifest["runtime_role"]
        == source["authority_role"]
        == "PRIMARY_CONVERSATIONAL_SOURCE"
    )

    assert (
        manifest["source_family"]
        == source["source_family"]
        == "bayyinat"
    )
