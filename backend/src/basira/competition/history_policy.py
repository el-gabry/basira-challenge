from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class HistorySourceFamily(StrEnum):
    FIRST_THREE_CENTURIES_ISLAMIC_SOURCE = (
        "first_three_centuries_islamic_source"
    )

    DORAR_HISTORY = "dorar_history"

    UNKNOWN = "unknown"


class HistorySourceEligibility(StrEnum):
    ELIGIBLE = "eligible"

    PENDING_AUDIT = "pending_audit"

    QUARANTINED = "quarantined"

    UNKNOWN = "unknown"


class HistorySourceUseMode(StrEnum):
    """
    A source's retrieval/use role is independent from
    the truth status of any historical report inside it.
    """

    CURATED_HISTORY_REFERENCE = (
        "curated_history_reference"
    )

    RAW_REPORT_COLLECTION = (
        "raw_report_collection"
    )

    PRIMARY_HISTORICAL_NARRATIVE = (
        "primary_historical_narrative"
    )

    BIOGRAPHICAL_SOURCE = (
        "biographical_source"
    )

    CHRONICLE = "chronicle"

    UNKNOWN = "unknown"


class HistoryEarlyPeriodStatus(StrEnum):
    VERIFIED = "verified"

    PENDING_VERIFICATION = (
        "pending_verification"
    )

    OUTSIDE_PERIOD = "outside_period"

    UNKNOWN = "unknown"


class HistoryEarlyPeriodBasis(StrEnum):
    WORK_COMPOSITION = "work_composition"

    SOURCE_ORIGIN = "source_origin"

    GOVERNED_SCHOLARLY_CATALOG = (
        "governed_scholarly_catalog"
    )

    MULTIPLE_CORROBORATING_BASES = (
        "multiple_corroborating_bases"
    )

    UNKNOWN = "unknown"


class HistoricalReportStatus(StrEnum):
    """
    This status MUST come from governed evidence.

    Basira must not infer historical certainty merely
    from source age, retrieval count or repeated wording.
    """

    ESTABLISHED_BY_GOVERNED_AUTHORITY = (
        "established_by_governed_authority"
    )

    CORROBORATED_BY_GOVERNED_AUTHORITY = (
        "corroborated_by_governed_authority"
    )

    DISPUTED_BY_GOVERNED_AUTHORITY = (
        "disputed_by_governed_authority"
    )

    REQUIRES_CAUTION_BY_GOVERNED_AUTHORITY = (
        "requires_caution_by_governed_authority"
    )

    REJECTED_BY_GOVERNED_AUTHORITY = (
        "rejected_by_governed_authority"
    )

    UNASSESSED = "unassessed"


class HistoricalAssessmentBasis(StrEnum):
    DORAR_GOVERNED_HISTORY = (
        "dorar_governed_history"
    )

    GOVERNED_SOURCE_CATALOG = (
        "governed_source_catalog"
    )

    MANUAL_SCHOLARLY_AUDIT = (
        "manual_scholarly_audit"
    )

    MULTIPLE_GOVERNED_BASES = (
        "multiple_governed_bases"
    )

    UNKNOWN = "unknown"


class HistoryMaterialType(StrEnum):
    HISTORICAL_EVENT_REPORT = (
        "historical_event_report"
    )

    SEERAH_EVENT_REPORT = (
        "seerah_event_report"
    )

    BIOGRAPHICAL_REPORT = (
        "biographical_report"
    )

    CHRONOLOGY = "chronology"

    SOURCE_QUOTATION = (
        "source_quotation"
    )

    SCHOLARLY_HISTORICAL_EXPLANATION = (
        "scholarly_historical_explanation"
    )

    QURAN_CONTEXT = "quran_context"

    PROPHETIC_REPORT = (
        "prophetic_report"
    )

    COMPANION_REPORT = (
        "companion_report"
    )

    UNKNOWN = "unknown"


class HistoryUseContext(StrEnum):
    NARRATIVE_CONTEXT = (
        "narrative_context"
    )

    CATEGORICAL_EVENT_CLAIM = (
        "categorical_event_claim"
    )

    DISPUTED_HISTORICAL_QUESTION = (
        "disputed_historical_question"
    )


class HistoryEvidenceDecision(StrEnum):
    USABLE = "usable"

    SUPPORTING_ONLY = (
        "supporting_only"
    )

    CAUTION_REQUIRED = (
        "caution_required"
    )

    RETRIEVE_MORE = (
        "retrieve_more"
    )

    BLOCKED = "blocked"


