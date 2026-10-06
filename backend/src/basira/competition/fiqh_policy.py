from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FiqhQuestionScope(StrEnum):
    GENERAL_FIQH = "general_fiqh"
    PERSONAL_CASE = "personal_case"


class FiqhSourceFamily(StrEnum):
    """
    Source FAMILY allowed by the official competition reference.

    This does NOT itself imply that a concrete book, edition,
    snapshot, or live provider response is runtime-eligible.
    """

    MADHHAB_FIQH_BOOK = "madhhab_fiqh_book"

    DORAR_FIQH = "dorar_fiqh"

    UNKNOWN = "unknown"


class FiqhSourceEligibility(StrEnum):
    """
    Basira governance state for the exact source instance.
    """

    ELIGIBLE = "eligible"

    PENDING_AUDIT = "pending_audit"

    QUARANTINED = "quarantined"

    UNKNOWN = "unknown"


class Madhhab(StrEnum):
    HANAFI = "hanafi"

    MALIKI = "maliki"

    SHAFII = "shafii"

    HANBALI = "hanbali"

    UNSPECIFIED = "unspecified"


class FiqhDisagreementState(StrEnum):
    SINGLE_POSITION = "single_position"

    DOCUMENTED_DISAGREEMENT = (
        "documented_disagreement"
    )

    UNRESOLVED = "unresolved"


class FiqhEvidenceDecision(StrEnum):
    USABLE_GENERAL_INFORMATION = (
        "usable_general_information"
    )

    USABLE_COMPARATIVE = (
        "usable_comparative"
    )

    RETRIEVE_MORE = "retrieve_more"

    ESCALATE_TO_QUALIFIED_SCHOLAR = (
        "escalate_to_qualified_scholar"
    )

    NOT_USABLE = "not_usable"


class FiqhPosition(BaseModel):
    position_text: str

    source_family: FiqhSourceFamily

    source_title: str

    source_reference: str | None = None

    source_eligibility: FiqhSourceEligibility = (
        FiqhSourceEligibility.UNKNOWN
    )

    madhhab: Madhhab = Madhhab.UNSPECIFIED

    scholar: str | None = None

    edition_or_provenance: str | None = None

    evidence_excerpt: str | None = None

    conditions: tuple[str, ...] = Field(
        default_factory=tuple
    )

    exceptions: tuple[str, ...] = Field(
        default_factory=tuple
    )


class FiqhEvidenceCandidate(BaseModel):
    issue: str

    scope: FiqhQuestionScope

    positions: tuple[
        FiqhPosition,
        ...
    ] = Field(
        default_factory=tuple
    )

    explicitly_disputed: bool = False


class FiqhPolicyAssessment(BaseModel):
    decision: FiqhEvidenceDecision

    disagreement_state: (
        FiqhDisagreementState
    )

    usable_positions: tuple[
        FiqhPosition,
        ...
    ] = Field(
        default_factory=tuple
    )

    preserve_madhhab_attribution: bool = True

    preserve_conditions: bool = True

    preserve_exceptions: bool = True

    automated_tarjih_allowed: bool = False

    majority_vote_allowed: bool = False

    consensus_inference_allowed: bool = False

    independent_personal_fatwa_allowed: bool = False

    qualified_referral_required: bool = False

    requires_claim_evidence_check: bool = True

    reasons: tuple[str, ...] = Field(
        default_factory=tuple
    )


_ALLOWED_SOURCE_FAMILIES = {
    FiqhSourceFamily.MADHHAB_FIQH_BOOK,
    FiqhSourceFamily.DORAR_FIQH,
}


