from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from basira.competition.fiqh_policy import (
    FiqhSourceEligibility,
    Madhhab,
)


class MadhhabBookAuthorityClass(StrEnum):
    VERIFIED_MUTAMAD = "verified_mutamad"

    VERIFIED_RECOGNIZED_REFERENCE = (
        "verified_recognized_reference"
    )

    DORAR_REFERENCE_LISTED = (
        "dorar_reference_listed"
    )

    UNVERIFIED = "unverified"


class MadhhabBookRetrievalMode(StrEnum):
    MUTAMAD_ONLY = "mutamad_only"

    SUPPORTING_REFERENCE_ALLOWED = (
        "supporting_reference_allowed"
    )


class HybridBookDecision(StrEnum):
    ALLOW = "allow"

    DISCOVERY_ONLY = "discovery_only"

    BLOCK = "block"


class MadhhabBookPassport(BaseModel):
    work_id: str

    canonical_title: str

    author: str

    madhhab: Madhhab

    authority_class: (
        MadhhabBookAuthorityClass
    )

    authority_evidence_ids: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    edition_or_provider: str | None = None

    exact_edition_governed: bool = False

    source_eligibility: (
        FiqhSourceEligibility
    ) = FiqhSourceEligibility.UNKNOWN


class HybridBookAssessment(BaseModel):
    decision: HybridBookDecision

    reasons: tuple[str, ...]

    may_call_mutamad: bool = False

    may_use_as_primary_book_evidence: bool = False


class MadhhabBookAuthorityGate:
    """
    Future Hybrid Fiqh Agent gate.

    DISCOVERED != AUTHORIZED
    FAMOUS != MUTAMAD
    CITED != MUTAMAD
    DORAR-LISTED != MUTAMAD
    """

    def assess(
        self,
        book: MadhhabBookPassport,
        *,
        mode: MadhhabBookRetrievalMode = (
            MadhhabBookRetrievalMode
            .MUTAMAD_ONLY
        ),
    ) -> HybridBookAssessment:

        if book.madhhab is Madhhab.UNSPECIFIED:
            return HybridBookAssessment(
                decision=(
                    HybridBookDecision.BLOCK
                ),
                reasons=(
                    "madhhab_identity_required",
                ),
            )

        if not book.authority_evidence_ids:
            return HybridBookAssessment(
                decision=(
                    HybridBookDecision
                    .DISCOVERY_ONLY
                ),
                reasons=(
                    "authority_evidence_required",
                ),
            )

        if (
            book.source_eligibility
            is not FiqhSourceEligibility.ELIGIBLE
        ):
            return HybridBookAssessment(
                decision=(
                    HybridBookDecision
                    .DISCOVERY_ONLY
                ),
                reasons=(
                    "runtime_source_not_eligible",
                ),
            )

        if not book.exact_edition_governed:
            return HybridBookAssessment(
                decision=(
                    HybridBookDecision
                    .DISCOVERY_ONLY
                ),
                reasons=(
                    "exact_edition_not_governed",
                ),
            )

        if (
            book.authority_class
            is MadhhabBookAuthorityClass
            .VERIFIED_MUTAMAD
        ):
            return HybridBookAssessment(
                decision=HybridBookDecision.ALLOW,
                reasons=(
                    "verified_mutamad",
                    "governed_eligible_edition",
                ),
                may_call_mutamad=True,
                may_use_as_primary_book_evidence=True,
            )

        if (
            mode
            is MadhhabBookRetrievalMode
            .SUPPORTING_REFERENCE_ALLOWED
            and book.authority_class
            is MadhhabBookAuthorityClass
            .VERIFIED_RECOGNIZED_REFERENCE
        ):
            return HybridBookAssessment(
                decision=HybridBookDecision.ALLOW,
                reasons=(
                    "verified_recognized_reference",
                    "supporting_mode",
                ),
                may_call_mutamad=False,
                may_use_as_primary_book_evidence=False,
            )

        if (
            book.authority_class
            is MadhhabBookAuthorityClass
            .DORAR_REFERENCE_LISTED
        ):
            return HybridBookAssessment(
                decision=(
                    HybridBookDecision
                    .DISCOVERY_ONLY
                ),
                reasons=(
                    "dorar_listing_is_not_mutamad_proof",
                ),
            )

        return HybridBookAssessment(
            decision=(
                HybridBookDecision
                .DISCOVERY_ONLY
            ),
            reasons=(
                "mutamad_authority_not_verified",
            ),
        )
