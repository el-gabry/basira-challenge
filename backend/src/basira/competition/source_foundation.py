from __future__ import annotations

from enum import StrEnum
import re

from pydantic import BaseModel, Field, field_validator


class CompetitionSourceRole(StrEnum):
    QURAN = "quran"
    HADITH = "hadith"
    TAFSIR = "tafsir"
    ASBAB_AL_NUZUL = "asbab_al_nuzul"
    FIQH = "fiqh"
    FATWA = "fatwa"
    GENERAL_SCHOLARLY = "general_scholarly"


class CompetitionSourceStatus(StrEnum):
    """
    Presence in the repository never implies eligibility.
    """

    PENDING_AUDIT = "pending_audit"

    ELIGIBLE = "eligible"

    ELIGIBLE_WITH_ATTESTATION = (
        "eligible_with_attestation"
    )

    QUARANTINED = "quarantined"

    BASELINE_ONLY = "baseline_only"

    UNAVAILABLE = "unavailable"


class CompetitionSourceIdentity(BaseModel):
    source_id: str

    name: str

    role: CompetitionSourceRole

    institution: str | None = None

    work: str | None = None

    author: str | None = None

    edition: str | None = None

    version: str | None = None

    riwaya: str | None = None

    rawi: str | None = None

    rasm_standard: str | None = None

    dabt_standard: str | None = None


class CompetitionSourceArtifact(BaseModel):
    identity: CompetitionSourceIdentity

    status: CompetitionSourceStatus

    official_reference_basis: str

    acquisition_uri: str | None = None

    snapshot_path: str | None = None

    sha256: str | None = None

    record_count: int | None = None

    attestation_ids: tuple[str, ...] = Field(
        default_factory=tuple
    )

    @field_validator("sha256")
    @classmethod
    def validate_sha256(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.lower().strip()

        if not re.fullmatch(
            r"[0-9a-f]{64}",
            normalized,
        ):
            raise ValueError(
                "sha256 must be exactly 64 hexadecimal characters"
            )

        return normalized

    audit_ids: tuple[str, ...] = Field(
        default_factory=tuple
    )

    notes: tuple[str, ...] = Field(
        default_factory=tuple
    )


class SourceEligibilityDecision(BaseModel):
    source_id: str

    eligible_for_runtime: bool

    status: CompetitionSourceStatus

    reasons: tuple[str, ...]


class CompetitionSourceEligibilityGate:
    """
    Fail closed.

    A source may support competition answers only after an
    explicit competition audit/admission decision.
    """

    def decide(
        self,
        artifact: CompetitionSourceArtifact,
    ) -> SourceEligibilityDecision:

        status = artifact.status

        if status not in {
            CompetitionSourceStatus.ELIGIBLE,
            CompetitionSourceStatus.ELIGIBLE_WITH_ATTESTATION,
        }:
            return SourceEligibilityDecision(
                source_id=artifact.identity.source_id,
                eligible_for_runtime=False,
                status=status,
                reasons=(
                    "source_not_admitted_to_competition_runtime",
                ),
            )

        missing: list[str] = []

        if not artifact.official_reference_basis.strip():
            missing.append(
                "missing_official_reference_basis"
            )

        if not artifact.sha256:
            missing.append(
                "missing_artifact_hash"
            )

        if not artifact.snapshot_path:
            missing.append(
                "missing_governed_snapshot"
            )

        if (
            status
            is CompetitionSourceStatus.ELIGIBLE_WITH_ATTESTATION
            and not artifact.attestation_ids
        ):
            missing.append(
                "missing_required_attestation"
            )

        if missing:
            return SourceEligibilityDecision(
                source_id=artifact.identity.source_id,
                eligible_for_runtime=False,
                status=CompetitionSourceStatus.QUARANTINED,
                reasons=tuple(missing),
            )

        return SourceEligibilityDecision(
            source_id=artifact.identity.source_id,
            eligible_for_runtime=True,
            status=status,
            reasons=(
                "competition_source_admitted",
            ),
        )
