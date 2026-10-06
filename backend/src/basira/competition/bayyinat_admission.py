from __future__ import annotations

import hashlib
import json
from pathlib import Path

from basira.competition.shubuhat_policy import (
    BayyinatSourceState,
    ShubuhatSourceEligibility,
)

ROOT = Path(
    __file__
).resolve().parents[3]

SOURCE_ID = "bayyinat-v1"

PASSPORT = (
    ROOT
    / "data"
    / "competition"
    / "passports"
    / "bayyinat.json"
)

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


def _load_json(
    path: Path,
) -> dict:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise RuntimeError(
            f"expected object: {path}"
        )

    return value


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def load_bayyinat_runtime_state(
) -> BayyinatSourceState:
    """
    Validate the admitted Bayyinat runtime chain and
    return the exact state accepted by Shubuhat policy.

    The source remains conversational only. This
    function does not grant cross-domain evidentiary
    authority.
    """

    passport = _load_json(
        PASSPORT
    )

    runtime = _load_json(
        RUNTIME_MANIFEST
    )

    registry = _load_json(
        REGISTRY
    )

    if (
        runtime.get("source_id")
        != SOURCE_ID
    ):
        raise RuntimeError(
            "unexpected Bayyinat runtime source id"
        )

    if (
        runtime.get(
            "runtime_eligibility"
        )
        != "eligible"
    ):
        raise RuntimeError(
            "Bayyinat runtime is not eligible"
        )

    if (
        runtime.get("passport_id")
        != passport.get("passport_id")
    ):
        raise RuntimeError(
            "Bayyinat passport mismatch"
        )

    if (
        runtime.get("source_family")
        != "bayyinat"
    ):
        raise RuntimeError(
            "unexpected Bayyinat source family"
        )

    if (
        runtime.get("runtime_role")
        != "PRIMARY_CONVERSATIONAL_SOURCE"
    ):
        raise RuntimeError(
            "unexpected Bayyinat runtime role"
        )

    if (
        runtime.get("adapter")
        != "src/basira/competition/bayyinat.py"
    ):
        raise RuntimeError(
            "unexpected Bayyinat adapter"
        )

    if (
        runtime.get("admission")
        != (
            "src/basira/competition/"
            "bayyinat_admission.py"
        )
    ):
        raise RuntimeError(
            "unexpected Bayyinat admission bridge"
        )

    if (
        passport.get(
            "runtime_source_id"
        )
        != SOURCE_ID
    ):
        raise RuntimeError(
            "Bayyinat passport source id mismatch"
        )

    if (
        passport.get(
            "runtime_admission"
        )
        != "GOVERNED_CONVERSATIONAL_RUNTIME"
    ):
        raise RuntimeError(
            "Bayyinat passport is not "
            "runtime admitted"
        )

    canonical = passport.get(
        "canonical_units",
        {},
    )

    snapshot_relative = runtime.get(
        "snapshot_path"
    )

    if (
        snapshot_relative
        != canonical.get(
            "snapshot_path"
        )
    ):
        raise RuntimeError(
            "Bayyinat snapshot path mismatch"
        )

    snapshot = (
        ROOT
        / snapshot_relative
    )

    expected_snapshot_sha256 = (
        runtime.get(
            "snapshot_sha256"
        )
    )

    if (
        expected_snapshot_sha256
        != canonical.get(
            "snapshot_sha256"
        )
    ):
        raise RuntimeError(
            "Bayyinat snapshot hash contract "
            "mismatch"
        )

    if (
        _sha256(snapshot)
        != expected_snapshot_sha256
    ):
        raise RuntimeError(
            "Bayyinat frozen snapshot hash "
            "mismatch"
        )

    snapshot_data = _load_json(
        snapshot
    )

    passport_artifact = passport.get(
        "artifact",
        {}
    )

    snapshot_artifact = snapshot_data.get(
        "artifact",
        {}
    )

    if (
        runtime.get("artifact_sha256")
        != passport_artifact.get("sha256")
    ):
        raise RuntimeError(
            "Bayyinat runtime artifact hash "
            "mismatch"
        )

    if (
        passport_artifact.get("sha256")
        != snapshot_artifact.get("sha256")
    ):
        raise RuntimeError(
            "Bayyinat exact artifact identity "
            "mismatch"
        )

    if (
        passport.get(
            "official_locator"
        )
        != snapshot_data.get(
            "official_locator"
        )
    ):
        raise RuntimeError(
            "Bayyinat official source identity "
            "mismatch"
        )

    sources = registry.get(
        "sources",
        [],
    )

    matches = [
        source
        for source in sources
        if (
            source.get("source_id")
            == SOURCE_ID
        )
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "Bayyinat registry admission missing "
            "or ambiguous"
        )

    source = matches[0]

    if (
        source.get("source_family")
        != "bayyinat"
    ):
        raise RuntimeError(
            "Bayyinat registry source family "
            "mismatch"
        )

    if (
        source.get("authority_role")
        != "PRIMARY_CONVERSATIONAL_SOURCE"
    ):
        raise RuntimeError(
            "Bayyinat registry authority role "
            "mismatch"
        )

    if (
        source.get("artifact_sha256")
        != passport_artifact.get("sha256")
    ):
        raise RuntimeError(
            "Bayyinat registry artifact hash "
            "mismatch"
        )

    if (
        source.get("snapshot_path")
        != snapshot_relative
    ):
        raise RuntimeError(
            "Bayyinat registry snapshot path "
            "mismatch"
        )

    if (
        source.get("runtime_manifest")
        != (
            "data/competition/manifests/"
            "shubuhat/"
            "bayyinat-runtime-v1.json"
        )
    ):
        raise RuntimeError(
            "Bayyinat registry runtime manifest "
            "mismatch"
        )

    if (
        source.get(
            "runtime_eligibility"
        )
        != "eligible"
    ):
        raise RuntimeError(
            "Bayyinat registry source "
            "not runtime eligible"
        )

    if (
        source.get("passport_id")
        != passport.get("passport_id")
    ):
        raise RuntimeError(
            "Bayyinat registry passport mismatch"
        )

    if (
        source.get(
            "snapshot_sha256"
        )
        != expected_snapshot_sha256
    ):
        raise RuntimeError(
            "Bayyinat registry snapshot "
            "hash mismatch"
        )

    return BayyinatSourceState(
        eligibility=(
            ShubuhatSourceEligibility
            .ELIGIBLE
        ),
        exact_artifact_governed=True,
        source_identity_verified=True,
    )
