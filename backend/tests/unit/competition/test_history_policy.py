from basira.competition.history_policy import (
    HistoricalAssessmentBasis,
    HistoricalReportAssessment,
    HistoricalReportStatus,
    HistoryEarlyPeriodBasis,
    HistoryEarlyPeriodEvidence,
    HistoryEarlyPeriodStatus,
    HistoryEvidenceDecision,
    HistoryEvidenceRecord,
    HistoryMaterialType,
    HistorySourceEligibility,
    HistorySourceFamily,
    HistorySourceUseMode,
    HistoryUseContext,
    OfficialHistoryPolicy,
)


def policy() -> OfficialHistoryPolicy:
    return OfficialHistoryPolicy()


def early_period():
    return HistoryEarlyPeriodEvidence(
        status=(
            HistoryEarlyPeriodStatus.VERIFIED
        ),
        basis=(
            HistoryEarlyPeriodBasis
            .WORK_COMPOSITION
        ),
        source_origin_not_after_ah=220,
        author_death_ah=240,
        evidence_ids=(
            "history:period:test",
        ),
    )


def established():
    return HistoricalReportAssessment(
        status=(
            HistoricalReportStatus
            .ESTABLISHED_BY_GOVERNED_AUTHORITY
        ),
        basis=(
            HistoricalAssessmentBasis
            .MANUAL_SCHOLARLY_AUDIT
        ),
        authority_name=(
            "governed-test-authority"
        ),
        evidence_ids=(
            "history:assessment:established",
        ),
    )


def disputed():
    return HistoricalReportAssessment(
        status=(
            HistoricalReportStatus
            .DISPUTED_BY_GOVERNED_AUTHORITY
        ),
        basis=(
            HistoricalAssessmentBasis
            .MANUAL_SCHOLARLY_AUDIT
        ),
        authority_name=(
            "governed-test-authority"
        ),
        evidence_ids=(
            "history:assessment:disputed",
        ),
    )


def early_record(
    *,
    assessment=None,
    material_type=(
        HistoryMaterialType
        .HISTORICAL_EVENT_REPORT
    ),
):
    return HistoryEvidenceRecord(
        text="خبر تاريخي مبكر",
        source_family=(
            HistorySourceFamily
            .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
        ),
        source_title="مصدر تاريخي مبكر",
        source_reference="1/10",
        source_eligibility=(
            HistorySourceEligibility.ELIGIBLE
        ),
        material_type=material_type,
        source_use_mode=(
            HistorySourceUseMode
            .PRIMARY_HISTORICAL_NARRATIVE
        ),
        early_period=early_period(),
        report_assessment=(
            assessment
            if assessment is not None
            else HistoricalReportAssessment()
        ),
        source_identity_verified=True,
        exact_artifact_governed=True,
    )


def test_early_source_does_not_equal_verified_event() -> None:
    result = policy().assess(
        (
            early_record(),
        ),
        use_context=(
            HistoryUseContext
            .CATEGORICAL_EVENT_CLAIM
        ),
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        result.may_state_as_established_fact
        is False
    )


def test_unassessed_report_can_be_preserved_as_report_only() -> None:
    result = policy().assess(
        (
            early_record(),
        ),
        use_context=(
            HistoryUseContext.NARRATIVE_CONTEXT
        ),
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .SUPPORTING_ONLY
    )

    assert (
        result.may_state_as_established_fact
        is False
    )


def test_governed_established_event_is_usable() -> None:
    result = policy().assess(
        (
            early_record(
                assessment=established(),
            ),
        ),
        use_context=(
            HistoryUseContext
            .CATEGORICAL_EVENT_CLAIM
        ),
    )

    assert (
        result.decision
        is HistoryEvidenceDecision.USABLE
    )

    assert (
        result.may_state_as_established_fact
        is True
    )


def test_disputed_report_preserves_caution() -> None:
    result = policy().assess(
        (
            early_record(
                assessment=disputed(),
            ),
        ),
        use_context=(
            HistoryUseContext
            .DISPUTED_HISTORICAL_QUESTION
        ),
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .CAUTION_REQUIRED
    )

    assert (
        result.may_state_as_established_fact
        is False
    )

    assert result.requires_caution_language is True


def test_multiple_unassessed_reports_do_not_create_corroboration() -> None:
    result = policy().assess(
        (
            early_record(),
            early_record(),
            early_record(),
        ),
        use_context=(
            HistoryUseContext
            .CATEGORICAL_EVENT_CLAIM
        ),
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        result.may_infer_corrobation_from_count
        is False
    )

    assert (
        result.may_infer_consensus_from_count
        is False
    )

    assert (
        result.may_state_as_established_fact
        is False
    )


def test_author_death_year_alone_does_not_prove_early_source() -> None:
    record = early_record()

    record.early_period = (
        HistoryEarlyPeriodEvidence(
            status=(
                HistoryEarlyPeriodStatus.VERIFIED
            ),
            basis=(
                HistoryEarlyPeriodBasis.UNKNOWN
            ),
            author_death_ah=180,
            evidence_ids=(
                "death-only",
            ),
        )
    )

    result = policy().assess(
        (
            record,
        )
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .RETRIEVE_MORE
    )


