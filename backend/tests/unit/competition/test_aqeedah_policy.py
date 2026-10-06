from basira.competition.aqeedah_authority import (
    AqeedahAuthorityBasis,
    AqeedahAuthorityEvidence,
    AqeedahAuthorityStatus,
)

from basira.competition.aqeedah_policy import (
    AqeedahEarlyPeriodBasis,
    AqeedahEarlyPeriodEvidence,
    AqeedahEarlyPeriodStatus,
    AqeedahEvidenceDecision,
    AqeedahEvidenceRecord,
    AqeedahMaterialType,
    AqeedahSourceEligibility,
    AqeedahSourceFamily,
    AqeedahUseContext,
    OfficialAqeedahPolicy,
)


def policy() -> OfficialAqeedahPolicy:
    return OfficialAqeedahPolicy()


def early_period() -> AqeedahEarlyPeriodEvidence:
    return AqeedahEarlyPeriodEvidence(
        status=(
            AqeedahEarlyPeriodStatus.VERIFIED
        ),
        basis=(
            AqeedahEarlyPeriodBasis
            .WORK_COMPOSITION
        ),
        source_origin_not_after_ah=250,
        author_death_ah=260,
        evidence_ids=(
            "aqeedah:period:1",
        ),
    )


def early_record(
    *,
    material_type: AqeedahMaterialType = (
        AqeedahMaterialType
        .EARLY_SCHOLAR_STATEMENT
    ),
) -> AqeedahEvidenceRecord:

    return AqeedahEvidenceRecord(
        text="بيان عقدي مبكر",
        source_family=(
            AqeedahSourceFamily
            .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
        ),
        source_title="مصدر إسلامي مبكر",
        source_reference="1/10",
        source_eligibility=(
            AqeedahSourceEligibility.ELIGIBLE
        ),
        material_type=material_type,
        early_period=early_period(),
        authority=AqeedahAuthorityEvidence(
            status=(
                AqeedahAuthorityStatus
                .VERIFIED_PRIMARY
            ),
            basis=(
                AqeedahAuthorityBasis
                .MANUAL_SCHOLARLY_AUDIT
            ),
            evidence_ids=(
                "aqeedah:authority:test-primary",
            ),
        ),
        source_identity_verified=True,
        exact_artifact_governed=True,
    )


