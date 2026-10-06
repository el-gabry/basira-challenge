import pytest

from basira.models.source_manifest import (
    IntegrityStatus,
    SourceDomain,
    SourceManifest,
    SourceRole,
    SourceStatus,
)
from basira.sources.registry import (
    DuplicateSourceError,
    SourceNotFoundError,
    TrustedSourceRegistry,
)


def build_manifest(
    source_id: str = "kfgqpc-hafs",
    domain: SourceDomain = SourceDomain.QURAN,
    status: SourceStatus = SourceStatus.APPROVED,
    integrity_status: IntegrityStatus = IntegrityStatus.VERIFIED,
) -> SourceManifest:
    return SourceManifest(
        source_id=source_id,
        source_name=source_id,
        domain=domain,
        role=SourceRole.PRIMARY_CANONICAL,
        narration="hafs",
        language_codes=["ar"],
        local_sha256="a" * 64,
        integrity_status=integrity_status,
        status=status,
        local_storage_allowed=True,
    )


def test_register_and_get_source() -> None:
    registry = TrustedSourceRegistry()

    manifest = build_manifest()

    registry.register(manifest)

    assert registry.get("kfgqpc-hafs") == manifest
    assert len(registry) == 1


def test_unknown_source_returns_none() -> None:
    registry = TrustedSourceRegistry()

    assert registry.get("unknown-source") is None


def test_require_returns_registered_source() -> None:
    manifest = build_manifest()

    registry = TrustedSourceRegistry(
        manifests=[manifest],
    )

    assert registry.require("kfgqpc-hafs") == manifest


def test_require_raises_for_unknown_source() -> None:
    registry = TrustedSourceRegistry()

    with pytest.raises(SourceNotFoundError):
        registry.require("unknown-source")


def test_duplicate_source_is_rejected() -> None:
    manifest = build_manifest()

    registry = TrustedSourceRegistry(
        manifests=[manifest],
    )

    with pytest.raises(DuplicateSourceError):
        registry.register(manifest)


def test_approved_verified_source_is_runtime_approved() -> None:
    manifest = build_manifest()

    registry = TrustedSourceRegistry(
        manifests=[manifest],
    )

    assert registry.is_runtime_approved("kfgqpc-hafs") is True


def test_pending_source_is_not_runtime_approved() -> None:
    manifest = build_manifest(
        status=SourceStatus.PENDING,
    )

    registry = TrustedSourceRegistry(
        manifests=[manifest],
    )

    assert registry.is_runtime_approved("kfgqpc-hafs") is False


def test_quarantined_source_is_not_runtime_approved() -> None:
    manifest = build_manifest(
        status=SourceStatus.QUARANTINED,
    )

    registry = TrustedSourceRegistry(
        manifests=[manifest],
    )

    assert registry.is_runtime_approved("kfgqpc-hafs") is False


def test_integrity_mismatch_blocks_runtime_approval() -> None:
    manifest = build_manifest(
        integrity_status=IntegrityStatus.MISMATCH,
    )

    registry = TrustedSourceRegistry(
        manifests=[manifest],
    )

    assert registry.is_runtime_approved("kfgqpc-hafs") is False


def test_runtime_approved_returns_only_allowed_sources() -> None:
    approved = build_manifest(
        source_id="kfgqpc-hafs",
    )

    pending = build_manifest(
        source_id="tanzil-pending",
        status=SourceStatus.PENDING,
    )

    mismatch = build_manifest(
        source_id="corrupted-source",
        integrity_status=IntegrityStatus.MISMATCH,
    )

    registry = TrustedSourceRegistry(
        manifests=[
            approved,
            pending,
            mismatch,
        ]
    )

    assert registry.runtime_approved() == (
        approved,
    )


def test_runtime_approved_for_domain_filters_sources() -> None:
    quran = build_manifest(
        source_id="kfgqpc-hafs",
        domain=SourceDomain.QURAN,
    )

    hadith = build_manifest(
        source_id="hadith-source",
        domain=SourceDomain.HADITH,
    )

    registry = TrustedSourceRegistry(
        manifests=[
            quran,
            hadith,
        ]
    )

    assert registry.runtime_approved_for_domain(
        SourceDomain.QURAN
    ) == (quran,)


def test_unknown_source_is_not_runtime_approved() -> None:
    registry = TrustedSourceRegistry()

    assert registry.is_runtime_approved(
        "unknown-source"
    ) is False


def test_all_returns_all_registered_sources() -> None:
    first = build_manifest(
        source_id="source-one",
    )

    second = build_manifest(
        source_id="source-two",
    )

    registry = TrustedSourceRegistry(
        manifests=[
            first,
            second,
        ]
    )

    assert registry.all() == (
        first,
        second,
    )