from __future__ import annotations

import hashlib
import shutil
from datetime import UTC, datetime
from pathlib import Path

from basira.models.source_manifest import (
    HashAlgorithm,
    IntegrityStatus,
    SourceDomain,
    SourceHash,
    SourceManifest,
    SourceRole,
    SourceStatus,
)

KFGQPC_HAFS_SOURCE_ID = "kfgqpc-hafs-uthmanic"
KFGQPC_HAFS_MIRROR_SOURCE_ID = "kfgqpc-hafs-mirror-v18"
KFGQPC_HAFS_VERSION = "13.0"

KFGQPC_HAFS_OFFICIAL_SHA1 = (
    "36ea5ab0d7ea1702f17ff43f9b50924cccd77ebf"
)

KFGQPC_HOMEPAGE = (
    "https://qurancomplex.gov.sa/en/techquran/dev/"
)


class KfgqpcIntegrityError(ValueError):
    """Raised when a KFGQPC package fails integrity verification."""


def calculate_file_hash(
    path: Path,
    algorithm: str,
    chunk_size: int = 1024 * 1024,
) -> str:
    """
    Calculate a cryptographic digest without loading the entire file
    into memory.
    """

    digest = hashlib.new(algorithm)

    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)

    return digest.hexdigest()


def verify_kfgqpc_hafs_package(
    source_file: Path,
) -> str:
    """
    Verify the downloaded Hafs package against KFGQPC's published SHA-1.

    Returns the calculated SHA-1 when verification succeeds.
    """

    if not source_file.exists():
        raise FileNotFoundError(
            f"KFGQPC package does not exist: {source_file}"
        )

    if not source_file.is_file():
        raise ValueError(
            f"KFGQPC package path is not a file: {source_file}"
        )

    calculated_sha1 = calculate_file_hash(
        source_file,
        "sha1",
    )

    if calculated_sha1 != KFGQPC_HAFS_OFFICIAL_SHA1:
        raise KfgqpcIntegrityError(
            "KFGQPC Hafs package SHA-1 mismatch. "
            f"Expected {KFGQPC_HAFS_OFFICIAL_SHA1}, "
            f"received {calculated_sha1}."
        )

    return calculated_sha1


def acquire_kfgqpc_hafs_package(
    source_file: Path,
    raw_directory: Path,
) -> SourceManifest:
    """
    Verify and preserve an immutable raw KFGQPC Hafs snapshot.

    The source package is never modified. A verified copy is placed in
    Basira's raw-data area and a provenance manifest is returned.
    """

    official_sha1 = verify_kfgqpc_hafs_package(
        source_file
    )

    raw_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        raw_directory
        / source_file.name
    )

    if destination.exists():
        existing_sha256 = calculate_file_hash(
            destination,
            "sha256",
        )

        source_sha256 = calculate_file_hash(
            source_file,
            "sha256",
        )

        if existing_sha256 != source_sha256:
            raise KfgqpcIntegrityError(
                "A different raw snapshot already exists at "
                f"{destination}. Refusing to overwrite it."
            )
    else:
        shutil.copy2(
            source_file,
            destination,
        )

    local_sha256 = calculate_file_hash(
        destination,
        "sha256",
    )

    return SourceManifest(
        source_id=KFGQPC_HAFS_SOURCE_ID,
        source_name=(
            "King Fahd Glorious Quran Printing Complex "
            "- Unicode Uthmanic Hafs"
        ),
        domain=SourceDomain.QURAN,
        role=SourceRole.PRIMARY_CANONICAL,
        narration="hafs",
        language_codes=["ar"],
        version=KFGQPC_HAFS_VERSION,
        publisher=(
            "King Fahd Glorious Quran Printing Complex"
        ),
        homepage_url=KFGQPC_HOMEPAGE,
        downloaded_at=datetime.now(UTC),
        official_hash=SourceHash(
            algorithm=HashAlgorithm.SHA1,
            value=official_sha1,
        ),
        local_sha256=local_sha256,
        integrity_status=IntegrityStatus.VERIFIED,
        status=SourceStatus.VERIFIED,
        local_storage_allowed=True,
        redistribution_allowed=False,
        attribution_required=True,
        raw_file_name=destination.name,
        raw_file_size_bytes=destination.stat().st_size,
        notes=(
            "KFGQPC Unicode Uthmanic Hafs developer package. "
            "Official release version 13.0."
        ),
    )