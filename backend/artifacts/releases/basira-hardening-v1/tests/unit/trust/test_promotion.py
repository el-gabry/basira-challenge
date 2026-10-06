import pytest

from basira.trust.promotion import (
    promote_from_executable_replay,
    promoted_constraints_document,
)
from basira.trust.replay import (
    PytestRunResult,
    ReplayPlan,
)
from basira.trust.self_hardening import (
    FailureCertificate,
    FailureDisposition,
    FailureKind,
    RepairPromotionError,
)


class FakeExecutor:
    def __init__(
        self,
        *,
        failing: frozenset[
            tuple[str, ...]
        ] = frozenset(),
    ) -> None:
        self.failing = failing

    def run(
        self,
        selectors: tuple[str, ...],
    ) -> PytestRunResult:
        return PytestRunResult(
            selectors=selectors,
            returncode=(
                1
                if selectors in self.failing
                else 0
            ),
            stdout="",
            stderr="",
        )


def _certificate() -> FailureCertificate:
    return FailureCertificate(
        certificate_id="failure:test:v1",
        failure_kind=(
            FailureKind.TYPED_ROLE_SPOOFING
        ),
        disposition=(
            FailureDisposition.REPAIRABLE_SYSTEM_FAILURE
        ),
        observed_failure="Observed exploit.",
        violated_invariant="Invariant violated.",
        repair_constraint="Reject unsafe identity.",
        replay_test_ids=("attack",),
    )


def _plan() -> ReplayPlan:
    return ReplayPlan(
        plan_id="replay:test:v1",
        certificate_id="failure:test:v1",
        attack_selectors=("attack",),
        valid_control_selectors=("control",),
        regression_selectors=("regression",),
    )


def test_clean_replay_promotes_constraint() -> None:
    batch = promote_from_executable_replay(
        certificates=(_certificate(),),
        plans=(_plan(),),
        executor=FakeExecutor(),
    )

    assert len(batch.constraints) == 1

    constraint = batch.constraints[0]

    assert constraint.evidence_authority == 0
    assert not constraint.can_support_religious_claim


def test_failed_replay_cannot_promote() -> None:
    with pytest.raises(RepairPromotionError):
        promote_from_executable_replay(
            certificates=(_certificate(),),
            plans=(_plan(),),
            executor=FakeExecutor(
                failing=frozenset(
                    {
                        ("control",),
                    }
                )
            ),
        )


def test_certificate_plan_mismatch_fails_closed() -> None:
    wrong_plan = ReplayPlan(
        plan_id="replay:wrong:v1",
        certificate_id="failure:other:v1",
        attack_selectors=("attack",),
        valid_control_selectors=("control",),
        regression_selectors=("regression",),
    )

    with pytest.raises(ValueError):
        promote_from_executable_replay(
            certificates=(_certificate(),),
            plans=(wrong_plan,),
            executor=FakeExecutor(),
        )


def test_promoted_document_has_zero_authority() -> None:
    batch = promote_from_executable_replay(
        certificates=(_certificate(),),
        plans=(_plan(),),
        executor=FakeExecutor(),
    )

    document = promoted_constraints_document(
        batch.constraints
    )

    assert (
        document["religious_evidence_authority"]
        == 0
    )

    assert all(
        item["religious_evidence_authority"] == 0
        for item in document["constraints"]
    )
