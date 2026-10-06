import pytest
from pydantic import ValidationError

from basira.competition.aqeedah_authority import (
    AqeedahAuthorityBasis,
    AqeedahAuthorityEvidence,
    AqeedahAuthorityStatus,
    AqeedahAuthorityUseDecision,
    assess_aqeedah_authority,
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
    OfficialAqeedahPolicy,
)


def period():
    return AqeedahEarlyPeriodEvidence(
        status=(
            AqeedahEarlyPeriodStatus.VERIFIED
        ),
        basis=(
            AqeedahEarlyPeriodBasis
            .WORK_COMPOSITION
        ),
        source_origin_not_after_ah=200,
        evidence_ids=(
            "period:verified",
        ),
    )


def early_record(
    authority: AqeedahAuthorityEvidence,
):
    return AqeedahEvidenceRecord(
        text="مادة عقدية مبكرة",
        source_family=(
            AqeedahSourceFamily
            .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
        ),
        source_title="مصدر مبكر",
        source_reference="1/10",
        source_eligibility=(
            AqeedahSourceEligibility.ELIGIBLE
        ),
        material_type=(
            AqeedahMaterialType
            .EARLY_SCHOLAR_STATEMENT
        ),
        early_period=period(),
        authority=authority,
        source_identity_verified=True,
        exact_artifact_governed=True,
    )


def test_early_unknown_authority_is_not_usable() -> None:
    result = OfficialAqeedahPolicy().assess(
        (
            early_record(
                AqeedahAuthorityEvidence()
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision.RETRIEVE_MORE
    )

    assert (
        "aqeedah_authority_unknown"
        in result.reasons
    )


def test_early_quarantined_authority_is_blocked() -> None:
    result = OfficialAqeedahPolicy().assess(
        (
            early_record(
                AqeedahAuthorityEvidence(
                    status=(
                        AqeedahAuthorityStatus
                        .QUARANTINED
                    ),
                    basis=(
                        AqeedahAuthorityBasis
                        .MANUAL_SCHOLARLY_AUDIT
                    ),
                    evidence_ids=(
                        "authority:quarantine",
                    ),
                )
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision.BLOCKED
    )


def test_verified_primary_authority_is_usable() -> None:
    result = OfficialAqeedahPolicy().assess(
        (
            early_record(
                AqeedahAuthorityEvidence(
                    status=(
                        AqeedahAuthorityStatus
                        .VERIFIED_PRIMARY
                    ),
                    basis=(
                        AqeedahAuthorityBasis
                        .MANUAL_SCHOLARLY_AUDIT
                    ),
                    evidence_ids=(
                        "authority:primary",
                    ),
                )
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision.USABLE
    )


def test_verified_supporting_authority_is_not_primary() -> None:
    result = OfficialAqeedahPolicy().assess(
        (
            early_record(
                AqeedahAuthorityEvidence(
                    status=(
                        AqeedahAuthorityStatus
                        .VERIFIED_SUPPORTING
                    ),
                    basis=(
                        AqeedahAuthorityBasis
                        .GOVERNED_SOURCE_CATALOG
                    ),
                    evidence_ids=(
                        "authority:supporting",
                    ),
                )
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision
        .SUPPORTING_ONLY
    )


def test_dorar_reference_listing_does_not_create_primary_authority() -> None:
    authority = AqeedahAuthorityEvidence(
        status=(
            AqeedahAuthorityStatus
            .DORAR_REFERENCE_LISTED
        ),
        basis=(
            AqeedahAuthorityBasis
            .DORAR_GOVERNED_REFERENCE
        ),
        evidence_ids=(
            "dorar:refs:aqeeda:test",
        ),
    )

    authority_result = (
        assess_aqeedah_authority(
            authority
        )
    )

    assert (
        authority_result.decision
        is AqeedahAuthorityUseDecision
        .SUPPORTING_ONLY
    )

    result = OfficialAqeedahPolicy().assess(
        (
            early_record(
                authority
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision
        .SUPPORTING_ONLY
    )


def test_age_and_provenance_do_not_replace_authority() -> None:
    """
    This is the critical regression.

    The source passes:
    - first-three-centuries period
    - identity
    - exact artifact
    - runtime eligibility

    but still fails because Aqeedah authority is unknown.
    """

    record = early_record(
        AqeedahAuthorityEvidence(
            status=(
                AqeedahAuthorityStatus.UNKNOWN
            )
        )
    )

    result = OfficialAqeedahPolicy().assess(
        (
            record,
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision.RETRIEVE_MORE
    )


def test_shamela_hosting_does_not_authorize_early_book() -> None:
    record = AqeedahEvidenceRecord(
        text="نص موجود في المكتبة الشاملة",
        source_family=(
            AqeedahSourceFamily
            .FIRST_THREE_CENTURIES_ISLAMIC_SOURCE
        ),
        source_title="كتاب مبكر غير مدقق سلطته",
        source_reference="shamela:test",
        source_eligibility=(
            AqeedahSourceEligibility.ELIGIBLE
        ),
        material_type=(
            AqeedahMaterialType
            .EARLY_SCHOLAR_STATEMENT
        ),
        early_period=period(),
        authority=AqeedahAuthorityEvidence(
            status=(
                AqeedahAuthorityStatus.UNKNOWN
            )
        ),
        edition_or_provider="Shamela",
        source_identity_verified=True,
        exact_artifact_governed=True,
    )

    result = OfficialAqeedahPolicy().assess(
        (
            record,
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision.RETRIEVE_MORE
    )

    assert (
        result.may_use_generic_shamela_fallback
        is False
    )


def test_fiqh_source_family_cannot_satisfy_aqeedah_record() -> None:
    with pytest.raises(
        ValidationError
    ):
        AqeedahEvidenceRecord(
            text="نص فقهي",
            source_family="dorar_fiqh",
            source_title="الموسوعة الفقهية",
            source_eligibility="eligible",
            material_type="scholarly_explanation",
            source_identity_verified=True,
            exact_artifact_governed=True,
        )


def test_three_early_sources_still_do_not_establish_consensus() -> None:
    authority = AqeedahAuthorityEvidence(
        status=(
            AqeedahAuthorityStatus
            .VERIFIED_PRIMARY
        ),
        basis=(
            AqeedahAuthorityBasis
            .MANUAL_SCHOLARLY_AUDIT
        ),
        evidence_ids=(
            "authority:primary",
        ),
    )

    result = OfficialAqeedahPolicy().assess(
        (
            early_record(
                authority
            ),
            early_record(
                authority
            ),
            early_record(
                authority
            ),
        )
    )

    assert (
        result.decision
        is AqeedahEvidenceDecision.USABLE
    )

    assert (
        result.may_claim_consensus
        is False
    )
