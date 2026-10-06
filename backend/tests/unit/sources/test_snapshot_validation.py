from __future__ import annotations

import hashlib
from pathlib import Path

from basira.models.source_snapshot import (
    SnapshotIntegrityStatus,
    SourceArtifact,
    SourceSnapshot,
)
from basira.sources.snapshot_validation import (
    validate_source_snapshot,
)


def sha256(
    data: bytes,
) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def snapshot_for(
    *,
    path: str,
    content: bytes,
) -> SourceSnapshot:
    return SourceSnapshot(
        source_id="test-source",
        repository="test/repo",
        revision="abc123",
        integrity_status=(
            SnapshotIntegrityStatus
            .VERIFIED_LOCAL_COPY
        ),
        artifacts=(
            SourceArtifact(
                config="test-config",
                path=path,
                sha256=sha256(
                    content
                ),
                size_bytes=len(
                    content
                ),
                row_count=1,
            ),
        ),
    )


def test_valid_snapshot_artifact(
    tmp_path: Path,
) -> None:
    content = b"trusted artifact"

    artifact_path = (
        tmp_path
        / "data"
        / "artifact.bin"
    )

    artifact_path.parent.mkdir()

    artifact_path.write_bytes(
        content
    )

    snapshot = snapshot_for(
        path="data/artifact.bin",
        content=content,
    )

    report = validate_source_snapshot(
        snapshot,
        snapshot_root=tmp_path,
    )

    assert report.valid
    assert report.artifact_count == 1
    assert report.failed_artifacts == ()


def test_missing_artifact_fails(
    tmp_path: Path,
) -> None:
    snapshot = snapshot_for(
        path="missing.bin",
        content=b"expected",
    )

    report = validate_source_snapshot(
        snapshot,
        snapshot_root=tmp_path,
    )

    assert not report.valid

    result = report.failed_artifacts[0]

    assert not result.exists
    assert not result.size_matches
    assert not result.sha256_matches


def test_modified_artifact_fails_hash(
    tmp_path: Path,
) -> None:
    expected = b"original"

    path = tmp_path / "artifact.bin"

    path.write_bytes(
        b"modified"
    )

    snapshot = snapshot_for(
        path="artifact.bin",
        content=expected,
    )

    report = validate_source_snapshot(
        snapshot,
        snapshot_root=tmp_path,
    )

    assert not report.valid

    result = report.failed_artifacts[0]

    assert result.exists
    assert result.size_matches
    assert not result.sha256_matches


def test_changed_size_fails(
    tmp_path: Path,
) -> None:
    expected = b"original"

    path = tmp_path / "artifact.bin"

    path.write_bytes(
        b"different-size"
    )

    snapshot = snapshot_for(
        path="artifact.bin",
        content=expected,
    )

    report = validate_source_snapshot(
        snapshot,
        snapshot_root=tmp_path,
    )

    assert not report.valid

    result = report.failed_artifacts[0]

    assert result.exists
    assert not result.size_matches
    assert not result.sha256_matches
