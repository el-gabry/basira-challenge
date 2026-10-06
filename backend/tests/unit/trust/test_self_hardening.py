from pathlib import Path

import pytest

from basira.trust.self_hardening import (
    MEMORY_EVIDENCE_AUTHORITY,
    FailureCertificate,
    FailureDisposition,
    FailureKind,
    RepairPromotionError,
    ReplayVerdict,
    SelfHardeningMemory,
    load_failure_certificates,
)

CERTIFICATES = Path(
    "data/trust/self-hardening/"
    "failure-certificates-v1.json"
)


def test_real_trust_shield_failures_are_seeded() -> None:
    certificates = load_failure_certificates(
        CERTIFICATES
    )

    assert {
        certificate.failure_kind
        for certificate in certificates
    } == {
        FailureKind.TYPED_ROLE_SPOOFING,
        FailureKind.ROLE_LAUNDERING,
        FailureKind.PUBLICATION_AUTHORITY_FORGERY,
        FailureKind.SOURCE_DOMAIN_IDENTITY_SPOOFING,
        FailureKind.QURAN_VERIFICATION_INTENT_FALLTHROUGH,
    }


def test_memory_artifacts_have_zero_evidence_authority() -> None:
    certificates = load_failure_certificates(
        CERTIFICATES
    )

    assert MEMORY_EVIDENCE_AUTHORITY == 0

    for certificate in certificates:
        assert certificate.evidence_authority == 0
        assert not certificate.can_support_religious_claim


def test_verified_failure_can_promote_constraint() -> None:
    certificate = load_failure_certificates(
        CERTIFICATES
    )[0]

    memory = SelfHardeningMemory()
    memory.remember_failure(certificate)

    constraint = memory.promote(
        certificate.certificate_id,
        ReplayVerdict(
            attack_blocked=True,
            valid_controls_passed=True,
            regression_passed=True,
        ),
    )

    assert constraint.evidence_authority == 0
    assert not constraint.can_support_religious_claim
    assert constraint.rule == certificate.repair_constraint


@pytest.mark.parametrize(
    (
        "attack_blocked",
        "valid_controls_passed",
        "regression_passed",
    ),
    (
        (False, True, True),
        (True, False, True),
        (True, True, False),
    ),
)
def test_promotion_fails_closed_when_replay_is_not_clean(
    attack_blocked: bool,
    valid_controls_passed: bool,
    regression_passed: bool,
) -> None:
    certificate = load_failure_certificates(
        CERTIFICATES
    )[0]

    memory = SelfHardeningMemory()
    memory.remember_failure(certificate)

    with pytest.raises(RepairPromotionError):
        memory.promote(
            certificate.certificate_id,
            ReplayVerdict(
                attack_blocked=attack_blocked,
                valid_controls_passed=(
                    valid_controls_passed
                ),
                regression_passed=regression_passed,
            ),
        )


def test_protected_disagreement_cannot_be_promoted() -> None:
    certificate = FailureCertificate(
        certificate_id="failure:protected-disagreement:test",
        failure_kind=FailureKind.TYPED_ROLE_SPOOFING,
        disposition=FailureDisposition.PROTECTED_DISAGREEMENT,
        observed_failure="Scholarly disagreement.",
        violated_invariant="No system invariant violated.",
        repair_constraint="Do not collapse disagreement.",
        replay_test_ids=("protected:test",),
    )

    memory = SelfHardeningMemory()
    memory.remember_failure(certificate)

    with pytest.raises(RepairPromotionError):
        memory.promote(
            certificate.certificate_id,
            ReplayVerdict(
                attack_blocked=True,
                valid_controls_passed=True,
                regression_passed=True,
            ),
        )
