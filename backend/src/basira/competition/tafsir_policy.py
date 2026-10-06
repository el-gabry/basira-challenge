from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


# ============================================================
# Source family
# ============================================================


class TafsirSourceFamily(StrEnum):
    """
    Official competition Tafsir source families.

    FIRST_THREE_CENTURIES_ISLAMIC_SOURCE is intentionally
    broader than "early Tafsir book".

    The source must still independently pass:
    - period verification;
    - identity/provenance verification;
    - exact runtime source governance.
    """

    FIRST_THREE_CENTURIES_ISLAMIC_SOURCE = (
        "first_three_centuries_islamic_source"
    )

    DORAR_TAFSIR = "dorar_tafsir"

    UNKNOWN = "unknown"


class TafsirSourceEligibility(StrEnum):
    ELIGIBLE = "eligible"

    PENDING_AUDIT = "pending_audit"

    QUARANTINED = "quarantined"

    UNKNOWN = "unknown"


# ============================================================
# First-three-centuries qualification
# ============================================================


class EarlyPeriodStatus(StrEnum):
    VERIFIED = "verified"

    PENDING_VERIFICATION = (
        "pending_verification"
    )

    OUTSIDE_PERIOD = "outside_period"

    UNKNOWN = "unknown"


class EarlyPeriodBasis(StrEnum):
    """
    Never infer first-three-centuries eligibility merely
    from author death year.

    We want evidence about the source/work itself.
    """

    WORK_COMPOSITION = "work_composition"

    SOURCE_ORIGIN = "source_origin"

    GOVERNED_SCHOLARLY_CATALOG = (
        "governed_scholarly_catalog"
    )

    MULTIPLE_CORROBORATING_BIASES = (
        "multiple_corroborating_bases"
    )

    UNKNOWN = "unknown"


class EarlySourcePeriodEvidence(BaseModel):
    status: EarlyPeriodStatus = (
        EarlyPeriodStatus.UNKNOWN
    )

    basis: EarlyPeriodBasis = (
        EarlyPeriodBasis.UNKNOWN
    )

    source_origin_not_after_ah: (
        int | None
    ) = None

    author_death_ah: int | None = None

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


# ============================================================
# Evidence / material type
# ============================================================


class TafsirMaterialType(StrEnum):
    QURAN_TEXT = "quran_text"

    PROPHETIC_TAFSIR = (
        "prophetic_tafsir"
    )

    COMPANION_ATHAR = (
        "companion_athar"
    )

    TABII_ATHAR = "tabii_athar"

    EARLY_SCHOLAR_EXPLANATION = (
        "early_scholar_explanation"
    )

    LINGUISTIC_EXPLANATION = (
        "linguistic_explanation"
    )

    SCHOLARLY_REASONING = (
        "scholarly_reasoning"
    )

    ASBAB_AL_NUZUL = (
        "asbab_al_nuzul"
    )

    UNKNOWN = "unknown"


class NarrationQualityStatus(StrEnum):
    """
    This is a REPORTED quality state.

    Basira does not independently grade chains.
    """

    ACCEPTED_BY_AUTHORITY = (
        "accepted_by_authority"
    )

    WEAK_BY_AUTHORITY = (
        "weak_by_authority"
    )

    REJECTED_BY_AUTHORITY = (
        "rejected_by_authority"
    )

    CONFLICTING_AUTHORITY_GRADES = (
        "conflicting_authority_grades"
    )

    UNGRADED = "ungraded"

    NOT_APPLICABLE = "not_applicable"


class AttributionStatus(StrEnum):
    VERIFIED_FROM_SOURCE = (
        "verified_from_source"
    )

    REPORTED = "reported"

    CONFLICTING = "conflicting"

    UNKNOWN = "unknown"

    NOT_APPLICABLE = "not_applicable"


# ============================================================
# Intended use
# ============================================================


class TafsirUseContext(StrEnum):
    EXPLAIN_AYAH = "explain_ayah"

    SUPPORT_FIQH_RULING = (
        "support_fiqh_ruling"
    )


class TafsirEvidenceDecision(StrEnum):
    USABLE = "usable"

    SUPPORTING_ONLY = (
        "supporting_only"
    )

    CONTEXT_ONLY = "context_only"

    RETRIEVE_MORE = "retrieve_more"

    BLOCKED = "blocked"


# ============================================================
# Main evidence record
# ============================================================


