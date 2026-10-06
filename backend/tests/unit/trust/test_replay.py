from pathlib import Path

from basira.trust.replay import (
    PytestRunResult,
    ReplayPlan,
    execute_replay_plans,
    load_replay_plans,
)

PLANS = Path(
    "data/trust/self-hardening/"
    "replay-plans-v1.json"
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
        self.calls: list[
            tuple[str, ...]
        ] = []

    def run(
        self,
        selectors: tuple[str, ...],
    ) -> PytestRunResult:
        self.calls.append(selectors)

        failed = selectors in self.failing

        return PytestRunResult(
            selectors=selectors,
            returncode=1 if failed else 0,
            stdout="",
            stderr="",
        )


def test_real_failure_certificates_have_replay_plans() -> None:
    plans = load_replay_plans(PLANS)

    assert {
        plan.certificate_id
        for plan in plans
    } == {
        "failure:typed-role-spoofing:v1",
        "failure:role-laundering:v1",
        "failure:publication-authority-forgery:v1",
        "failure:source-domain-identity-spoofing:v1",
    }


def test_clean_executable_replay_is_promotion_eligible() -> None:
    plan = ReplayPlan(
        plan_id="replay:test",
        certificate_id="failure:test",
        attack_selectors=("attack",),
        valid_control_selectors=("control",),
        regression_selectors=("regression",),
    )

    result = execute_replay_plans(
        (plan,),
        executor=FakeExecutor(),
    )[0]

    assert result.verdict.safe_to_promote


def test_failed_attack_replay_fails_closed() -> None:
    plan = ReplayPlan(
        plan_id="replay:test",
        certificate_id="failure:test",
        attack_selectors=("attack",),
        valid_control_selectors=("control",),
        regression_selectors=("regression",),
    )

    result = execute_replay_plans(
        (plan,),
        executor=FakeExecutor(
            failing=frozenset(
                {
                    ("attack",),
                }
            )
        ),
    )[0]

    assert not result.verdict.attack_blocked
    assert not result.verdict.safe_to_promote


def test_shared_replay_groups_execute_only_once() -> None:
    shared_control = ("control",)
    shared_regression = ("regression",)

    plans = (
        ReplayPlan(
            plan_id="replay:a",
            certificate_id="failure:a",
            attack_selectors=("attack-a",),
            valid_control_selectors=shared_control,
            regression_selectors=shared_regression,
        ),
        ReplayPlan(
            plan_id="replay:b",
            certificate_id="failure:b",
            attack_selectors=("attack-b",),
            valid_control_selectors=shared_control,
            regression_selectors=shared_regression,
        ),
    )

    executor = FakeExecutor()

    execute_replay_plans(
        plans,
        executor=executor,
    )

    assert executor.calls.count(
        shared_control
    ) == 1

    assert executor.calls.count(
        shared_regression
    ) == 1

    assert len(executor.calls) == 4
