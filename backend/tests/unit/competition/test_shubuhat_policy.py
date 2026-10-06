from basira.competition.shubuhat_policy import (
    BayyinatSourceState,
    OfficialShubuhatPolicy,
    ShubuhatClaim,
    ShubuhatClaimDecision,
    ShubuhatClaimDomain,
    ShubuhatClaimRole,
    ShubuhatOverallDecision,
    ShubuhatQuestionMode,
    ShubuhatSourceEligibility,
)


def policy():
    return OfficialShubuhatPolicy()


def pending_bayyinat():
    return BayyinatSourceState()


def eligible_bayyinat():
    return BayyinatSourceState(
        eligibility=(
            ShubuhatSourceEligibility
            .ELIGIBLE
        ),
        exact_artifact_governed=True,
        source_identity_verified=True,
    )


def claim(
    domain,
    *,
    role=(
        ShubuhatClaimRole
        .EVIDENTIARY_CLAIM
    ),
    claim_id="c1",
    text="ادعاء اختباري",
    consensus=False,
):
    return ShubuhatClaim(
        claim_id=claim_id,
        text=text,
        role=role,
        domain=domain,
        asserts_consensus=consensus,
    )


def test_claim_decomposition_is_required() -> None:
    result = policy().assess(
        claims=(),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=pending_bayyinat(),
    )

    assert (
        result.decision
        is ShubuhatOverallDecision
        .RETRIEVE_MORE
    )

    assert (
        result.claim_decomposition_required
        is True
    )


def test_bayyinat_is_conversational_not_universal_evidence() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain
                .QURAN
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .SHUBHAH_OBJECTION
        ),
        bayyinat=pending_bayyinat(),
    )

    plan = result.claim_plans[0]

    assert (
        plan.decision
        is ShubuhatClaimDecision
        .ROUTE_TO_PRIMARY_DOMAIN
    )

    assert (
        plan.primary_evidence_domain
        is ShubuhatClaimDomain.QURAN
    )

    assert (
        plan.bayyinat_may_structure_claim
        is True
    )

    assert (
        plan.bayyinat_may_be_primary_evidence
        is False
    )


def test_quran_claim_routes_to_quran() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.QURAN
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=pending_bayyinat(),
    )

    assert (
        result.claim_plans[0]
        .primary_evidence_domain
        is ShubuhatClaimDomain.QURAN
    )


def test_tafsir_claim_routes_to_tafsir() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.TAFSIR
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=pending_bayyinat(),
    )

    assert (
        result.claim_plans[0]
        .primary_evidence_domain
        is ShubuhatClaimDomain.TAFSIR
    )


def test_hadith_claim_routes_to_hadith() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.HADITH
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=pending_bayyinat(),
    )

    assert (
        result.claim_plans[0]
        .primary_evidence_domain
        is ShubuhatClaimDomain.HADITH
    )


def test_aqeedah_claim_routes_to_aqeedah() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.AQEEDAH
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=pending_bayyinat(),
    )

    assert (
        result.claim_plans[0]
        .primary_evidence_domain
        is ShubuhatClaimDomain.AQEEDAH
    )


def test_fiqh_claim_routes_to_fiqh() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.FIQH
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=pending_bayyinat(),
    )

    assert (
        result.claim_plans[0]
        .primary_evidence_domain
        is ShubuhatClaimDomain.FIQH
    )


def test_history_claim_routes_to_history() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.HISTORY
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=pending_bayyinat(),
    )

    assert (
        result.claim_plans[0]
        .primary_evidence_domain
        is ShubuhatClaimDomain.HISTORY
    )


def test_cross_domain_claim_requires_primary_evidence() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.QURAN,
                claim_id="q",
            ),
            claim(
                ShubuhatClaimDomain.HISTORY,
                claim_id="h",
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .SHUBHAH_OBJECTION
        ),
        bayyinat=eligible_bayyinat(),
    )

    assert (
        result.decision
        is ShubuhatOverallDecision
        .PRIMARY_EVIDENCE_REQUIRED
    )