def test_verified_early_source_is_usable() -> None:
    result = policy().assess(
        (
            early_record(),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision.USABLE
    )

    assert result.may_claim_consensus is False

    assert (
        result.may_use_generic_shamela_fallback
        is False
    )


def test_author_death_year_alone_is_not_enough() -> None:
    result = policy().assess(
        (
            AqeedahEvidenceRecord(
                text="نص",
                source_family=(
                    AqeedahSourceFamily
                    .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
                ),
                source_title="مصدر",
                source_eligibility=(
                    AqeedahSourceEligibility
                    .ELIGIBLE
                ),
                material_type=(
                    AqeedahMaterialType
                    .EARLY_SCHOLAR_STATEMENT
                ),
                early_period=(
                    AqeedahEarlyPeriodEvidence(
                        status=(
                            AqeedahEarlyPeriodStatus
                            .VERIFIED
                        ),
                        basis=(
                            AqeedahEarlyPeriodBasis
                            .UNKNOWN
                        ),
                        author_death_ah=180,
                        evidence_ids=(
                            "death-only",
                        ),
                    )
                ),
                source_identity_verified=True,
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        "first_three_centuries_period_verification_required"
        in result.reasons
    )


def test_source_origin_after_300_ah_fails_early_gate() -> None:
    result = policy().assess(
        (
            AqeedahEvidenceRecord(
                text="نص متأخر",
                source_family=(
                    AqeedahSourceFamily
                    .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
                ),
                source_title="مصدر",
                source_eligibility=(
                    AqeedahSourceEligibility
                    .ELIGIBLE
                ),
                material_type=(
                    AqeedahMaterialType
                    .SCHOLARLY_EXPLANATION
                ),
                early_period=(
                    AqeedahEarlyPeriodEvidence(
                        status=(
                            AqeedahEarlyPeriodStatus
                            .VERIFIED
                        ),
                        basis=(
                            AqeedahEarlyPeriodBasis
                            .WORK_COMPOSITION
                        ),
                        source_origin_not_after_ah=350,
                        evidence_ids=(
                            "late-source",
                        ),
                    )
                ),
                source_identity_verified=True,
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision
        .RETRIEVE_MORE
    )


def test_dorar_family_does_not_need_early_period_evidence() -> None:
    result = policy().assess(
        (
            AqeedahEvidenceRecord(
                text="تعريف بالتوحيد",
                source_family=(
                    AqeedahSourceFamily
                    .DORAR_AQEEDA
                ),
                source_title=(
                    "الموسوعة العقدية"
                ),
                source_reference=(
                    "aqeeda:test"
                ),
                source_eligibility=(
                    AqeedahSourceEligibility
                    .ELIGIBLE
                ),
                material_type=(
                    AqeedahMaterialType
                    .BASIC_ISLAMIC_BELIEF
                ),
                source_identity_verified=True,
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision.USABLE
    )


def test_pending_dorar_source_is_not_runtime_usable() -> None:
    result = policy().assess(
        (
            AqeedahEvidenceRecord(
                text="تعريف",
                source_family=(
                    AqeedahSourceFamily
                    .DORAR_AQEEDA
                ),
                source_title=(
                    "الموسوعة العقدية"
                ),
                source_eligibility=(
                    AqeedahSourceEligibility
                    .PENDING_AUDIT
                ),
                material_type=(
                    AqeedahMaterialType
                    .BASIC_ISLAMIC_BELIEF
                ),
                source_identity_verified=True,
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        "runtime_source_eligibility_required"
        in result.reasons
    )


def test_quran_quote_requires_quran_foundation() -> None:
    record = early_record(
        material_type=(
            AqeedahMaterialType.QURAN_TEXT
        )
    )

    result = policy().assess(
        (
            record,
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision
        .SUPPORTING_ONLY
    )

    assert (
        result.quran_must_use_canonical_quran_foundation
        is True
    )

    assert (
        "quran_text_requires_canonical_quran_foundation"
        in result.reasons
    )


def test_prophetic_report_routes_to_hadith_foundation() -> None:
    record = early_record(
        material_type=(
            AqeedahMaterialType
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
        is AqeedahEvidenceDecision
        .SUPPORTING_ONLY
    )

    assert (
        result.prophetic_report_must_use_hadith_foundation
        is True
    )

    assert (
        "prophetic_report_requires_hadith_foundation"
        in result.reasons
    )


def test_companion_athar_requires_attribution() -> None:
    record = early_record(
        material_type=(
            AqeedahMaterialType
            .COMPANION_ATHAR
        )
    )

    result = policy().assess(
        (
            record,
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        "athar_attribution_required"
        in result.reasons
    )


def test_detailed_aqeedah_issue_requires_disagreement_check() -> None:
    result = policy().assess(
        (
            early_record(),
        ),
        use_context=(
            AqeedahUseContext
            .DETAILED_AQEEDAH_ISSUE
        ),
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision.USABLE
    )

    assert (
        result.requires_disagreement_check
        is True
    )

    assert result.may_claim_consensus is False


def test_source_count_never_proves_consensus() -> None:
    result = policy().assess(
        (
            early_record(),
            early_record(),
            early_record(),
        ),
        use_context=(
            AqeedahUseContext
            .DETAILED_AQEEDAH_ISSUE
        ),
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision.USABLE
    )

    assert result.may_claim_consensus is False


def test_unknown_source_family_is_not_usable() -> None:
    result = policy().assess(
        (
            AqeedahEvidenceRecord(
                text="نص",
                source_family=(
                    AqeedahSourceFamily.UNKNOWN
                ),
                source_title="كتاب غير محكوم",
                source_eligibility=(
                    AqeedahSourceEligibility
                    .ELIGIBLE
                ),
                material_type=(
                    AqeedahMaterialType
                    .SCHOLARLY_EXPLANATION
                ),
                source_identity_verified=True,
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision
        .RETRIEVE_MORE
    )


def test_exact_artifact_governance_is_required() -> None:
    result = policy().assess(
        (
            AqeedahEvidenceRecord(
                text="نص",
                source_family=(
                    AqeedahSourceFamily
                    .DORAR_AQEEDA
                ),
                source_title=(
                    "الموسوعة العقدية"
                ),
                source_eligibility=(
                    AqeedahSourceEligibility
                    .ELIGIBLE
                ),
                material_type=(
                    AqeedahMaterialType
                    .BASIC_ISLAMIC_BELIEF
                ),
                source_identity_verified=True,
                exact_artifact_governed=False,
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision
        .RETRIEVE_MORE
    )

    assert (
        "exact_artifact_governance_required"
        in result.reasons
    )
