from __future__ import annotations

import pytest
from pydantic import ValidationError

from basira.models.source_snapshot import (
    SnapshotIntegrityStatus,
    SourceArtifact,
    SourceSnapshot,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def artifact(
    *,
    config: str = "bukhari-ar",
    path: str = (
        "bukhari-ar/"
        "train-00000-of-00001.parquet"
    ),
    sha256: str = HASH_A,
    rows: int = 7580,
    size: int = 100,
) -> SourceArtifact:
    return SourceArtifact(
        config=config,
        path=path,
        sha256=sha256,
        size_bytes=size,
        row_count=rows,
    )


def test_source_artifact_accepts_relative_path() -> None:
    item = artifact()

    assert item.config == "bukhari-ar"
    assert item.row_count == 7580


def test_source_artifact_rejects_absolute_path() -> None:
    with pytest.raises(
        ValidationError,
        match="must be relative",
    ):
        artifact(
            path="/tmp/data.parquet"
        )


def test_source_artifact_rejects_parent_escape() -> None:
    with pytest.raises(
        ValidationError,
        match="must not escape",
    ):
        artifact(
            path="../data.parquet"
        )


def test_source_artifact_rejects_invalid_sha256() -> None:
    with pytest.raises(
        ValidationError,
        match="64 hexadecimal",
    ):
        artifact(
            sha256="not-a-hash"
        )


def test_source_snapshot_reports_totals() -> None:
    snapshot = SourceSnapshot(
        source_id="quranlab-hadith",
        repository="quranlab/hadith",
        revision="abc123",
        integrity_status=(
            SnapshotIntegrityStatus
            .VERIFIED_LOCAL_COPY
        ),
        snapshot_manifest_sha256=HASH_C,
        artifacts=(
            artifact(),
            artifact(
                config="muslim-ar",
                path=(
                    "muslim-ar/"
                    "train-00000-of-00001.parquet"
                ),
                sha256=HASH_B,
                rows=7360,
                size=200,
            ),
        ),
    )

    assert snapshot.artifact_count == 2
    assert snapshot.config_count == 2
    assert snapshot.total_rows == 14940
    assert snapshot.total_size_bytes == 300

    assert snapshot.config_names == (
        "bukhari-ar",
        "muslim-ar",
    )


def test_source_snapshot_rejects_duplicate_paths() -> None:
    first = artifact()

    second = artifact(
        config="another-config",
        sha256=HASH_B,
    )

    with pytest.raises(
        ValidationError,
        match="paths must be unique",
    ):
        SourceSnapshot(
            source_id="quranlab-hadith",
            repository="quranlab/hadith",
            revision="abc123",
            artifacts=(
                first,
                second,
            ),
        )


def test_artifacts_for_config() -> None:
    first = artifact()

    second = artifact(
        config="bukhari-ar",
        path=(
            "bukhari-ar/"
            "train-00001-of-00002.parquet"
        ),
        sha256=HASH_B,
        rows=10,
    )

    snapshot = SourceSnapshot(
        source_id="quranlab-hadith",
        repository="quranlab/hadith",
        revision="abc123",
        artifacts=(
            first,
            second,
        ),
    )

    assert len(
        snapshot.artifacts_for_config(
            "bukhari-ar"
        )
    ) == 2
