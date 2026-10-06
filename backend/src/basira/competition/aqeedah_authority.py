from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AqeedahAuthorityStatus(StrEnum):
    VERIFIED_PRIMARY = (
        "verified_primary"
    )

    VERIFIED_SUPPORTING = (
        "verified_supporting"
    )

    DORAR_REFERENCE_LISTED = (
        "dorar_reference_listed"
    )

    PENDING_AUTHORITY_REVIEW = (
        "pending_authority_review"
    )

    QUARANTINED = "quarantined"

    UNKNOWN = "unknown"


class AqeedahAuthorityBasis(StrEnum):
    """
    Basira does not infer religious authority from age,
    fame, citation count or retrieval similarity.

    Authority status must be backed by governed evidence.
    """

    OFFICIAL_COMPETITION_RULE = (
        "official_competition_rule"
    )

    DORAR_GOVERNED_REFERENCE = (
        "dorar_governed_reference"
    )

    GOVERNED_SOURCE_CATALOG = (
        "governed_source_catalog"
    )

    MANUAL_SCHOLARLY_AUDIT = (
        "manual_scholarly_audit"
    )

    UNKNOWN = "unknown"


class AqeedahAuthorityUseDecision(StrEnum):
    PRIMARY = "primary"

    SUPPORTING_ONLY = (
        "supporting_only"
    )

    RETRIEVE_MORE = "retrieve_more"

    BLOCK = "block"


class AqeedahAuthorityEvidence(BaseModel):
    status: AqeedahAuthorityStatus = (
        AqeedahAuthorityStatus.UNKNOWN
    )

    basis: AqeedahAuthorityBasis = (
        AqeedahAuthorityBasis.UNKNOWN
    )

    evidence_ids: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    notes: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


class AqeedahAuthorityAssessment(BaseModel):
    decision: AqeedahAuthorityUseDecision

    reasons: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


def assess_aqeedah_authority(
    authority: AqeedahAuthorityEvidence,
) -> AqeedahAuthorityAssessment:
    """
    Authority eligibility is independent from source period.

    Hard invariants:

    EARLY != AUTHORIZED

    FAMOUS != AUTHORIZED

    CITED != PRIMARY

    DORAR-LISTED != PRIMARY

    SHAMELA-HOSTED != AUTHORIZED

    SOURCE COUNT != CONSENSUS
    """

    if (
        authority.status
        is AqeedahAuthorityStatus.QUARANTINED
    ):
        return AqeedahAuthorityAssessment(
            decision=(
                AqeedahAuthorityUseDecision.BLOCK
            ),
            reasons=(
                "aqeedah_authority_quarantined",
            ),
        )

    if (
        authority.status
        is AqeedahAuthorityStatus
        .PENDING_AUTHORITY_REVIEW
    ):
        return AqeedahAuthorityAssessment(
            decision=(
                AqeedahAuthorityUseDecision
                .RETRIEVE_MORE
            ),
            reasons=(
                "aqeedah_authority_review_required",
            ),
        )

    if (
        authority.status
        is AqeedahAuthorityStatus.UNKNOWN
    ):
        return AqeedahAuthorityAssessment(
            decision=(
                AqeedahAuthorityUseDecision
                .RETRIEVE_MORE
            ),
            reasons=(
                "aqeedah_authority_unknown",
            ),
        )

    if (
        authority.status
        is AqeedahAuthorityStatus
        .VERIFIED_PRIMARY
    ):
        if (
            authority.basis
            is AqeedahAuthorityBasis.UNKNOWN
            or not authority.evidence_ids
        ):
            return AqeedahAuthorityAssessment(
                decision=(
                    AqeedahAuthorityUseDecision
                    .RETRIEVE_MORE
                ),
                reasons=(
                    "primary_authority_evidence_required",
                ),
            )

        return AqeedahAuthorityAssessment(
            decision=(
                AqeedahAuthorityUseDecision.PRIMARY
            ),
            reasons=(
                "verified_primary_aqeedah_authority",
            ),
        )

    if (
        authority.status
        is AqeedahAuthorityStatus
        .VERIFIED_SUPPORTING
    ):
        if (
            authority.basis
            is AqeedahAuthorityBasis.UNKNOWN
            or not authority.evidence_ids
        ):
            return AqeedahAuthorityAssessment(
                decision=(
                    AqeedahAuthorityUseDecision
                    .RETRIEVE_MORE
                ),
                reasons=(
                    "supporting_authority_evidence_required",
                ),
            )

        return AqeedahAuthorityAssessment(
            decision=(
                AqeedahAuthorityUseDecision
                .SUPPORTING_ONLY
            ),
            reasons=(
                "verified_supporting_aqeedah_authority",
            ),
        )

    if (
        authority.status
        is AqeedahAuthorityStatus
        .DORAR_REFERENCE_LISTED
    ):
        # Listing in Dorar references is useful provenance,
        # but does NOT itself promote a work to primary
        # Aqeedah authority.
        if not authority.evidence_ids:
            return AqeedahAuthorityAssessment(
                decision=(
                    AqeedahAuthorityUseDecision
                    .RETRIEVE_MORE
                ),
                reasons=(
                    "dorar_reference_evidence_required",
                ),
            )

        return AqeedahAuthorityAssessment(
            decision=(
                AqeedahAuthorityUseDecision
                .SUPPORTING_ONLY
            ),
            reasons=(
                "dorar_reference_listing_is_not_primary_authority",
            ),
        )

    return AqeedahAuthorityAssessment(
        decision=(
            AqeedahAuthorityUseDecision
            .RETRIEVE_MORE
        ),
        reasons=(
            "aqeedah_authority_unresolved",
        ),
    )
