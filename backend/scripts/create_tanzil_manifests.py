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
from basira.sources.quran.kfgqpc import calculate_file_hash
from basira.sources.quran.tanzil.parser import TANZIL_SOURCE_ID

BASE = Path(
    "/mnt/c/Users/_/Downloads/tanzil"
)

UTHMANI_FILE = BASE / "quran-uthmani.txt"
SIMPLE_PLAIN_FILE = BASE / "quran-simple-plain.txt"

OUTPUT_DIR = Path(
    "data/manifests/quran"
)

TANZIL_HOMEPAGE = "https://tanzil.net/"

TANZIL_LICENSE_URL = (
    "https://tanzil.net/docs/Text_License"
)


def write_manifest(
    manifest: SourceManifest,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
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


def main() -> None:
    for path in (
        UTHMANI_FILE,
        SIMPLE_PLAIN_FILE,
    ):
        if not path.exists():
            raise FileNotFoundError(
                f"Tanzil file not found: {path}"
            )

    uthmani_sha256 = calculate_file_hash(
        UTHMANI_FILE,
        "sha256",
    )

    simple_plain_sha256 = calculate_file_hash(
        SIMPLE_PLAIN_FILE,
        "sha256",
    )

    downloaded_at = datetime.now(UTC)

    uthmani_manifest = SourceManifest(
        source_id=(
            f"{TANZIL_SOURCE_ID}-uthmani"
        ),
        source_name=(
            "Tanzil Quran Text v1.1 - Uthmani"
        ),
        domain=SourceDomain.QURAN,
        role=SourceRole.INDEPENDENT_VERIFIER,
        narration="hafs",
        language_codes=["ar"],
        version="1.1",
        publisher="Tanzil Project",
        homepage_url=TANZIL_HOMEPAGE,
        downloaded_at=downloaded_at,
        local_sha256=uthmani_sha256,
        integrity_status=(
            IntegrityStatus.REVIEW_REQUIRED
        ),
        status=SourceStatus.VERIFIED,
        license_name="CC BY 3.0",
        license_url=TANZIL_LICENSE_URL,
        local_storage_allowed=True,
        redistribution_allowed=True,
        attribution_required=True,
        raw_file_name=UTHMANI_FILE.name,
        raw_file_size_bytes=(
            UTHMANI_FILE.stat().st_size
        ),
        notes=(
            "Official Tanzil Uthmani Quran text "
            "downloaded directly from Tanzil. "
            "Structurally validated as 6,236 verses. "
            "No upstream cryptographic checksum has "
            "yet been recorded by Basira, so this "
            "snapshot remains non-approved until "
            "cross-source integrity verification."
        ),
    )

    simple_plain_manifest = SourceManifest(
        source_id=(
            f"{TANZIL_SOURCE_ID}-simple-plain"
        ),
        source_name=(
            "Tanzil Quran Text v1.1 "
            "- Simple Plain"
        ),
        domain=SourceDomain.QURAN,
        role=SourceRole.SECONDARY_REFERENCE,
        narration="hafs",
        language_codes=["ar"],
        version="1.1",
        publisher="Tanzil Project",
        homepage_url=TANZIL_HOMEPAGE,
        downloaded_at=downloaded_at,
        local_sha256=simple_plain_sha256,
        integrity_status=(
            IntegrityStatus.REVIEW_REQUIRED
        ),
        status=SourceStatus.VERIFIED,
        license_name="CC BY 3.0",
        license_url=TANZIL_LICENSE_URL,
        local_storage_allowed=True,
        redistribution_allowed=True,
        attribution_required=True,
        raw_file_name=SIMPLE_PLAIN_FILE.name,
        raw_file_size_bytes=(
            SIMPLE_PLAIN_FILE.stat().st_size
        ),
        notes=(
            "Official Tanzil Simple Plain Quran text "
            "used as Basira's search representation. "
            "All 6,236 verses normalize equivalently "
            "to Tanzil Simple under Basira normalization."
        ),
    )

    uthmani_output = (
        OUTPUT_DIR
        / "tanzil-quran-v1.1-uthmani.json"
    )

    simple_plain_output = (
        OUTPUT_DIR
        / "tanzil-quran-v1.1-simple-plain.json"
    )

    write_manifest(
        uthmani_manifest,
        uthmani_output,
    )

    write_manifest(
        simple_plain_manifest,
        simple_plain_output,
    )

    print("Tanzil manifests: CREATED")

    print()
    print("Uthmani")
    print("SHA-256:", uthmani_sha256)
    print(
        "Runtime approved:",
        uthmani_manifest.is_runtime_approved,
    )

    print()
    print("Simple Plain")
    print(
        "SHA-256:",
        simple_plain_sha256,
    )
    print(
        "Runtime approved:",
        simple_plain_manifest.is_runtime_approved,
    )

    print()
    print("Manifest files:")
    print(uthmani_output)
    print(simple_plain_output)


if __name__ == "__main__":
    main()