def test_source_after_300_ah_fails_early_source_gate() -> None:
    record = early_record()

    record.early_period = (
        HistoryEarlyPeriodEvidence(
            status=(
                HistoryEarlyPeriodStatus.VERIFIED
            ),
            basis=(
                HistoryEarlyPeriodBasis
                .WORK_COMPOSITION
            ),
            source_origin_not_after_ah=350,
            evidence_ids=(
                "late-source",
            ),
        )
    )

    result = policy().assess(
        (
            record,
        )
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .RETRIEVE_MORE
    )


def test_dorar_history_does_not_require_early_period_proof() -> None:
    record = HistoryEvidenceRecord(
        text="مادة تاريخية من الموسوعة",
        source_family=(
            HistorySourceFamily.DORAR_HISTORY
        ),
        source_title=(
            "الموسوعة التاريخية"
        ),
        source_reference="history:test",
        source_eligibility=(
            HistorySourceEligibility.ELIGIBLE
        ),
        material_type=(
            HistoryMaterialType
            .HISTORICAL_EVENT_REPORT
        ),
        source_use_mode=(
            HistorySourceUseMode
            .CURATED_HISTORY_REFERENCE
        ),
        report_assessment=established(),
        source_identity_verified=True,
        exact_artifact_governed=True,
    )

    result = policy().assess(
        (
            record,
        ),
        use_context=(
            HistoryUseContext
            .CATEGORICAL_EVENT_CLAIM
        ),
    )

    assert (
        result.decision
        is HistoryEvidenceDecision.USABLE
    )


def test_pending_dorar_history_is_not_runtime_usable() -> None:
    record = HistoryEvidenceRecord(
        text="مادة تاريخية",
        source_family=(
            HistorySourceFamily.DORAR_HISTORY
        ),
        source_title=(
            "الموسوعة التاريخية"
        ),
        source_eligibility=(
            HistorySourceEligibility.PENDING_AUDIT
        ),
        material_type=(
            HistoryMaterialType
            .HISTORICAL_EVENT_REPORT
        ),
        source_use_mode=(
            HistorySourceUseMode
            .CURATED_HISTORY_REFERENCE
        ),
        report_assessment=established(),
        source_identity_verified=True,
        exact_artifact_governed=True,
    )

    result = policy().assess(
        (
            record,
        )
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .RETRIEVE_MORE
    )


def test_quran_context_routes_to_quran_foundation() -> None:
    record = early_record(
        material_type=(
            HistoryMaterialType.QURAN_CONTEXT
        )
    )

    result = policy().assess(
        (
            record,
        )
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .SUPPORTING_ONLY
    )

    assert (
        result.quran_must_use_canonical_quran_foundation
        is True
    )


def test_prophetic_report_routes_to_hadith_foundation() -> None:
    record = early_record(
        material_type=(
            HistoryMaterialType
            .PROPHETIC_REPORT
        )
    )

    result = policy().assess(
        (
            record,
        )
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .SUPPORTING_ONLY
    )

    assert (
        result.prophetic_report_must_use_hadith_foundation
        is True
    )


def test_generic_shamela_fallback_is_prohibited() -> None:
    result = policy().assess(
        (
            early_record(),
        )
    )

    assert (
        result.may_use_generic_shamela_fallback
        is False
    )


def test_history_source_use_mode_is_required() -> None:
    record = early_record()

    record.source_use_mode = (
        HistorySourceUseMode.UNKNOWN
    )

    result = policy().assess(
        (
            record,
        )
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        "history_source_use_mode_required"
        in result.reasons
    )


def test_raw_report_collection_does_not_establish_fact_by_itself() -> None:
    record = early_record()

    record.source_use_mode = (
        HistorySourceUseMode
        .RAW_REPORT_COLLECTION
    )

    result = policy().assess(
        (
            record,
        ),
        use_context=(
            HistoryUseContext
            .CATEGORICAL_EVENT_CLAIM
        ),
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        result.may_state_as_established_fact
        is False
    )

    assert (
        result
        .source_use_mode_alone_may_establish_event
        is False
    )

    assert (
        "raw_report_collection_requires_external_report_assessment_for_fact_promotion"
        in result.reasons
    )


def test_raw_collection_can_be_used_after_external_governed_assessment() -> None:
    record = early_record(
        assessment=established(),
    )

    record.source_use_mode = (
        HistorySourceUseMode
        .RAW_REPORT_COLLECTION
    )

    result = policy().assess(
        (
            record,
        ),
        use_context=(
            HistoryUseContext
            .CATEGORICAL_EVENT_CLAIM
        ),
    )

    assert (
        result.decision
        is HistoryEvidenceDecision.USABLE
    )

    assert (
        result.may_state_as_established_fact
        is True
    )

    # The FACT state came from governed report assessment,
    # not from RAW_REPORT_COLLECTION itself.
    assert (
        result
        .source_use_mode_alone_may_establish_event
        is False
    )


def test_curated_source_still_does_not_establish_unassessed_event() -> None:
    record = early_record()

    record.source_use_mode = (
        HistorySourceUseMode
        .CURATED_HISTORY_REFERENCE
    )

    result = policy().assess(
        (
            record,
        ),
        use_context=(
            HistoryUseContext
            .CATEGORICAL_EVENT_CLAIM
        ),
    )

    assert (
        result.decision
        is HistoryEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        result.may_state_as_established_fact
        is False
    )
