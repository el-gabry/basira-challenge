import pytest
from pydantic import ValidationError

from basira.models.source_manifest import (
    HashAlgorithm,
    IntegrityStatus,
    SourceDomain,
    SourceHash,
    SourceManifest,
    SourceRole,
    SourceStatus,
)


def build_manifest(**overrides) -> SourceManifest:
    data = {
        "source_id": "kfgqpc-hafs",
        "source_name": "King Fahd Quran Complex - Hafs",
        "domain": SourceDomain.QURAN,
        "role": SourceRole.PRIMARY_CANONICAL,
        "narration": "hafs",
        "language_codes": ["ar"],
        "official_hash": SourceHash(
            algorithm=HashAlgorithm.SHA1,
            value="a" * 40,
        ),
        "local_sha256": "b" * 64,
        "integrity_status": IntegrityStatus.VERIFIED,
        "status": SourceStatus.APPROVED,
        "local_storage_allowed": True,
    }

    data.update(overrides)

    return SourceManifest(**data)


def test_manifest_can_be_runtime_approved() -> None:
    manifest = build_manifest()

    assert manifest.is_runtime_approved is True


def test_pending_manifest_is_not_runtime_approved() -> None:
    manifest = build_manifest(
        status=SourceStatus.PENDING,
    )

    assert manifest.is_runtime_approved is False


def test_integrity_mismatch_blocks_runtime_approval() -> None:
    manifest = build_manifest(
        integrity_status=IntegrityStatus.MISMATCH,
    )

    assert manifest.is_runtime_approved is False


def test_language_codes_are_normalized_and_deduplicated() -> None:
    manifest = build_manifest(
        language_codes=[
            "AR",
            "ar",
            "en_US",
            " EN-us ",
        ]
    )

    assert manifest.language_codes == [
        "ar",
        "en-us",
    ]


def test_required_text_is_normalized() -> None:
    manifest = build_manifest(
        source_id="  kfgqpc-hafs  ",
        source_name="  King   Fahd   Quran   Complex  ",
    )

    assert manifest.source_id == "kfgqpc-hafs"
    assert manifest.source_name == "King Fahd Quran Complex"


def test_blank_source_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        build_manifest(
            source_id="   ",
        )


def test_sha256_must_have_64_characters() -> None:
    with pytest.raises(ValidationError):
        build_manifest(
            local_sha256="abc123",
        )


def test_sha256_must_be_hexadecimal() -> None:
    with pytest.raises(ValidationError):
        build_manifest(
            local_sha256="z" * 64,
        )


def test_source_hash_rejects_non_hexadecimal_value() -> None:
    with pytest.raises(ValidationError):
        SourceHash(
            algorithm=HashAlgorithm.SHA256,
            value="not-a-valid-hash",
        )


def test_raw_file_size_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        build_manifest(
            raw_file_size_bytes=-1,
        )