class HistoryEarlyPeriodEvidence(BaseModel):
    status: HistoryEarlyPeriodStatus = (
        HistoryEarlyPeriodStatus.UNKNOWN
    )

    basis: HistoryEarlyPeriodBasis = (
        HistoryEarlyPeriodBasis.UNKNOWN
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


class HistoricalReportAssessment(BaseModel):
    status: HistoricalReportStatus = (
        HistoricalReportStatus.UNASSESSED
    )

    basis: HistoricalAssessmentBasis = (
        HistoricalAssessmentBasis.UNKNOWN
    )

    authority_name: str | None = None

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


class HistoryEvidenceRecord(BaseModel):
    text: str

    source_family: HistorySourceFamily

    source_title: str

    source_reference: str | None = None

    source_eligibility: HistorySourceEligibility = (
        HistorySourceEligibility.UNKNOWN
    )

    material_type: HistoryMaterialType

    source_use_mode: HistorySourceUseMode = (
        HistorySourceUseMode.UNKNOWN
    )

    early_period: (
        HistoryEarlyPeriodEvidence | None
    ) = None

    report_assessment: HistoricalReportAssessment = Field(
        default_factory=HistoricalReportAssessment
    )

    source_identity_verified: bool = False

    exact_artifact_governed: bool = False

    attributed_to: str | None = None

    notes: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


class HistoryAssessment(BaseModel):
    decision: HistoryEvidenceDecision

    usable_records: tuple[
        HistoryEvidenceRecord,
        ...
    ] = Field(
        default_factory=tuple
    )

    may_state_as_established_fact: bool = False

    source_use_mode_alone_may_establish_event: bool = False

    requires_caution_language: bool = True

    may_infer_corrobation_from_count: bool = False

    may_infer_consensus_from_count: bool = False

    may_use_generic_shamela_fallback: bool = False

    quran_must_use_canonical_quran_foundation: bool = True

    prophetic_report_must_use_hadith_foundation: bool = True

    reasons: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


def _early_period_verified(
    evidence: HistoryEarlyPeriodEvidence | None,
) -> bool:

    if evidence is None:
        return False

    if (
        evidence.status
        is not HistoryEarlyPeriodStatus.VERIFIED
    ):
        return False

    if (
        evidence.basis
        is HistoryEarlyPeriodBasis.UNKNOWN
    ):
        return False

    if not evidence.evidence_ids:
        return False

    if (
        evidence.source_origin_not_after_ah
        is None
    ):
        return False

    return (
        evidence.source_origin_not_after_ah
        <= 300
    )


def _report_assessment_is_governed(
    assessment: HistoricalReportAssessment,
) -> bool:

    if (
        assessment.status
        is HistoricalReportStatus.UNASSESSED
    ):
        return False

    if (
        assessment.basis
        is HistoricalAssessmentBasis.UNKNOWN
    ):
        return False

    if not assessment.evidence_ids:
        return False

    return True


class OfficialHistoryPolicy:
    """
    Official Seerah / History evidence policy.

    Hard invariants:

    EARLY SOURCE
        != VERIFIED HISTORICAL EVENT

    SOURCE REPORT
        != ESTABLISHED FACT

    AUTHOR DIED <= 300 AH
        != SOURCE PROVEN EARLY

    MULTIPLE RETRIEVED REPORTS
        != AUTOMATIC CORROBORATION

    REPEATED WORDING
        != CONSENSUS

    DORAR HISTORY
        != HADITH AUTHENTICATION

    QURAN INSIDE HISTORY SOURCE
        != CANONICAL QURAN WITNESS

    SHAMELA HIT
        != GOVERNED HISTORICAL EVIDENCE

    RAW REPORT COLLECTION
        != CURATED HISTORY

    SOURCE USE MODE
        != EVENT TRUTH

    HISTORICAL CONFIDENCE
        != NUMERIC MODEL SCORE
    """

    def assess(
        self,
        records: tuple[
            HistoryEvidenceRecord,
            ...
        ],
        *,
        use_context: HistoryUseContext = (
            HistoryUseContext
            .NARRATIVE_CONTEXT
        ),
    ) -> HistoryAssessment:

        if not records:
            return HistoryAssessment(
                decision=(
                    HistoryEvidenceDecision
                    .RETRIEVE_MORE
                ),
                reasons=(
                    "no_history_evidence",
                ),
            )

        usable: list[
            HistoryEvidenceRecord
        ] = []

        supporting: list[
            HistoryEvidenceRecord
        ] = []

        caution: list[
            HistoryEvidenceRecord
        ] = []

        unresolved = False
        blocked = False

        reasons: list[str] = []

        categorical = (
            use_context
            in {
                HistoryUseContext
                .CATEGORICAL_EVENT_CLAIM,

                HistoryUseContext
                .DISPUTED_HISTORICAL_QUESTION,
            }
        )

        for record in records:

            if not record.text.strip():
                unresolved = True
                reasons.append(
                    "empty_history_evidence"
                )
                continue

            if (
                record.source_family
                is HistorySourceFamily.UNKNOWN
            ):
                unresolved = True
                reasons.append(
                    "official_history_source_family_required"
                )
                continue

            if (
                record.source_family
                is HistorySourceFamily
                .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
            ):
                if not _early_period_verified(
                    record.early_period
                ):
                    unresolved = True
                    reasons.append(
                        "first_three_centuries_period_verification_required"
                    )
                    continue

            if (
                record.source_eligibility
                is HistorySourceEligibility
                .QUARANTINED
            ):
                blocked = True
                reasons.append(
                    "history_source_quarantined"
                )
                continue

            if (
                record.source_eligibility
                is not HistorySourceEligibility
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

            # --------------------------------------------
            # SOURCE-USE MODE GATE
            #
            # A governed source may still be a raw report
            # collection. Source role never establishes
            # event truth by itself.
            # --------------------------------------------

            if (
                record.source_use_mode
                is HistorySourceUseMode.UNKNOWN
            ):
                unresolved = True

                reasons.append(
                    "history_source_use_mode_required"
                )

                continue

            if (
                record.source_use_mode
                is HistorySourceUseMode
                .RAW_REPORT_COLLECTION
            ):
                reasons.append(
                    "raw_report_collection_requires_external_report_assessment_for_fact_promotion"
                )

            # --------------------------------------------
            # Cross-domain boundaries
            # --------------------------------------------

            if (
                record.material_type
                is HistoryMaterialType.QURAN_CONTEXT
            ):
                supporting.append(
                    record
                )

                reasons.append(
                    "quran_context_requires_quran_foundation"
                )

                continue

            if (
                record.material_type
                is HistoryMaterialType.PROPHETIC_REPORT
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
                is HistoryMaterialType.UNKNOWN
            ):
                unresolved = True
                reasons.append(
                    "history_material_type_required"
                )
                continue

            status = (
                record.report_assessment.status
            )

            governed = (
                _report_assessment_is_governed(
                    record.report_assessment
                )
            )

            if (
                status
                is HistoricalReportStatus
                .REJECTED_BY_GOVERNED_AUTHORITY
                and governed
            ):
                blocked = True

                reasons.append(
                    "historical_report_rejected_by_governed_authority"
                )

                continue

            if (
                status
                in {
                    HistoricalReportStatus
                    .DISPUTED_BY_GOVERNED_AUTHORITY,

                    HistoricalReportStatus
                    .REQUIRES_CAUTION_BY_GOVERNED_AUTHORITY,
                }
                and governed
            ):
                caution.append(
                    record
                )

                reasons.append(
                    "historical_report_requires_caution"
                )

                continue

            if (
                status
                in {
                    HistoricalReportStatus
                    .ESTABLISHED_BY_GOVERNED_AUTHORITY,

                    HistoricalReportStatus
                    .CORROBORATED_BY_GOVERNED_AUTHORITY,
                }
                and governed
            ):
                usable.append(
                    record
                )

                continue

            # --------------------------------------------
            # Unassessed report.
            #
            # It may be preserved as a report in narrative
            # context, but not promoted into established fact.
            # --------------------------------------------

            if categorical:
                unresolved = True

                supporting.append(
                    record
                )

                reasons.append(
                    "historical_report_assessment_required_for_categorical_claim"
                )

                continue

            supporting.append(
                record
            )

            reasons.append(
                "historical_report_preserved_without_fact_promotion"
            )

        if usable:
            return HistoryAssessment(
                decision=(
                    HistoryEvidenceDecision.USABLE
                ),
                usable_records=tuple(
                    usable
                ),
                may_state_as_established_fact=True,
                requires_caution_language=False,
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        if caution:
            return HistoryAssessment(
                decision=(
                    HistoryEvidenceDecision
                    .CAUTION_REQUIRED
                ),
                usable_records=tuple(
                    caution
                    + supporting
                ),
                may_state_as_established_fact=False,
                requires_caution_language=True,
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        if blocked and not supporting:
            return HistoryAssessment(
                decision=(
                    HistoryEvidenceDecision.BLOCKED
                ),
                may_state_as_established_fact=False,
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        if unresolved:
            return HistoryAssessment(
                decision=(
                    HistoryEvidenceDecision
                    .RETRIEVE_MORE
                ),
                usable_records=tuple(
                    supporting
                ),
                may_state_as_established_fact=False,
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        if supporting:
            return HistoryAssessment(
                decision=(
                    HistoryEvidenceDecision
                    .SUPPORTING_ONLY
                ),
                usable_records=tuple(
                    supporting
                ),
                may_state_as_established_fact=False,
                reasons=tuple(
                    dict.fromkeys(
                        reasons
                    )
                ),
            )

        return HistoryAssessment(
            decision=(
                HistoryEvidenceDecision
                .RETRIEVE_MORE
            ),
            reasons=(
                "insufficient_history_evidence",
            ),
        )
