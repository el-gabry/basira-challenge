from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field


class HadithAuthorityClass(StrEnum):
    SAHIHAIN_PRIMARY = "sahihain_primary"

    OTHER_SUNNAH_REQUIRES_VERIFICATION = (
        "other_sunnah_requires_verification"
    )

    UNKNOWN_SOURCE = "unknown_source"


class HadithVerificationAuthority(StrEnum):
    CANONICAL_SAHIHAIN = "canonical_sahihain"

    DORAR = "dorar"

    APPROVED_SHAMELA_EDITION = (
        "approved_shamela_edition"
    )

    NONE = "none"


class HadithEvidenceDecision(StrEnum):
    USABLE = "usable"

    USABLE_WITH_ATTRIBUTED_GRADINGS = (
        "usable_with_attributed_gradings"
    )

    RETRIEVE_MORE = "retrieve_more"

    NOT_USABLE_AS_HADITH_EVIDENCE = (
        "not_usable_as_hadith_evidence"
    )


class HadithVerificationState(StrEnum):
    SAHIHAIN_SOURCE_VERIFIED = (
        "sahihain_source_verified"
    )

    VERIFIED_WITH_ATTRIBUTED_GRADING = (
        "verified_with_attributed_grading"
    )

    CONFLICTING_ATTRIBUTED_GRADINGS = (
        "conflicting_attributed_gradings"
    )

    NO_HITS_FOR_QUERY = "no_hits_for_query"

    MISSING_ATTRIBUTION = "missing_attribution"

    UNVERIFIED = "unverified"


class HadithAttestation(BaseModel):
    verification_authority: HadithVerificationAuthority

    muhaddith: str | None = None

    verdict: str | None = None

    reference: str | None = None


class HadithEvidenceCandidate(BaseModel):
    hadith_text: str

    claimed_collection: str | None = None

    collection_reference: str | None = None

    narrator: str | None = None

    governed_canonical_source: bool = False

    attestations: tuple[
        HadithAttestation,
        ...
    ] = Field(
        default_factory=tuple
    )

    no_hits_for_query: bool = False


class HadithPolicyAssessment(BaseModel):
    authority_class: HadithAuthorityClass

    decision: HadithEvidenceDecision

    verification_state: HadithVerificationState

    verification_authorities: tuple[
        HadithVerificationAuthority,
        ...
    ] = Field(
        default_factory=tuple
    )

    preserve_all_attestations: bool = True

    majority_vote_allowed: bool = False

    consensus_inference_allowed: bool = False

    requires_claim_evidence_check: bool = True

    reasons: tuple[str, ...]


_ARABIC_DIACRITICS = re.compile(
    r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]"
)


def _normalize_source(
    value: str | None,
) -> str:

    if not value:
        return ""

    value = _ARABIC_DIACRITICS.sub(
        "",
        value,
    )

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9\u0600-\u06ff]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _is_bukhari(
    value: str | None,
) -> bool:

    normalized = _normalize_source(
        value
    )

    indicators = (
        "صحيح البخاري",
        "البخاري",
        "sahih al bukhari",
        "sahih bukhari",
    )

    return any(
        indicator in normalized
        for indicator in indicators
    )


def _is_muslim(
    value: str | None,
) -> bool:

    normalized = _normalize_source(
        value
    )

    indicators = (
        "صحيح مسلم",
        "sahih muslim",
    )

    return any(
        indicator in normalized
        for indicator in indicators
    )


def _is_sahihain(
    value: str | None,
) -> bool:

    return (
        _is_bukhari(value)
        or _is_muslim(value)
    )