def test_bayyinat_conversational_material_needs_runtime_eligibility() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain
                .BAYYINAT_CONVERSATIONAL,
                role=(
                    ShubuhatClaimRole
                    .CONVERSATIONAL_FRAMING
                ),
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=pending_bayyinat(),
    )

    assert (
        result.decision
        is ShubuhatOverallDecision
        .RETRIEVE_MORE
    )

    assert (
        result.claim_plans[0]
        .decision
        is ShubuhatClaimDecision
        .RETRIEVE_MORE
    )


def test_eligible_bayyinat_may_supply_conversational_framing() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain
                .BAYYINAT_CONVERSATIONAL,
                role=(
                    ShubuhatClaimRole
                    .CONVERSATIONAL_FRAMING
                ),
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=eligible_bayyinat(),
    )

    assert (
        result.decision
        is ShubuhatOverallDecision
        .READY_FOR_CONVERSATIONAL_DRAFT
    )

    assert (
        result.claim_plans[0]
        .decision
        is ShubuhatClaimDecision
        .USE_CONVERSATIONALLY
    )

    assert (
        result.claim_plans[0]
        .bayyinat_may_be_primary_evidence
        is False
    )


def test_bayyinat_conversational_domain_cannot_carry_evidentiary_claim() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain
                .BAYYINAT_CONVERSATIONAL,
                role=(
                    ShubuhatClaimRole
                    .EVIDENTIARY_CLAIM
                ),
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=eligible_bayyinat(),
    )

    assert (
        result.decision
        is ShubuhatOverallDecision
        .BLOCKED
    )


def test_bayyinat_wording_cannot_establish_consensus() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.FIQH,
                consensus=True,
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=eligible_bayyinat(),
    )

    plan = result.claim_plans[0]

    assert (
        plan.may_state_consensus_from_bayyinat
        is False
    )

    assert (
        "consensus_requires_primary_domain_support"
        in plan.reasons
    )

    assert (
        result.false_consensus_inference_allowed
        is False
    )


def test_hostile_question_does_not_authorize_hostile_response() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.AQEEDAH
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .HOSTILE_FORMULATION
        ),
        bayyinat=eligible_bayyinat(),
    )

    assert (
        result.hostile_question_authorizes_hostile_response
        is False
    )

    assert (
        result.response_must_remain_civil_and_wise
        is True
    )

    assert (
        "hostile_wording_does_not_change_response_ethics"
        in result.reasons
    )


def test_personal_fatwa_escalates() -> None:
    personal = ShubuhatClaim(
        claim_id="personal",
        text=(
            "ما الحكم في زواجي أنا؟"
        ),
        role=(
            ShubuhatClaimRole
            .PERSONAL_RULING_REQUEST
        ),
        domain=(
            ShubuhatClaimDomain.FIQH
        ),
        personal_case_specific=True,
    )

    result = policy().assess(
        claims=(
            personal,
        ),
        question_mode=(
            ShubuhatQuestionMode
            .PERSONAL_CASE
        ),
        bayyinat=eligible_bayyinat(),
    )

    assert (
        result.decision
        is ShubuhatOverallDecision
        .ESCALATE
    )

    assert (
        result.personal_fatwa_allowed
        is False
    )

    assert (
        result.claim_plans[0]
        .may_make_personal_ruling
        is False
    )


def test_unknown_claim_domain_retrieves_more() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.UNKNOWN
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=eligible_bayyinat(),
    )

    assert (
        result.decision
        is ShubuhatOverallDecision
        .RETRIEVE_MORE
    )


def test_generic_shamela_and_web_cannot_replace_primary_domain() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.HADITH
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=eligible_bayyinat(),
    )

    assert (
        result.generic_shamela_fallback_allowed
        is False
    )

    assert (
        result
        .generic_web_fallback_may_replace_primary_domain
        is False
    )


def test_answer_wording_cannot_infer_source_role() -> None:
    result = policy().assess(
        claims=(
            claim(
                ShubuhatClaimDomain.QURAN
            ),
        ),
        question_mode=(
            ShubuhatQuestionMode
            .GENERAL_FAQ
        ),
        bayyinat=eligible_bayyinat(),
    )

    assert (
        result
        .source_role_may_be_inferred_from_answer_wording
        is False
    )
