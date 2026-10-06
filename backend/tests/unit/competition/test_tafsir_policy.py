from basira.competition.tafsir_policy import (
    AttributionStatus,
    EarlyPeriodBasis,
    EarlyPeriodStatus,
    EarlySourcePeriodEvidence,
    NarrationQualityStatus,
    OfficialTafsirPolicy,
    TafsirEvidenceDecision,
    TafsirEvidenceRecord,
    TafsirMaterialType,
    TafsirSourceEligibility,
    TafsirSourceFamily,
    TafsirUseContext,
)


def policy() -> OfficialTafsirPolicy:
    return OfficialTafsirPolicy()


def verified_early_period() -> EarlySourcePeriodEvidence:
    return EarlySourcePeriodEvidence(
        status=EarlyPeriodStatus.VERIFIED,
        basis=EarlyPeriodBasis.WORK_COMPOSITION,
        source_origin_not_after_ah=250,
        author_death_ah=260,
        evidence_ids=(
            "period:evidence:1",
        ),
    )


def test_verified_early_scholarly_explanation_is_usable() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="شرح مبكر للآية",
                source_family=(
                    TafsirSourceFamily
                    .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
                ),
                source_title="مصدر إسلامي مبكر",
                source_reference="1/20",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType
                    .EARLY_SCHOLAR_EXPLANATION
                ),
                early_period=verified_early_period(),
                exact_artifact_governed=True,
            ),
        )
    )

    assert result.decision is TafsirEvidenceDecision.USABLE
    assert result.canonical_quran_text_allowed is False


def test_author_death_year_alone_does_not_prove_early_source() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="نص",
                source_family=(
                    TafsirSourceFamily
                    .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
                ),
                source_title="مصدر",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType
                    .EARLY_SCHOLAR_EXPLANATION
                ),
                early_period=(
                    EarlySourcePeriodEvidence(
                        status=EarlyPeriodStatus.VERIFIED,
                        basis=EarlyPeriodBasis.UNKNOWN,
                        author_death_ah=200,
                        evidence_ids=(
                            "death-year-only",
                        ),
                    )
                ),
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is TafsirEvidenceDecision.RETRIEVE_MORE
    )

    assert (
        "first_three_centuries_period_verification_required"
        in result.reasons
    )


def test_source_after_300_ah_fails_early_family_gate() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="نص",
                source_family=(
                    TafsirSourceFamily
                    .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
                ),
                source_title="مصدر",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType
                    .EARLY_SCHOLAR_EXPLANATION
                ),
                early_period=(
                    EarlySourcePeriodEvidence(
                        status=EarlyPeriodStatus.VERIFIED,
                        basis=(
                            EarlyPeriodBasis.WORK_COMPOSITION
                        ),
                        source_origin_not_after_ah=350,
                        evidence_ids=(
                            "period:evidence:late",
                        ),
                    )
                ),
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is TafsirEvidenceDecision.RETRIEVE_MORE
    )


def test_dorar_tafsir_does_not_need_early_period_gate() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="شرح الآية",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_reference="tafseer:test",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType
                    .SCHOLARLY_REASONING
                ),
                exact_artifact_governed=True,
            ),
        )
    )

    assert result.decision is TafsirEvidenceDecision.USABLE


def test_quran_text_inside_tafsir_is_context_only() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="وَالتِّينِ وَالزَّيْتُونِ",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_reference="tafseer:test",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType.QURAN_TEXT
                ),
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is TafsirEvidenceDecision.CONTEXT_ONLY
    )

    assert result.canonical_quran_text_allowed is False


def test_accepted_prophetic_tafsir_requires_grade_authority() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="رواية تفسيرية",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType.PROPHETIC_TAFSIR
                ),
                attributed_to="النبي صلى الله عليه وسلم",
                attribution_status=(
                    AttributionStatus.VERIFIED_FROM_SOURCE
                ),
                narration_quality=(
                    NarrationQualityStatus
                    .ACCEPTED_BY_AUTHORITY
                ),
                grading_authority="جهة تحقق",
                grade_reference="grade:1",
                exact_artifact_governed=True,
            ),
        )
    )

    assert result.decision is TafsirEvidenceDecision.USABLE


