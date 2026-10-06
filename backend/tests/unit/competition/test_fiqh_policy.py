from basira.competition.fiqh_policy import (
    FiqhDisagreementState,
    FiqhEvidenceCandidate,
    FiqhEvidenceDecision,
    FiqhPosition,
    FiqhQuestionScope,
    FiqhSourceEligibility,
    FiqhSourceFamily,
    Madhhab,
    OfficialFiqhPolicy,
)


def policy() -> OfficialFiqhPolicy:
    return OfficialFiqhPolicy()


def eligible_dorar_position(
    text: str = "حكم فقهي",
) -> FiqhPosition:
    return FiqhPosition(
        position_text=text,
        source_family=(
            FiqhSourceFamily.DORAR_FIQH
        ),
        source_title=(
            "الموسوعة الفقهية - الدرر السنية"
        ),
        source_reference="feqhia:test",
        source_eligibility=(
            FiqhSourceEligibility.ELIGIBLE
        ),
    )


def test_dorar_family_plus_eligibility_is_usable() -> None:
    result = policy().assess(
        FiqhEvidenceCandidate(
            issue="مسألة فقهية عامة",
            scope=(
                FiqhQuestionScope.GENERAL_FIQH
            ),
            positions=(
                eligible_dorar_position(),
            ),
        )
    )

    assert (
        result.decision
        is FiqhEvidenceDecision
        .USABLE_GENERAL_INFORMATION
    )

    assert result.automated_tarjih_allowed is False


def test_dorar_family_alone_does_not_bypass_governance() -> None:
    result = policy().assess(
        FiqhEvidenceCandidate(
            issue="مسألة",
            scope=(
                FiqhQuestionScope.GENERAL_FIQH
            ),
            positions=(
                FiqhPosition(
                    position_text="قول",
                    source_family=(
                        FiqhSourceFamily.DORAR_FIQH
                    ),
                    source_title="الدرر",
                    source_eligibility=(
                        FiqhSourceEligibility
                        .PENDING_AUDIT
                    ),
                ),
            ),
        )
    )

    assert (
        result.decision
        is FiqhEvidenceDecision.RETRIEVE_MORE
    )

    assert (
        "source_governance_required"
        in result.reasons
    )


def test_madhhab_book_is_allowed_family_when_eligible() -> None:
    result = policy().assess(
        FiqhEvidenceCandidate(
            issue="مسألة",
            scope=(
                FiqhQuestionScope.GENERAL_FIQH
            ),
            positions=(
                FiqhPosition(
                    position_text="قول المذهب",
                    source_family=(
                        FiqhSourceFamily
                        .MADHHAB_FIQH_BOOK
                    ),
                    source_title="كتاب فقهي معتمد",
                    source_reference="1/20",
                    source_eligibility=(
                        FiqhSourceEligibility.ELIGIBLE
                    ),
                    madhhab=Madhhab.HANAFI,
                ),
            ),
        )
    )

    assert (
        result.decision
        is FiqhEvidenceDecision
        .USABLE_GENERAL_INFORMATION
    )


def test_madhhab_book_requires_madhhab_identity() -> None:
    result = policy().assess(
        FiqhEvidenceCandidate(
            issue="مسألة",
            scope=(
                FiqhQuestionScope.GENERAL_FIQH
            ),
            positions=(
                FiqhPosition(
                    position_text="قول",
                    source_family=(
                        FiqhSourceFamily
                        .MADHHAB_FIQH_BOOK
                    ),
                    source_title="كتاب فقهي",
                    source_eligibility=(
                        FiqhSourceEligibility.ELIGIBLE
                    ),
                    madhhab=Madhhab.UNSPECIFIED,
                ),
            ),
        )
    )

    assert (
        result.decision
        is FiqhEvidenceDecision.RETRIEVE_MORE
    )

    assert (
        "official_source_family_required"
        in result.reasons
    )


