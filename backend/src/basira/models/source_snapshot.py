from __future__ import annotations

import re
from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

_SHA256_RE = re.compile(
    r"^[0-9a-f]{64}$"
)


class SnapshotIntegrityStatus(StrEnum):
    """
    Integrity of a frozen local source snapshot.

    This describes reproducibility of local artifact
    bytes. It does NOT imply religious authority or
    runtime source approval.
    """

    NOT_CHECKED = "not_checked"
    VERIFIED_LOCAL_COPY = "verified_local_copy"
    MISMATCH = "mismatch"


class SourceArtifact(BaseModel):
    """
    One immutable artifact belonging to a source
    snapshot.
    """

    config: str = Field(min_length=1)

    path: str = Field(min_length=1)

    sha256: str

    size_bytes: int = Field(gt=0)

    row_count: int = Field(ge=0)

    @field_validator("config")
    @classmethod
    def normalize_config(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(
            value.split()
        )

        if not normalized:
            raise ValueError(
                "config must not be blank."
            )

        return normalized

    @field_validator("path")
    @classmethod
    def validate_relative_path(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "path must not be blank."
            )

        path = PurePosixPath(
            normalized
        )

        if path.is_absolute():
            raise ValueError(
                "Artifact path must be relative."
            )

        if ".." in path.parts:
            raise ValueError(
                "Artifact path must not escape "
                "the snapshot root."
            )

        return str(path)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(
        cls,
        value: str,
    ) -> str:
        normalized = (
            value
            .strip()
            .lower()
        )

        if not _SHA256_RE.fullmatch(
            normalized
        ):
            raise ValueError(
                "sha256 must contain exactly "
                "64 hexadecimal characters."
            )

        return normalized


class SourceSnapshot(BaseModel):
    """
    Frozen multi-artifact representation of one
    external source revision.

    Snapshot integrity is deliberately separate from
    SourceManifest approval and evidence authority.
    """

    source_id: str = Field(
        min_length=1
    )

    repository: str = Field(
        min_length=1
    )

    revision: str = Field(
        min_length=1
    )

    integrity_status: SnapshotIntegrityStatus = (
        SnapshotIntegrityStatus.NOT_CHECKED
    )

    snapshot_manifest_sha256: (
        str | None
    ) = None

    artifacts: tuple[
        SourceArtifact,
        ...,
    ] = Field(min_length=1)

    @field_validator(
        "source_id",
        "repository",
        "revision",
    )
    @classmethod
    def normalize_identifier(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(
            value.split()
        )

        if not normalized:
            raise ValueError(
                "Identifier must not be blank."
            )

        return normalized

    @field_validator(
        "snapshot_manifest_sha256"
    )
    @classmethod
    def validate_manifest_sha256(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = (
            value
            .strip()
            .lower()
        )

        if not _SHA256_RE.fullmatch(
            normalized
        ):
            raise ValueError(
                "snapshot_manifest_sha256 must "
                "contain exactly 64 hexadecimal "
                "characters."
            )

        return normalized

    @model_validator(mode="after")
    def validate_unique_artifacts(
        self,
    ) -> SourceSnapshot:
        paths = [
            artifact.path
            for artifact in self.artifacts
        ]

        if len(paths) != len(set(paths)):
            raise ValueError(
                "Snapshot artifact paths "
                "must be unique."
            )

        return self

    @property
    def config_names(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    artifact.config
                    for artifact
                    in self.artifacts
                }
            )
        )

    @property
    def config_count(
        self,
    ) -> int:
        return len(
            self.config_names
        )

    @property
    def artifact_count(
        self,
    ) -> int:
        return len(
            self.artifacts
        )

    @property
    def total_rows(
        self,
    ) -> int:
        return sum(
            artifact.row_count
            for artifact
            in self.artifacts
        )

    @property
    def total_size_bytes(
        self,
    ) -> int:
        return sum(
            artifact.size_bytes
            for artifact
            in self.artifacts
        )

    def artifacts_for_config(
        self,
        config: str,
    ) -> tuple[
        SourceArtifact,
        ...,
    ]:
        return tuple(
            artifact
            for artifact
            in self.artifacts
            if artifact.config == config
        )