class OfficialFiqhPolicy:
    """
    Official competition Fiqh policy.

    Allowed source families:

    A) A recognized/authoritative Fiqh book within one
       of the four madhhabs:
       Hanafi, Maliki, Shafii, Hanbali.

    B) Dorar Fiqh Encyclopedia.

    IMPORTANT:

    Being in an allowed family is not the same as runtime
    source eligibility.

    The exact book/edition/provider snapshot must still pass
    Basira source governance before its evidence can be used.

    The policy also prohibits:

    - independent personal fatwa;
    - automated tarjih;
    - majority-vote jurisprudence;
    - collapsing documented disagreement;
    - unsupported consensus claims.
    """

    def assess(
        self,
        candidate: FiqhEvidenceCandidate,
    ) -> FiqhPolicyAssessment:

        # ----------------------------------------------------
        # Personal case boundary comes first.
        # ----------------------------------------------------

        if (
            candidate.scope
            is FiqhQuestionScope.PERSONAL_CASE
        ):
            return FiqhPolicyAssessment(
                decision=(
                    FiqhEvidenceDecision
                    .ESCALATE_TO_QUALIFIED_SCHOLAR
                ),
                disagreement_state=(
                    FiqhDisagreementState
                    .UNRESOLVED
                ),
                qualified_referral_required=True,
                reasons=(
                    "personal_case_no_independent_fatwa",
                    "general_information_only",
                    "qualified_referral_required",
                ),
            )

        if not candidate.positions:
            return FiqhPolicyAssessment(
                decision=(
                    FiqhEvidenceDecision
                    .RETRIEVE_MORE
                ),
                disagreement_state=(
                    FiqhDisagreementState
                    .UNRESOLVED
                ),
                reasons=(
                    "no_fiqh_positions_retrieved",
                ),
            )

        usable: list[FiqhPosition] = []

        family_rejected = False
        governance_rejected = False

        for position in candidate.positions:

            if not position.position_text.strip():
                continue

            if not position.source_title.strip():
                continue

            # ------------------------------------------------
            # Layer 1 — official source-family permission.
            # ------------------------------------------------

            if (
                position.source_family
                not in _ALLOWED_SOURCE_FAMILIES
            ):
                family_rejected = True
                continue

            # ------------------------------------------------
            # Madhhab book requires madhhab identity.
            # "A Fiqh book" is not sufficient by itself.
            # ------------------------------------------------

            if (
                position.source_family
                is FiqhSourceFamily.MADHHAB_FIQH_BOOK
                and position.madhhab
                is Madhhab.UNSPECIFIED
            ):
                family_rejected = True
                continue

            # ------------------------------------------------
            # Layer 2 — Basira source governance.
            #
            # Allowed family ≠ runtime eligible source.
            # Applies to BOTH Dorar and madhhab books.
            # ------------------------------------------------

            if (
                position.source_eligibility
                is not FiqhSourceEligibility.ELIGIBLE
            ):
                governance_rejected = True
                continue

            usable.append(
                position
            )

        if not usable:
            reasons = [
                "no_eligible_fiqh_evidence",
            ]

            if family_rejected:
                reasons.append(
                    "official_source_family_required"
                )

            if governance_rejected:
                reasons.append(
                    "source_governance_required"
                )

            return FiqhPolicyAssessment(
                decision=(
                    FiqhEvidenceDecision
                    .RETRIEVE_MORE
                ),
                disagreement_state=(
                    FiqhDisagreementState
                    .UNRESOLVED
                ),
                reasons=tuple(reasons),
            )

        # ----------------------------------------------------
        # Pluralism / disagreement preservation.
        # ----------------------------------------------------

        distinct_positions = {
            item.position_text.strip()
            for item in usable
        }

        distinct_madhhabs = {
            item.madhhab
            for item in usable
            if (
                item.madhhab
                is not Madhhab.UNSPECIFIED
            )
        }

        has_disagreement = (
            candidate.explicitly_disputed
            or len(distinct_positions) > 1
            or len(distinct_madhhabs) > 1
        )

        if has_disagreement:
            return FiqhPolicyAssessment(
                decision=(
                    FiqhEvidenceDecision
                    .USABLE_COMPARATIVE
                ),
                disagreement_state=(
                    FiqhDisagreementState
                    .DOCUMENTED_DISAGREEMENT
                ),
                usable_positions=tuple(
                    usable
                ),
                reasons=(
                    "documented_positions_preserved",
                    "automated_tarjih_prohibited",
                    "false_consensus_prohibited",
                ),
            )

        return FiqhPolicyAssessment(
            decision=(
                FiqhEvidenceDecision
                .USABLE_GENERAL_INFORMATION
            ),
            disagreement_state=(
                FiqhDisagreementState
                .SINGLE_POSITION
            ),
            usable_positions=tuple(
                usable
            ),
            reasons=(
                "eligible_general_fiqh_evidence",
                "no_automated_tarjih",
            ),
        )
