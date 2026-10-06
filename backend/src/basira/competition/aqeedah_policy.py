from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from basira.competition.aqeedah_authority import (
    AqeedahAuthorityEvidence,
    AqeedahAuthorityStatus,
    AqeedahAuthorityUseDecision,
    assess_aqeedah_authority,
)


class AqeedahSourceFamily(StrEnum):
    """
    Official competition Aqeedah source families.
    """

    FIRST_THREE_CENTURIES_ISLAMIC_SOURCE = (
        "first_three_centuries_islamic_source"
    )

    DORAR_AQEEDA = "dorar_aqeeda"

    UNKNOWN = "unknown"


class AqeedahSourceEligibility(StrEnum):
    ELIGIBLE = "eligible"

    PENDING_AUDIT = "pending_audit"

    QUARANTINED = "quarantined"

    UNKNOWN = "unknown"


class AqeedahEarlyPeriodStatus(StrEnum):
    VERIFIED = "verified"

    PENDING_VERIFICATION = (
        "pending_verification"
    )

    OUTSIDE_PERIOD = "outside_period"

    UNKNOWN = "unknown"


class AqeedahEarlyPeriodBasis(StrEnum):
    """
    Author death year alone is deliberately insufficient.

    We need evidence about the source/work origin itself.
    """

    WORK_COMPOSITION = "work_composition"

    SOURCE_ORIGIN = "source_origin"

    GOVERNED_SCHOLARLY_CATALOG = (
        "governed_scholarly_catalog"
    )

    MULTIPLE_CORROBORATING_BASES = (
        "multiple_corroborating_bases"
    )

    UNKNOWN = "unknown"


