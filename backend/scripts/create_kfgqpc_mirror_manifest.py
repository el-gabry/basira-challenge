from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from basira.models.source_manifest import (
    IntegrityStatus,
    SourceDomain,
    SourceManifest,
    SourceRole,
    SourceStatus,
)
from basira.sources.quran.kfgqpc import (
    KFGQPC_HAFS_MIRROR_SOURCE_ID,
    calculate_file_hash,
)

DATASET = Path(
    "/mnt/c/Users/_/Downloads/"
    "kfgqpc-mirror/hafs/data/hafsData_v18.json"
)

OUTPUT = Path(
    "data/manifests/quran/"
    "kfgqpc-hafs-mirror-v18.json"
)


def main() -> None:
    if not DATASET.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET}"
        )

    sha256 = calculate_file_hash(
        DATASET,
        "sha256",
    )

    manifest = SourceManifest(
        source_id=KFGQPC_HAFS_MIRROR_SOURCE_ID,
        source_name=(
            "KFGQPC Hafs Data v18 "
            "- GitHub Development Mirror"
        ),
        domain=SourceDomain.QURAN,
        role=SourceRole.SECONDARY_REFERENCE,
        narration="hafs",
        language_codes=["ar"],
        version="18",
        publisher=(
            "Third-party GitHub mirror of "
            "King Fahd Quran Complex developer data"
        ),
        homepage_url=(
            "https://github.com/ibnhazm/KFGQPC"
        ),
        downloaded_at=datetime.now(UTC),
        local_sha256=sha256,
        integrity_status=(
            IntegrityStatus.REVIEW_REQUIRED
        ),
        status=SourceStatus.QUARANTINED,
        local_storage_allowed=True,
        redistribution_allowed=False,
        attribution_required=True,
        raw_file_name=DATASET.name,
        raw_file_size_bytes=(
            DATASET.stat().st_size
        ),
        notes=(
            "Development-only Quran corpus. "
            "The upstream official KFGQPC service was "
            "unreachable when this snapshot was acquired. "
            "This mirror must not be promoted to APPROVED "
            "until independently compared with an official "
            "KFGQPC release."
        ),
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            manifest.model_dump(
                mode="json"
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("KFGQPC mirror manifest: CREATED")
    print("Dataset:", DATASET)
    print("SHA-256:", sha256)
    print("Status:", manifest.status)
    print(
        "Integrity:",
        manifest.integrity_status,
    )
    print(
        "Runtime approved:",
        manifest.is_runtime_approved,
    )
    print("Manifest:", OUTPUT)


if __name__ == "__main__":
    main()