from basira.competition.source_foundation import (
    CompetitionSourceArtifact,
    CompetitionSourceEligibilityGate,
    CompetitionSourceIdentity,
    CompetitionSourceRole,
    CompetitionSourceStatus,
)


def artifact(
    *,
    status: CompetitionSourceStatus,
    sha256: str | None = "a" * 64,
    snapshot_path: str | None = "/snapshot/source.json",
) -> CompetitionSourceArtifact:
    return CompetitionSourceArtifact(
        identity=CompetitionSourceIdentity(
            source_id="source:test",
            name="Test Source",
            role=CompetitionSourceRole.QURAN,
        ),
        status=status,
        official_reference_basis="official-package",
        sha256=sha256,
        snapshot_path=snapshot_path,
    )


def test_pending_source_is_not_runtime_eligible() -> None:
    decision = CompetitionSourceEligibilityGate().decide(
        artifact(
            status=CompetitionSourceStatus.PENDING_AUDIT,
        )
    )

    assert decision.eligible_for_runtime is False


def test_baseline_only_source_is_not_runtime_eligible() -> None:
    decision = CompetitionSourceEligibilityGate().decide(
        artifact(
            status=CompetitionSourceStatus.BASELINE_ONLY,
        )
    )

    assert decision.eligible_for_runtime is False


def test_even_eligible_label_fails_without_hash() -> None:
    decision = CompetitionSourceEligibilityGate().decide(
        artifact(
            status=CompetitionSourceStatus.ELIGIBLE,
            sha256=None,
        )
    )

    assert decision.eligible_for_runtime is False
    assert decision.status is CompetitionSourceStatus.QUARANTINED


def test_even_eligible_label_fails_without_snapshot() -> None:
    decision = CompetitionSourceEligibilityGate().decide(
        artifact(
            status=CompetitionSourceStatus.ELIGIBLE,
            snapshot_path=None,
        )
    )

    assert decision.eligible_for_runtime is False


def test_audited_eligible_source_can_enter_runtime() -> None:
    decision = CompetitionSourceEligibilityGate().decide(
        artifact(
            status=CompetitionSourceStatus.ELIGIBLE,
        )
    )

    assert decision.eligible_for_runtime is True


def test_attestation_status_requires_attestation_proof() -> None:
    decision = CompetitionSourceEligibilityGate().decide(
        artifact(
            status=(
                CompetitionSourceStatus
                .ELIGIBLE_WITH_ATTESTATION
            ),
        )
    )

    assert decision.eligible_for_runtime is False
    assert (
        "missing_required_attestation"
        in decision.reasons
    )


def test_malformed_sha256_is_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        artifact(
            status=CompetitionSourceStatus.ELIGIBLE,
            sha256="abc123",
        )
