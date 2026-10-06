from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ShubuhatSourceFamily(StrEnum):
    BAYYINAT = "bayyinat"

    UNKNOWN = "unknown"


class ShubuhatSourceEligibility(StrEnum):
    ELIGIBLE = "eligible"

    PENDING_AUDIT = "pending_audit"

    QUARANTINED = "quarantined"

    UNKNOWN = "unknown"


class ShubuhatQuestionMode(StrEnum):
    GENERAL_FAQ = "general_faq"

    SHUBHAH_OBJECTION = "shubhah_objection"

    COMPARATIVE_QUESTION = (
        "comparative_question"
    )

    HOSTILE_FORMULATION = (
        "hostile_formulation"
    )

    PERSONAL_CASE = "personal_case"


class ShubuhatClaimRole(StrEnum):
    """
    What role does the claim play in the answer?
    """

    CONVERSATIONAL_FRAMING = (
        "conversational_framing"
    )

    EXPLANATORY_STRUCTURE = (
        "explanatory_structure"
    )

    EVIDENTIARY_CLAIM = (
        "evidentiary_claim"
    )

    DIRECT_QUOTATION = (
        "direct_quotation"
    )

    PERSONAL_RULING_REQUEST = (
        "personal_ruling_request"
    )


class ShubuhatClaimDomain(StrEnum):
    """
    Domain ownership for evidentiary verification.

    BAYYINAT_CONVERSATIONAL is intentionally not a
    substitute for Quran/Hadith/Fiqh/etc.
    """

    BAYYINAT_CONVERSATIONAL = (
        "bayyinat_conversational"
    )

    QURAN = "quran"

    TAFSIR = "tafsir"

    HADITH = "hadith"

    AQEEDAH = "aqeedah_intro_to_islam"

    FIQH = "general_fiqh"

    HISTORY = "seerah_history"

    TERMINOLOGY = (
        "translation_terminology"
    )

    DAWAH_GENERAL = (
        "dawah_general_content"
    )

    UNKNOWN = "unknown"


class ShubuhatClaimDecision(StrEnum):
    USE_CONVERSATIONALLY = (
        "use_conversationally"
    )

    ROUTE_TO_PRIMARY_DOMAIN = (
        "route_to_primary_domain"
    )

    RETRIEVE_MORE = "retrieve_more"

    ESCALATE = "escalate"

    BLOCKED = "blocked"


class ShubuhatOverallDecision(StrEnum):
    READY_FOR_CONVERSATIONAL_DRAFT = (
        "ready_for_conversational_draft"
    )

    PRIMARY_EVIDENCE_REQUIRED = (
        "primary_evidence_required"
    )

    RETRIEVE_MORE = "retrieve_more"

    ESCALATE = "escalate"

    BLOCKED = "blocked"


class ShubuhatClaim(BaseModel):
    claim_id: str

    text: str

    role: ShubuhatClaimRole

    domain: ShubuhatClaimDomain

    asserts_consensus: bool = False

    personal_case_specific: bool = False

    notes: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


class BayyinatSourceState(BaseModel):
    source_family: ShubuhatSourceFamily = (
        ShubuhatSourceFamily.BAYYINAT
    )

    eligibility: ShubuhatSourceEligibility = (
        ShubuhatSourceEligibility.PENDING_AUDIT
    )

    exact_artifact_governed: bool = False

    source_identity_verified: bool = False


class ShubuhatClaimPlan(BaseModel):
    claim_id: str

    decision: ShubuhatClaimDecision

    primary_evidence_domain: (
        ShubuhatClaimDomain | None
    ) = None

    bayyinat_may_structure_claim: bool = True

    bayyinat_may_be_primary_evidence: bool = False

    may_state_consensus_from_bayyinat: bool = False

    may_make_personal_ruling: bool = False

    reasons: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


class ShubuhatAssessment(BaseModel):
    decision: ShubuhatOverallDecision

    claim_plans: tuple[
        ShubuhatClaimPlan,
        ...
    ] = Field(
        default_factory=tuple
    )

    claim_decomposition_required: bool = True

    bayyinat_is_primary_conversational_source: bool = True

    bayyinat_is_universal_primary_evidence: bool = False

    source_role_may_be_inferred_from_answer_wording: bool = False

    false_consensus_inference_allowed: bool = False

    hostile_question_authorizes_hostile_response: bool = False

    response_must_remain_civil_and_wise: bool = True

    personal_fatwa_allowed: bool = False

    generic_shamela_fallback_allowed: bool = False

    generic_web_fallback_may_replace_primary_domain: bool = False

    reasons: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