def test_madhhab_book_pending_audit_is_not_usable() -> None:
    result = policy().assess(
        FiqhEvidenceCandidate(
            issue="مسألة",
            scope=(
                FiqhQuestionScope.GENERAL_FIQH
            ),
            positions=(
                FiqhPosition(
                    position_text="قول",
                    source_family=(
                        FiqhSourceFamily
                        .MADHHAB_FIQH_BOOK
                    ),
                    source_title="كتاب فقهي",
                    source_eligibility=(
                        FiqhSourceEligibility
                        .PENDING_AUDIT
                    ),
                    madhhab=Madhhab.MALIKI,
                ),
            ),
        )
    )

    assert (
        result.decision
        is FiqhEvidenceDecision.RETRIEVE_MORE
    )

    assert (
        "source_governance_required"
        in result.reasons
    )


def test_unknown_fiqh_source_family_is_not_usable() -> None:
    result = policy().assess(
        FiqhEvidenceCandidate(
            issue="مسألة",
            scope=(
                FiqhQuestionScope.GENERAL_FIQH
            ),
            positions=(
                FiqhPosition(
                    position_text="قول",
                    source_family=(
                        FiqhSourceFamily.UNKNOWN
                    ),
                    source_title="مصدر غير معلوم",
                    source_eligibility=(
                        FiqhSourceEligibility.ELIGIBLE
                    ),
                ),
            ),
        )
    )

    assert (
        result.decision
        is FiqhEvidenceDecision.RETRIEVE_MORE
    )

    assert (
        "official_source_family_required"
        in result.reasons
    )


def test_comparative_fiqh_preserves_positions() -> None:
    result = policy().assess(
        FiqhEvidenceCandidate(
            issue="لمس المرأة ونقض الوضوء",
            scope=(
                FiqhQuestionScope.GENERAL_FIQH
            ),
            explicitly_disputed=True,
            positions=(
                FiqhPosition(
                    position_text="قول أول",
                    source_family=(
                        FiqhSourceFamily
                        .MADHHAB_FIQH_BOOK
                    ),
                    source_title="كتاب حنفي",
                    source_eligibility=(
                        FiqhSourceEligibility.ELIGIBLE
                    ),
                    madhhab=Madhhab.HANAFI,
                ),
                FiqhPosition(
                    position_text="قول ثان",
                    source_family=(
                        FiqhSourceFamily
                        .MADHHAB_FIQH_BOOK
                    ),
                    source_title="كتاب شافعي",
                    source_eligibility=(
                        FiqhSourceEligibility.ELIGIBLE
                    ),
                    madhhab=Madhhab.SHAFII,
                ),
            ),
        )
    )

    assert (
        result.decision
        is FiqhEvidenceDecision
        .USABLE_COMPARATIVE
    )

    assert (
        result.disagreement_state
        is FiqhDisagreementState
        .DOCUMENTED_DISAGREEMENT
    )

    assert len(
        result.usable_positions
    ) == 2

    assert result.automated_tarjih_allowed is False
    assert result.majority_vote_allowed is False
    assert result.consensus_inference_allowed is False


def test_personal_case_escalates() -> None:
    result = policy().assess(
        FiqhEvidenceCandidate(
            issue=(
                "حالتي الشخصية في الزواج"
            ),
            scope=(
                FiqhQuestionScope.PERSONAL_CASE
            ),
        )
    )

    assert (
        result.decision
        is FiqhEvidenceDecision
        .ESCALATE_TO_QUALIFIED_SCHOLAR
    )

    assert result.qualified_referral_required is True

    assert (
        result.independent_personal_fatwa_allowed
        is False
    )


def test_no_evidence_retrieves_more() -> None:
    result = policy().assess(
        FiqhEvidenceCandidate(
            issue="مسألة",
            scope=(
                FiqhQuestionScope.GENERAL_FIQH
            ),
        )
    )

    assert (
        result.decision
        is FiqhEvidenceDecision.RETRIEVE_MORE
    )


def test_fiqh_evidence_never_disables_claim_check() -> None:
    result = policy().assess(
        FiqhEvidenceCandidate(
            issue="مسألة",
            scope=(
                FiqhQuestionScope.GENERAL_FIQH
            ),
            positions=(
                eligible_dorar_position(
                    "قول فقهي"
                ),
            ),
        )
    )

    assert result.requires_claim_evidence_check is True