class OfficialHadithPolicy:
    """
    Competition Hadith policy.

    Official source hierarchy:

    1. Sahih al-Bukhari / Sahih Muslim:
       canonical primary path.

    2. Other Sunnah collections:
       require verification before use.

    3. Dorar:
       verification / grading authority.

    4. Approved Shamela editions:
       governed edition verification path.

    Search frequency never establishes consensus.
    """

    def assess(
        self,
        candidate: HadithEvidenceCandidate,
    ) -> HadithPolicyAssessment:

        text = candidate.hadith_text.strip()

        if not text:
            return HadithPolicyAssessment(
                authority_class=(
                    HadithAuthorityClass
                    .UNKNOWN_SOURCE
                ),
                decision=(
                    HadithEvidenceDecision
                    .NOT_USABLE_AS_HADITH_EVIDENCE
                ),
                verification_state=(
                    HadithVerificationState
                    .MISSING_ATTRIBUTION
                ),
                reasons=(
                    "missing_hadith_text",
                ),
            )

        collection = (
            candidate.claimed_collection
            or ""
        ).strip()

        reference = (
            candidate.collection_reference
            or ""
        ).strip()

        # ----------------------------------------------------
        # No source/reference → never usable as Hadith evidence
        # ----------------------------------------------------

        if not collection or not reference:
            return HadithPolicyAssessment(
                authority_class=(
                    HadithAuthorityClass
                    .UNKNOWN_SOURCE
                ),
                decision=(
                    HadithEvidenceDecision
                    .NOT_USABLE_AS_HADITH_EVIDENCE
                ),
                verification_state=(
                    HadithVerificationState
                    .MISSING_ATTRIBUTION
                ),
                reasons=(
                    "missing_collection_or_reference",
                    "hadith_attribution_required",
                ),
            )

        # ----------------------------------------------------
        # Sahihain primary path
        # ----------------------------------------------------

        if _is_sahihain(collection):

            if not candidate.governed_canonical_source:
                return HadithPolicyAssessment(
                    authority_class=(
                        HadithAuthorityClass
                        .SAHIHAIN_PRIMARY
                    ),
                    decision=(
                        HadithEvidenceDecision
                        .RETRIEVE_MORE
                    ),
                    verification_state=(
                        HadithVerificationState
                        .UNVERIFIED
                    ),
                    reasons=(
                        "sahihain_claim_requires_governed_source",
                    ),
                )

            return HadithPolicyAssessment(
                authority_class=(
                    HadithAuthorityClass
                    .SAHIHAIN_PRIMARY
                ),
                decision=(
                    HadithEvidenceDecision
                    .USABLE
                ),
                verification_state=(
                    HadithVerificationState
                    .SAHIHAIN_SOURCE_VERIFIED
                ),
                verification_authorities=(
                    HadithVerificationAuthority
                    .CANONICAL_SAHIHAIN,
                ),
                reasons=(
                    "canonical_sahihain_source_verified",
                    "no_extra_grading_invented",
                ),
            )

        # ----------------------------------------------------
        # Search failure is NOT proof of absence
        # ----------------------------------------------------

        if (
            candidate.no_hits_for_query
            and not candidate.attestations
        ):
            return HadithPolicyAssessment(
                authority_class=(
                    HadithAuthorityClass
                    .OTHER_SUNNAH_REQUIRES_VERIFICATION
                ),
                decision=(
                    HadithEvidenceDecision
                    .RETRIEVE_MORE
                ),
                verification_state=(
                    HadithVerificationState
                    .NO_HITS_FOR_QUERY
                ),
                reasons=(
                    "no_hits_for_query",
                    "zero_hits_do_not_prove_nonexistence",
                ),
            )

        # ----------------------------------------------------
        # Other Sunnah collections require attributed grading
        # ----------------------------------------------------

        if not candidate.attestations:
            return HadithPolicyAssessment(
                authority_class=(
                    HadithAuthorityClass
                    .OTHER_SUNNAH_REQUIRES_VERIFICATION
                ),
                decision=(
                    HadithEvidenceDecision
                    .RETRIEVE_MORE
                ),
                verification_state=(
                    HadithVerificationState
                    .UNVERIFIED
                ),
                reasons=(
                    "other_sunnah_requires_verification",
                ),
            )

        complete_attestations = []

        for attestation in candidate.attestations:

            if (
                attestation.verification_authority
                is HadithVerificationAuthority.NONE
            ):
                continue

            if not (
                attestation.muhaddith
                and attestation.verdict
            ):
                continue

            complete_attestations.append(
                attestation
            )

        if not complete_attestations:
            return HadithPolicyAssessment(
                authority_class=(
                    HadithAuthorityClass
                    .OTHER_SUNNAH_REQUIRES_VERIFICATION
                ),
                decision=(
                    HadithEvidenceDecision
                    .RETRIEVE_MORE
                ),
                verification_state=(
                    HadithVerificationState
                    .UNVERIFIED
                ),
                reasons=(
                    "grading_exists_without_complete_attribution",
                ),
            )

        verdicts = {
            item.verdict.strip()
            for item in complete_attestations
            if item.verdict
        }

        authorities = tuple(
            dict.fromkeys(
                item.verification_authority
                for item in complete_attestations
            )
        )

        if len(verdicts) > 1:
            return HadithPolicyAssessment(
                authority_class=(
                    HadithAuthorityClass
                    .OTHER_SUNNAH_REQUIRES_VERIFICATION
                ),
                decision=(
                    HadithEvidenceDecision
                    .USABLE_WITH_ATTRIBUTED_GRADINGS
                ),
                verification_state=(
                    HadithVerificationState
                    .CONFLICTING_ATTRIBUTED_GRADINGS
                ),
                verification_authorities=authorities,
                reasons=(
                    "multiple_attributed_gradings_preserved",
                    "majority_vote_prohibited",
                    "consensus_inference_prohibited",
                ),
            )

        return HadithPolicyAssessment(
            authority_class=(
                HadithAuthorityClass
                .OTHER_SUNNAH_REQUIRES_VERIFICATION
            ),
            decision=(
                HadithEvidenceDecision
                .USABLE_WITH_ATTRIBUTED_GRADINGS
            ),
            verification_state=(
                HadithVerificationState
                .VERIFIED_WITH_ATTRIBUTED_GRADING
            ),
            verification_authorities=authorities,
            reasons=(
                "other_sunnah_verified_with_attributed_grading",
            ),
        )