_PRIMARY_EVIDENCE_DOMAINS = {
    ShubuhatClaimDomain.QURAN,
    ShubuhatClaimDomain.TAFSIR,
    ShubuhatClaimDomain.HADITH,
    ShubuhatClaimDomain.AQEEDAH,
    ShubuhatClaimDomain.FIQH,
    ShubuhatClaimDomain.HISTORY,
    ShubuhatClaimDomain.TERMINOLOGY,
    ShubuhatClaimDomain.DAWAH_GENERAL,
}


def _bayyinat_runtime_ready(
    state: BayyinatSourceState,
) -> bool:

    return (
        state.source_family
        is ShubuhatSourceFamily.BAYYINAT
        and state.eligibility
        is ShubuhatSourceEligibility.ELIGIBLE
        and state.exact_artifact_governed
        and state.source_identity_verified
    )


class OfficialShubuhatPolicy:
    """
    Official Shubuhat / FAQ policy.

    Core invariants:

    BAYYINAT
        = PRIMARY CONVERSATIONAL SOURCE

    BAYYINAT
        != UNIVERSAL PRIMARY EVIDENCE

    CONVERSATIONAL FRAMING
        != EVIDENTIARY AUTHORITY

    SOURCE WORDING
        != CONSENSUS

    HOSTILE QUESTION
        != HOSTILE RESPONSE LICENSE

    PERSONAL FATWA
        != SHUBUHAT ANSWER

    CROSS-DOMAIN CLAIM
        -> PRIMARY GOVERNED DOMAIN

    GENERIC SHAMELA / WEB SEARCH
        != PRIMARY DOMAIN REPLACEMENT
    """

    def assess(
        self,
        *,
        claims: tuple[
            ShubuhatClaim,
            ...
        ],
        question_mode: ShubuhatQuestionMode,
        bayyinat: BayyinatSourceState,
    ) -> ShubuhatAssessment:

        if not claims:

            return ShubuhatAssessment(
                decision=(
                    ShubuhatOverallDecision
                    .RETRIEVE_MORE
                ),
                reasons=(
                    "claim_decomposition_required",
                ),
            )

        plans: list[
            ShubuhatClaimPlan
        ] = []

        overall_reasons: list[str] = []

        has_primary_route = False
        has_retrieve_more = False
        has_escalation = False
        has_block = False

        bayyinat_ready = (
            _bayyinat_runtime_ready(
                bayyinat
            )
        )

        for claim in claims:

            text = claim.text.strip()

            if not text:

                has_retrieve_more = True

                plans.append(
                    ShubuhatClaimPlan(
                        claim_id=claim.claim_id,
                        decision=(
                            ShubuhatClaimDecision
                            .RETRIEVE_MORE
                        ),
                        reasons=(
                            "empty_claim",
                        ),
                    )
                )

                continue


            # ------------------------------------------------
            # PERSONAL CASE / FATWA BOUNDARY
            # ------------------------------------------------

            if (
                claim.role
                is ShubuhatClaimRole
                .PERSONAL_RULING_REQUEST
                or claim.personal_case_specific
                or question_mode
                is ShubuhatQuestionMode
                .PERSONAL_CASE
            ):

                has_escalation = True

                plans.append(
                    ShubuhatClaimPlan(
                        claim_id=claim.claim_id,
                        decision=(
                            ShubuhatClaimDecision
                            .ESCALATE
                        ),
                        bayyinat_may_structure_claim=False,
                        reasons=(
                            "personal_fatwa_out_of_scope",
                        ),
                    )
                )

                continue


            # ------------------------------------------------
            # UNKNOWN DOMAIN
            # ------------------------------------------------

            if (
                claim.domain
                is ShubuhatClaimDomain.UNKNOWN
            ):

                has_retrieve_more = True

                plans.append(
                    ShubuhatClaimPlan(
                        claim_id=claim.claim_id,
                        decision=(
                            ShubuhatClaimDecision
                            .RETRIEVE_MORE
                        ),
                        reasons=(
                            "claim_domain_required",
                        ),
                    )
                )

                continue


            # ------------------------------------------------
            # CROSS-DOMAIN EVIDENTIARY CLAIM
            #
            # Bayyinat may explain/structure it.
            # Evidence ownership stays with primary domain.
            # ------------------------------------------------

            if (
                claim.domain
                in _PRIMARY_EVIDENCE_DOMAINS
            ):

                has_primary_route = True

                reasons = [
                    "primary_domain_evidence_required",
                    (
                        "bayyinat_conversational_role_"
                        "does_not_transfer_evidentiary_authority"
                    ),
                ]

                if claim.asserts_consensus:

                    reasons.append(
                        "consensus_requires_primary_domain_support"
                    )

                plans.append(
                    ShubuhatClaimPlan(
                        claim_id=claim.claim_id,
                        decision=(
                            ShubuhatClaimDecision
                            .ROUTE_TO_PRIMARY_DOMAIN
                        ),
                        primary_evidence_domain=(
                            claim.domain
                        ),
                        bayyinat_may_structure_claim=True,
                        bayyinat_may_be_primary_evidence=False,
                        may_state_consensus_from_bayyinat=False,
                        reasons=tuple(
                            reasons
                        ),
                    )
                )

                continue


            # ------------------------------------------------
            # BAYYINAT-CONVERSATIONAL MATERIAL
            #
            # This is framing/FAQ structure, not a license to
            # manufacture primary evidence.
            # ------------------------------------------------

            if (
                claim.domain
                is ShubuhatClaimDomain
                .BAYYINAT_CONVERSATIONAL
            ):

                if (
                    claim.role
                    not in {
                        ShubuhatClaimRole
                        .CONVERSATIONAL_FRAMING,

                        ShubuhatClaimRole
                        .EXPLANATORY_STRUCTURE,
                    }
                ):

                    has_block = True

                    plans.append(
                        ShubuhatClaimPlan(
                            claim_id=claim.claim_id,
                            decision=(
                                ShubuhatClaimDecision
                                .BLOCKED
                            ),
                            reasons=(
                                "bayyinat_conversational_domain_cannot_carry_primary_evidentiary_claim",
                            ),
                        )
                    )

                    continue

                if not bayyinat_ready:

                    has_retrieve_more = True

                    plans.append(
                        ShubuhatClaimPlan(
                            claim_id=claim.claim_id,
                            decision=(
                                ShubuhatClaimDecision
                                .RETRIEVE_MORE
                            ),
                            reasons=(
                                "bayyinat_runtime_source_not_yet_eligible",
                            ),
                        )
                    )

                    continue

                plans.append(
                    ShubuhatClaimPlan(
                        claim_id=claim.claim_id,
                        decision=(
                            ShubuhatClaimDecision
                            .USE_CONVERSATIONALLY
                        ),
                        bayyinat_may_structure_claim=True,
                        bayyinat_may_be_primary_evidence=False,
                        reasons=(
                            "bayyinat_conversational_material_eligible",
                        ),
                    )
                )

                continue


            has_retrieve_more = True

            plans.append(
                ShubuhatClaimPlan(
                    claim_id=claim.claim_id,
                    decision=(
                        ShubuhatClaimDecision
                        .RETRIEVE_MORE
                    ),
                    reasons=(
                        "unsupported_claim_configuration",
                    ),
                )
            )


        # ----------------------------------------------------
        # OVERALL DECISION
        # ----------------------------------------------------

        if has_escalation:

            decision = (
                ShubuhatOverallDecision
                .ESCALATE
            )

            overall_reasons.append(
                "personal_case_requires_qualified_referral"
            )

        elif has_block:

            decision = (
                ShubuhatOverallDecision
                .BLOCKED
            )

            overall_reasons.append(
                "unsafe_source_role_configuration"
            )

        elif has_retrieve_more:

            decision = (
                ShubuhatOverallDecision
                .RETRIEVE_MORE
            )

            overall_reasons.append(
                "additional_governed_material_required"
            )

        elif has_primary_route:

            decision = (
                ShubuhatOverallDecision
                .PRIMARY_EVIDENCE_REQUIRED
            )

            overall_reasons.append(
                "cross_domain_claims_require_primary_evidence"
            )

        else:

            decision = (
                ShubuhatOverallDecision
                .READY_FOR_CONVERSATIONAL_DRAFT
            )


        if (
            question_mode
            is ShubuhatQuestionMode
            .HOSTILE_FORMULATION
        ):

            overall_reasons.append(
                "hostile_wording_does_not_change_response_ethics"
            )


        return ShubuhatAssessment(
            decision=decision,
            claim_plans=tuple(
                plans
            ),
            reasons=tuple(
                dict.fromkeys(
                    overall_reasons
                )
            ),
        )