class TafsirEvidenceRecord(BaseModel):
    text: str

    source_family: TafsirSourceFamily

    source_title: str

    source_reference: str | None = None

    source_eligibility: TafsirSourceEligibility = (
        TafsirSourceEligibility.UNKNOWN
    )

    material_type: TafsirMaterialType

    attributed_to: str | None = None

    attribution_status: AttributionStatus = (
        AttributionStatus.UNKNOWN
    )

    narration_quality: NarrationQualityStatus = (
        NarrationQualityStatus.NOT_APPLICABLE
    )

    reported_grade_text: str | None = None

    grading_authority: str | None = None

    grade_reference: str | None = None

    early_period: (
        EarlySourcePeriodEvidence | None
    ) = None

    edition_or_provider: str | None = None

    exact_artifact_governed: bool = False

    conditions: tuple[
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


class TafsirAssessment(BaseModel):
    decision: TafsirEvidenceDecision

    usable_records: tuple[
        TafsirEvidenceRecord,
        ...
    ] = Field(
        default_factory=tuple
    )

    canonical_quran_text_allowed: bool = False

    may_directly_establish_fiqh_ruling: bool = False

    preserve_quran_tafsir_boundary: bool = True

    preserve_asbab_boundary: bool = True

    preserve_attribution: bool = True

    preserve_quality_label: bool = True

    requires_claim_evidence_check: bool = True

    reasons: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


# ============================================================
# Helpers
# ============================================================


_NARRATION_TYPES = {
    TafsirMaterialType.PROPHETIC_TAFSIR,
    TafsirMaterialType.COMPANION_ATHAR,
    TafsirMaterialType.TABII_ATHAR,
    TafsirMaterialType.ASBAB_AL_NUZUL,
}


def _early_source_period_is_verified(
    evidence: (
        EarlySourcePeriodEvidence | None
    ),
) -> bool:

    if evidence is None:
        return False

    if (
        evidence.status
        is not EarlyPeriodStatus.VERIFIED
    ):
        return False

    if (
        evidence.basis
        is EarlyPeriodBasis.UNKNOWN
    ):
        return False

    if not evidence.evidence_ids:
        return False

    # IMPORTANT:
    # Author death alone does not prove that the source/work
    # itself belongs to the first three centuries.
    if (
        evidence.source_origin_not_after_ah
        is None
    ):
        return False

    return (
        evidence.source_origin_not_after_ah
        <= 300
    )


def _narration_has_grade_provenance(
    record: TafsirEvidenceRecord,
) -> bool:

    if (
        record.narration_quality
        is NarrationQualityStatus
        .NOT_APPLICABLE
    ):
        return True

    if (
        record.narration_quality
        is NarrationQualityStatus.UNGRADED
    ):
        return True

    return bool(
        record.grading_authority
        and record.grade_reference
    )


# ============================================================
# Official policy
# ============================================================


class OfficialTafsirPolicy:
    """
    Tafsir competition policy.

    Core invariants:

    QURAN TEXT != TAFSIR

    FOUND IN EARLY SOURCE != AUTHENTICALLY ATTRIBUTED

    MULTIPLE TRANSMISSIONS != AUTOMATICALLY AUTHENTIC

    NO GRADE FOUND != WEAK

    WEAK != FABRICATED

    COMPANION ATHAR != PROPHETIC HADITH

    SCHOLARLY EXPLANATION != PROPHETIC REPORT

    TAFSIR EVIDENCE != DIRECT FIQH RULING AUTHORITY
    """

    def assess(
        self,
        records: tuple[
            TafsirEvidenceRecord,
            ...
        ],
        *,
        use_context: TafsirUseContext = (
            TafsirUseContext.EXPLAIN_AYAH
        ),
    ) -> TafsirAssessment:

        if not records:
            return TafsirAssessment(
                decision=(
                    TafsirEvidenceDecision
                    .RETRIEVE_MORE
                ),
                reasons=(
                    "no_tafsir_evidence",
                ),
            )

        # ----------------------------------------------------
        # Fiqh ruling boundary.
        #
        # Tafsir may contain relevant material, but Basira
        # must route ruling construction to the dedicated
        # Fiqh/Hadith evidence architecture.
        # ----------------------------------------------------

        if (
            use_context
            is TafsirUseContext
            .SUPPORT_FIQH_RULING
        ):
            return TafsirAssessment(
                decision=(
                    TafsirEvidenceDecision
                    .RETRIEVE_MORE
                ),
                reasons=(
                    "tafsir_cannot_directly_establish_fiqh_ruling",
                    "route_to_fiqh_and_hadith_evidence",
                ),
            )

        usable: list[
            TafsirEvidenceRecord
        ] = []

        supporting: list[
            TafsirEvidenceRecord
        ] = []

        context_only = False

        blocked = False

        unresolved = False

        reasons: list[str] = []

        for record in records:

            if not record.text.strip():
                unresolved = True
                reasons.append(
                    "empty_tafsir_evidence"
                )
                continue

            if (
                record.source_family
                is TafsirSourceFamily.UNKNOWN
            ):
                unresolved = True
                reasons.append(
                    "official_tafsir_source_family_required"
                )
                continue

            # -----------------------------------------------
            # First-three-centuries family must have actual
            # verified source-period qualification.
            # -----------------------------------------------

            if (
                record.source_family
                is TafsirSourceFamily
                .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
                and not _early_source_period_is_verified(
                    record.early_period
                )
            ):
                unresolved = True
                reasons.append(
                    "first_three_centuries_period_verification_required"
                )
                continue

            # -----------------------------------------------
            # Technical runtime governance is independent
            # from scholarly/source-family eligibility.
            # -----------------------------------------------

            if (
                record.source_eligibility
                is not TafsirSourceEligibility.ELIGIBLE
            ):
                unresolved = True
                reasons.append(
                    "runtime_source_eligibility_required"
                )
                continue

            if not record.exact_artifact_governed:
                unresolved = True
                reasons.append(
                    "exact_artifact_governance_required"
                )
                continue

            # -----------------------------------------------
            # Quran text displayed inside Tafsir material is
            # never promoted to canonical Quran evidence.
            # -----------------------------------------------

            if (
                record.material_type
                is TafsirMaterialType.QURAN_TEXT
            ):
                context_only = True
                reasons.append(
                    "quran_text_inside_tafsir_is_context_only"
                )
                continue

            # -----------------------------------------------
            # Narration / Athar quality.
            # -----------------------------------------------

            if (
                record.material_type
                in _NARRATION_TYPES
            ):
                if not record.attributed_to:
                    unresolved = True
                    reasons.append(
                        "narration_attribution_target_required"
                    )
                    continue

                if (
                    record.attribution_status
                    is AttributionStatus.UNKNOWN
                ):
                    unresolved = True
                    reasons.append(
                        "narration_attribution_status_required"
                    )
                    continue

                if not _narration_has_grade_provenance(
                    record
                ):
                    unresolved = True
                    reasons.append(
                        "reported_grade_provenance_required"
                    )
                    continue

                if (
                    record.narration_quality
                    is NarrationQualityStatus
                    .REJECTED_BY_AUTHORITY
                ):
                    blocked = True
                    reasons.append(
                        "rejected_narration_not_usable"
                    )
                    continue

                if (
                    record.narration_quality
                    is NarrationQualityStatus
                    .CONFLICTING_AUTHORITY_GRADES
                ):
                    unresolved = True
                    reasons.append(
                        "conflicting_narration_grades_preserved"
                    )
                    continue

                if (
                    record.narration_quality
                    is NarrationQualityStatus
                    .WEAK_BY_AUTHORITY
                ):
                    context_only = True
                    reasons.append(
                        "weak_narration_context_only"
                    )
                    continue

                if (
                    record.narration_quality
                    is NarrationQualityStatus
                    .UNGRADED
                ):
                    supporting.append(
                        record
                    )

                    reasons.append(
                        "ungraded_narration_supporting_only"
                    )
                    continue

                if (
                    record.narration_quality
                    is NarrationQualityStatus
                    .NOT_APPLICABLE
                ):
                    unresolved = True
                    reasons.append(
                        "narration_quality_status_required"
                    )
                    continue

                usable.append(
                    record
                )
                continue

            # -----------------------------------------------
            # Non-narrative scholarly explanation.
            # No isnad grade is invented or required.
            # -----------------------------------------------

            usable.append(
                record
            )

        # ----------------------------------------------------
        # Decision priority.
        # ----------------------------------------------------

        if usable:
            return TafsirAssessment(
                decision=(
                    TafsirEvidenceDecision.USABLE
                ),
                usable_records=tuple(
                    usable
                ),
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                        + [
                            "eligible_tafsir_evidence",
                            "quran_tafsir_boundary_preserved",
                        ]
                    )
                ),
            )

        if supporting:
            return TafsirAssessment(
                decision=(
                    TafsirEvidenceDecision
                    .SUPPORTING_ONLY
                ),
                usable_records=tuple(
                    supporting
                ),
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        if blocked and not unresolved:
            return TafsirAssessment(
                decision=(
                    TafsirEvidenceDecision.BLOCKED
                ),
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        if unresolved:
            return TafsirAssessment(
                decision=(
                    TafsirEvidenceDecision
                    .RETRIEVE_MORE
                ),
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        if context_only:
            return TafsirAssessment(
                decision=(
                    TafsirEvidenceDecision
                    .CONTEXT_ONLY
                ),
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        return TafsirAssessment(
            decision=(
                TafsirEvidenceDecision
                .RETRIEVE_MORE
            ),
            reasons=(
                "insufficient_tafsir_evidence",
            ),
        )