class AqeedahEarlyPeriodEvidence(BaseModel):
    status: AqeedahEarlyPeriodStatus = (
        AqeedahEarlyPeriodStatus.UNKNOWN
    )

    basis: AqeedahEarlyPeriodBasis = (
        AqeedahEarlyPeriodBasis.UNKNOWN
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


class AqeedahMaterialType(StrEnum):
    """
    Evidence role is kept separate from source family.
    """

    BASIC_ISLAMIC_BELIEF = (
        "basic_islamic_belief"
    )

    INTRODUCTION_TO_ISLAM = (
        "introduction_to_islam"
    )

    EARLY_SCHOLAR_STATEMENT = (
        "early_scholar_statement"
    )

    SCHOLARLY_EXPLANATION = (
        "scholarly_explanation"
    )

    QURAN_TEXT = "quran_text"

    PROPHETIC_REPORT = (
        "prophetic_report"
    )

    COMPANION_ATHAR = (
        "companion_athar"
    )

    TABII_ATHAR = "tabii_athar"

    UNKNOWN = "unknown"


class AqeedahUseContext(StrEnum):
    BASIC_INTRODUCTION = (
        "basic_introduction"
    )

    DETAILED_AQEEDAH_ISSUE = (
        "detailed_aqeedah_issue"
    )

    COMPARATIVE_RELIGION_OR_SECT = (
        "comparative_religion_or_sect"
    )


class AqeedahEvidenceDecision(StrEnum):
    USABLE = "usable"

    SUPPORTING_ONLY = (
        "supporting_only"
    )

    RETRIEVE_MORE = "retrieve_more"

    BLOCKED = "blocked"

    ESCALATE = "escalate"


class AqeedahEvidenceRecord(BaseModel):
    text: str

    source_family: AqeedahSourceFamily

    source_title: str

    source_reference: str | None = None

    source_eligibility: AqeedahSourceEligibility = (
        AqeedahSourceEligibility.UNKNOWN
    )

    material_type: AqeedahMaterialType

    attributed_to: str | None = None

    early_period: (
        AqeedahEarlyPeriodEvidence | None
    ) = None

    # Period eligibility and Aqeedah authority are separate.
    #
    # A source may be genuinely early but still not be
    # authorized as primary Aqeedah evidence.
    authority: AqeedahAuthorityEvidence = Field(
        default_factory=AqeedahAuthorityEvidence
    )

    edition_or_provider: str | None = None

    exact_artifact_governed: bool = False

    source_identity_verified: bool = False

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


class AqeedahAssessment(BaseModel):
    decision: AqeedahEvidenceDecision

    usable_records: tuple[
        AqeedahEvidenceRecord,
        ...
    ] = Field(
        default_factory=tuple
    )

    requires_source_attribution: bool = True

    requires_disagreement_check: bool = False

    requires_claim_evidence_check: bool = True

    may_claim_consensus: bool = False

    may_use_generic_shamela_fallback: bool = False

    quran_must_use_canonical_quran_foundation: bool = True

    prophetic_report_must_use_hadith_foundation: bool = True

    preserve_athar_identity: bool = True

    reasons: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


def _early_source_period_is_verified(
    evidence: (
        AqeedahEarlyPeriodEvidence | None
    ),
) -> bool:

    if evidence is None:
        return False

    if (
        evidence.status
        is not AqeedahEarlyPeriodStatus.VERIFIED
    ):
        return False

    if (
        evidence.basis
        is AqeedahEarlyPeriodBasis.UNKNOWN
    ):
        return False

    if not evidence.evidence_ids:
        return False

    # Author death alone does not establish that the source
    # or work belongs to the first three centuries.
    if (
        evidence.source_origin_not_after_ah
        is None
    ):
        return False

    return (
        evidence.source_origin_not_after_ah
        <= 300
    )


class OfficialAqeedahPolicy:
    """
    Official competition Aqeedah policy.

    Core invariants:

    FIRST-THREE-CENTURIES SOURCE
        != merely famous old book

    AUTHOR DIED <= 300 AH
        != source/work proven early

    DORAR AQEEDA OFFICIAL FAMILY
        != automatic runtime admission

    QURAN QUOTED IN AQEEDAH SOURCE
        != canonical Quran witness

    PROPHETIC REPORT IN AQEEDAH SOURCE
        != independently authenticated Hadith

    MANY SOURCES AGREE
        != automatic consensus

    SHAMELA SEARCH HIT
        != authorized Aqeedah evidence
    """

    def assess(
        self,
        records: tuple[
            AqeedahEvidenceRecord,
            ...
        ],
        *,
        use_context: AqeedahUseContext = (
            AqeedahUseContext
            .BASIC_INTRODUCTION
        ),
    ) -> AqeedahAssessment:

        disagreement_required = (
            use_context
            is not AqeedahUseContext
            .BASIC_INTRODUCTION
        )

        if not records:
            return AqeedahAssessment(
                decision=(
                    AqeedahEvidenceDecision
                    .RETRIEVE_MORE
                ),
                requires_disagreement_check=(
                    disagreement_required
                ),
                reasons=(
                    "no_aqeedah_evidence",
                ),
            )

        usable: list[
            AqeedahEvidenceRecord
        ] = []

        supporting: list[
            AqeedahEvidenceRecord
        ] = []

        unresolved = False

        blocked = False

        reasons: list[str] = []

        for record in records:

            if not record.text.strip():
                unresolved = True

                reasons.append(
                    "empty_aqeedah_evidence"
                )

                continue

            if (
                record.source_family
                is AqeedahSourceFamily.UNKNOWN
            ):
                unresolved = True

                reasons.append(
                    "official_aqeedah_source_family_required"
                )

                continue

            if (
                record.source_family
                is AqeedahSourceFamily
                .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
            ):

                if not (
                    _early_source_period_is_verified(
                        record.early_period
                    )
                ):
                    unresolved = True

                    reasons.append(
                        "first_three_centuries_period_verification_required"
                    )

                    continue

                # --------------------------------------------
                # CRITICAL AUTHORITY GATE
                #
                # Period eligibility does not establish
                # Aqeedah authority.
                # --------------------------------------------

                authority_assessment = (
                    assess_aqeedah_authority(
                        record.authority
                    )
                )

                if (
                    authority_assessment.decision
                    is AqeedahAuthorityUseDecision.BLOCK
                ):
                    blocked = True

                    reasons.extend(
                        authority_assessment.reasons
                    )

                    continue

                if (
                    authority_assessment.decision
                    is AqeedahAuthorityUseDecision
                    .RETRIEVE_MORE
                ):
                    unresolved = True

                    reasons.extend(
                        authority_assessment.reasons
                    )

                    continue

                early_authority_supporting_only = (
                    authority_assessment.decision
                    is AqeedahAuthorityUseDecision
                    .SUPPORTING_ONLY
                )

            else:
                early_authority_supporting_only = False

            # Source family permission is separate from
            # exact runtime source eligibility.
            if (
                record.source_eligibility
                is not AqeedahSourceEligibility
                .ELIGIBLE
            ):
                unresolved = True

                reasons.append(
                    "runtime_source_eligibility_required"
                )

                continue

            if not record.source_identity_verified:
                unresolved = True

                reasons.append(
                    "source_identity_verification_required"
                )

                continue

            if not record.exact_artifact_governed:
                unresolved = True

                reasons.append(
                    "exact_artifact_governance_required"
                )

                continue

            # ------------------------------------------------
            # Cross-domain primary evidence boundaries
            # ------------------------------------------------

            if (
                record.material_type
                is AqeedahMaterialType.QURAN_TEXT
            ):
                supporting.append(
                    record
                )

                reasons.append(
                    "quran_text_requires_canonical_quran_foundation"
                )

                continue

            if (
                record.material_type
                is AqeedahMaterialType
                .PROPHETIC_REPORT
            ):
                supporting.append(
                    record
                )

                reasons.append(
                    "prophetic_report_requires_hadith_foundation"
                )

                continue

            if (
                record.material_type
                in {
                    AqeedahMaterialType
                    .COMPANION_ATHAR,

                    AqeedahMaterialType
                    .TABII_ATHAR,
                }
                and not record.attributed_to
            ):
                unresolved = True

                reasons.append(
                    "athar_attribution_required"
                )

                continue

            if (
                record.material_type
                is AqeedahMaterialType.UNKNOWN
            ):
                unresolved = True

                reasons.append(
                    "aqeedah_material_type_required"
                )

                continue

            if early_authority_supporting_only:
                supporting.append(
                    record
                )

                reasons.append(
                    "early_source_authority_supporting_only"
                )

                continue

            usable.append(
                record
            )

        if usable:
            return AqeedahAssessment(
                decision=(
                    AqeedahEvidenceDecision
                    .USABLE
                ),
                usable_records=tuple(
                    usable
                ),
                requires_disagreement_check=(
                    disagreement_required
                ),
                may_claim_consensus=False,
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                        + [
                            "eligible_aqeedah_evidence",
                            "no_automatic_consensus",
                        ]
                    )
                ),
            )

        if unresolved:
            return AqeedahAssessment(
                decision=(
                    AqeedahEvidenceDecision
                    .RETRIEVE_MORE
                ),
                usable_records=tuple(
                    supporting
                ),
                requires_disagreement_check=(
                    disagreement_required
                ),
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        if supporting:
            return AqeedahAssessment(
                decision=(
                    AqeedahEvidenceDecision
                    .SUPPORTING_ONLY
                ),
                usable_records=tuple(
                    supporting
                ),
                requires_disagreement_check=(
                    disagreement_required
                ),
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        if blocked:
            return AqeedahAssessment(
                decision=(
                    AqeedahEvidenceDecision.BLOCKED
                ),
                requires_disagreement_check=(
                    disagreement_required
                ),
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        return AqeedahAssessment(
            decision=(
                AqeedahEvidenceDecision
                .RETRIEVE_MORE
            ),
            requires_disagreement_check=(
                disagreement_required
            ),
            reasons=(
                "insufficient_aqeedah_evidence",
            ),
        )
