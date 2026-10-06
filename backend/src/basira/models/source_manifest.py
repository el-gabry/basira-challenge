from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from basira.models.source_usage import RuntimeUse, SourceUsagePolicy


class SourceDomain(StrEnum):
    QURAN = "quran"
    HADITH = "hadith"
    TAFSIR = "tafsir"
    FIQH = "fiqh"
    FATWA = "fatwa"
    GENERAL = "general"


class SourceRole(StrEnum):
    PRIMARY_CANONICAL = "primary_canonical"
    INDEPENDENT_VERIFIER = "independent_verifier"
    AUTHORITATIVE_REFERENCE = "authoritative_reference"
    SECONDARY_REFERENCE = "secondary_reference"


class SourceStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    APPROVED = "approved"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    REVOKED = "revoked"


class HashAlgorithm(StrEnum):
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


class IntegrityStatus(StrEnum):
    NOT_CHECKED = "not_checked"
    VERIFIED = "verified"
    MISMATCH = "mismatch"
    REVIEW_REQUIRED = "review_required"


class SourceHash(BaseModel):
    algorithm: HashAlgorithm
    value: str = Field(min_length=1)

    @field_validator("value")
    @classmethod
    def normalize_hash(cls, value: str) -> str:
        normalized = value.strip().lower()

        if not normalized:
            raise ValueError("Hash value must not be blank.")

        if any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("Hash value must be hexadecimal.")

        return normalized


class SourceManifest(BaseModel):
    """
    Immutable provenance metadata describing an external source snapshot.

    A manifest records where a source came from, which version was acquired,
    how its integrity was checked, and whether Basira has approved it for use.
    """

    source_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)

    domain: SourceDomain
    role: SourceRole

    usage_policy: SourceUsagePolicy | None = None

    narration: str | None = None
    language_codes: list[str] = Field(default_factory=list)

    version: str | None = None
    edition: str | None = None

    publisher: str | None = None

    homepage_url: HttpUrl | None = None
    download_url: HttpUrl | None = None

    downloaded_at: datetime | None = None

    official_hash: SourceHash | None = None
    local_sha256: str | None = None

    integrity_status: IntegrityStatus = IntegrityStatus.NOT_CHECKED
    status: SourceStatus = SourceStatus.PENDING

    license_name: str | None = None
    license_url: HttpUrl | None = None

    local_storage_allowed: bool = False
    redistribution_allowed: bool = False
    attribution_required: bool = True

    raw_file_name: str | None = None
    raw_file_size_bytes: int | None = Field(default=None, ge=0)

    notes: str | None = None

    @field_validator(
        "source_id",
        "source_name",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError("Field must not be blank.")

        return normalized

    @field_validator(
        "narration",
        "version",
        "edition",
        "publisher",
        "license_name",
        "raw_file_name",
        "notes",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = " ".join(value.split())

        return normalized or None

    @field_validator("language_codes")
    @classmethod
    def normalize_languages(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = value.strip().lower().replace("_", "-")

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(normalized)

        return result

    @field_validator("local_sha256")
    @classmethod
    def validate_local_sha256(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()

        if len(normalized) != 64:
            raise ValueError(
                "local_sha256 must contain exactly 64 hexadecimal characters."
            )

        if any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("local_sha256 must be hexadecimal.")

        return normalized

    @model_validator(mode="after")
    def validate_usage_policy_source(
        self,
    ) -> SourceManifest:
        if self.usage_policy is None:
            return self

        if self.usage_policy.source_id != self.source_id:
            raise ValueError(
                "SourceUsagePolicy.source_id must match "
                "SourceManifest.source_id."
            )

        return self

    @property
    def is_runtime_approved(self) -> bool:
        """
        Whether this snapshot may participate in trusted runtime verification.
        """

        return (
            self.status is SourceStatus.APPROVED
            and self.integrity_status is IntegrityStatus.VERIFIED
        )

    @property
    def has_usage_policy(self) -> bool:
        return self.usage_policy is not None

    def allows_runtime_use(
        self,
        runtime_use: RuntimeUse,
    ) -> bool:
        if not self.is_runtime_approved:
            return False

        if self.usage_policy is None:
            return False

        return self.usage_policy.allows(
            runtime_use
        )

    @property
    def may_support_answer(self) -> bool:
        return self.allows_runtime_use(
            RuntimeUse.SUPPORT_ANSWER
        )

    @property
    def may_be_cited(self) -> bool:
        return self.allows_runtime_use(
            RuntimeUse.CITE_TO_USER
        )

    @property
    def may_verify_canonical_text(self) -> bool:
        return self.allows_runtime_use(
            RuntimeUse.VERIFY_CANONICAL_TEXT
        )

