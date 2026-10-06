from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from basira.models.source_snapshot import (
    SourceArtifact,
    SourceSnapshot,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ArtifactValidationResult:
    artifact: SourceArtifact
    exists: bool
    size_matches: bool
    sha256_matches: bool

    @property
    def valid(self) -> bool:
        return (
            self.exists
            and self.size_matches
            and self.sha256_matches
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SnapshotValidationReport:
    source_id: str
    revision: str
    artifacts: tuple[
        ArtifactValidationResult,
        ...,
    ]

    @property
    def valid(self) -> bool:
        return all(
            result.valid
            for result in self.artifacts
        )

    @property
    def artifact_count(self) -> int:
        return len(self.artifacts)

    @property
    def failed_artifacts(
        self,
    ) -> tuple[
        ArtifactValidationResult,
        ...,
    ]:
        return tuple(
            result
            for result in self.artifacts
            if not result.valid
        )


def _sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def validate_source_snapshot(
    snapshot: SourceSnapshot,
    *,
    snapshot_root: Path,
) -> SnapshotValidationReport:
    root = snapshot_root.resolve()

    results: list[
        ArtifactValidationResult
    ] = []

    for artifact in snapshot.artifacts:
        path = (
            snapshot_root
            / artifact.path
        ).resolve()

        try:
            path.relative_to(root)
        except ValueError:
            results.append(
                ArtifactValidationResult(
                    artifact=artifact,
                    exists=False,
                    size_matches=False,
                    sha256_matches=False,
                )
            )
            continue

        if not path.is_file():
            results.append(
                ArtifactValidationResult(
                    artifact=artifact,
                    exists=False,
                    size_matches=False,
                    sha256_matches=False,
                )
            )
            continue

        size_matches = (
            path.stat().st_size
            == artifact.size_bytes
        )

        sha256_matches = (
            _sha256_file(path)
            == artifact.sha256
        )

        results.append(
            ArtifactValidationResult(
                artifact=artifact,
                exists=True,
                size_matches=size_matches,
                sha256_matches=(
                    sha256_matches
                ),
            )
        )

    return SnapshotValidationReport(
        source_id=snapshot.source_id,
        revision=snapshot.revision,
        artifacts=tuple(results),
    )