def test_reported_grade_without_provenance_retrieves_more() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="رواية",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType.PROPHETIC_TAFSIR
                ),
                attributed_to="النبي صلى الله عليه وسلم",
                attribution_status=(
                    AttributionStatus.VERIFIED_FROM_SOURCE
                ),
                narration_quality=(
                    NarrationQualityStatus
                    .ACCEPTED_BY_AUTHORITY
                ),
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is TafsirEvidenceDecision.RETRIEVE_MORE
    )


def test_weak_narration_is_context_only_not_primary() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="رواية ضعيفة منقولة",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType.COMPANION_ATHAR
                ),
                attributed_to="صحابي",
                attribution_status=(
                    AttributionStatus.VERIFIED_FROM_SOURCE
                ),
                narration_quality=(
                    NarrationQualityStatus
                    .WEAK_BY_AUTHORITY
                ),
                grading_authority="جهة تحقق",
                grade_reference="grade:weak",
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is TafsirEvidenceDecision.CONTEXT_ONLY
    )


def test_rejected_narration_is_blocked() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="رواية مردودة",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType.PROPHETIC_TAFSIR
                ),
                attributed_to="النبي صلى الله عليه وسلم",
                attribution_status=(
                    AttributionStatus.VERIFIED_FROM_SOURCE
                ),
                narration_quality=(
                    NarrationQualityStatus
                    .REJECTED_BY_AUTHORITY
                ),
                grading_authority="جهة تحقق",
                grade_reference="grade:rejected",
                exact_artifact_governed=True,
            ),
        )
    )

    assert result.decision is TafsirEvidenceDecision.BLOCKED


def test_conflicting_grades_are_preserved_not_collapsed() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="رواية مختلف في درجتها",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType.TABII_ATHAR
                ),
                attributed_to="تابعي",
                attribution_status=(
                    AttributionStatus.VERIFIED_FROM_SOURCE
                ),
                narration_quality=(
                    NarrationQualityStatus
                    .CONFLICTING_AUTHORITY_GRADES
                ),
                grading_authority="عدة جهات",
                grade_reference="grades:conflict",
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is TafsirEvidenceDecision.RETRIEVE_MORE
    )

    assert (
        "conflicting_narration_grades_preserved"
        in result.reasons
    )


def test_ungraded_narration_is_not_called_weak() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="أثر غير مصنف",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType.COMPANION_ATHAR
                ),
                attributed_to="صحابي",
                attribution_status=(
                    AttributionStatus.VERIFIED_FROM_SOURCE
                ),
                narration_quality=(
                    NarrationQualityStatus.UNGRADED
                ),
                exact_artifact_governed=True,
            ),
        )
    )

    assert (
        result.decision
        is TafsirEvidenceDecision.SUPPORTING_ONLY
    )

    assert (
        "ungraded_narration_supporting_only"
        in result.reasons
    )


def test_scholarly_reasoning_does_not_require_hadith_grade() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="استنباط أو شرح علمي",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType.SCHOLARLY_REASONING
                ),
                narration_quality=(
                    NarrationQualityStatus.NOT_APPLICABLE
                ),
                exact_artifact_governed=True,
            ),
        )
    )

    assert result.decision is TafsirEvidenceDecision.USABLE


def test_tafsir_cannot_directly_establish_fiqh_ruling() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="شرح فقهي للآية",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType.SCHOLARLY_REASONING
                ),
                exact_artifact_governed=True,
            ),
        ),
        use_context=(
            TafsirUseContext.SUPPORT_FIQH_RULING
        ),
    )

    assert (
        result.decision
        is TafsirEvidenceDecision.RETRIEVE_MORE
    )

    assert result.may_directly_establish_fiqh_ruling is False

    assert (
        "route_to_fiqh_and_hadith_evidence"
        in result.reasons
    )


def test_asbab_boundary_is_preserved() -> None:
    result = policy().assess(
        (
            TafsirEvidenceRecord(
                text="سبب نزول منقول",
                source_family=(
                    TafsirSourceFamily.DORAR_TAFSIR
                ),
                source_title="موسوعة التفسير",
                source_eligibility=(
                    TafsirSourceEligibility.ELIGIBLE
                ),
                material_type=(
                    TafsirMaterialType.ASBAB_AL_NUZUL
                ),
                attributed_to="راو",
                attribution_status=(
                    AttributionStatus.VERIFIED_FROM_SOURCE
                ),
                narration_quality=(
                    NarrationQualityStatus.UNGRADED
                ),
                exact_artifact_governed=True,
            ),
        )
    )

    assert result.preserve_asbab_boundary is True
