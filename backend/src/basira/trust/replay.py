"""
Executable counterfactual replay for Self-Hardening Memory.

A repair is not trusted because it exists.
It becomes promotion-eligible only after executable replay proves:

1. the historical attack is blocked;
2. valid controls still work;
3. the wider Trust Shield regression remains green.

Replay produces governance evidence only.
It never produces religious evidence.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from basira.trust.self_hardening import ReplayVerdict


@dataclass(frozen=True, slots=True)
class ReplayPlan:
    plan_id: str
    certificate_id: str
    attack_selectors: tuple[str, ...]
    valid_control_selectors: tuple[str, ...]
    regression_selectors: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise ValueError("plan_id must not be blank")

        if not self.certificate_id.strip():
            raise ValueError(
                "certificate_id must not be blank"
            )

        if not self.attack_selectors:
            raise ValueError(
                "replay requires attack selectors"
            )

        if not self.valid_control_selectors:
            raise ValueError(
                "replay requires valid controls"
            )

        if not self.regression_selectors:
            raise ValueError(
                "replay requires regression selectors"
            )


@dataclass(frozen=True, slots=True)
class PytestRunResult:
    selectors: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


@dataclass(frozen=True, slots=True)
class CertificateReplayResult:
    certificate_id: str
    attack: PytestRunResult
    valid_controls: PytestRunResult
    regression: PytestRunResult

    @property
    def verdict(self) -> ReplayVerdict:
        return ReplayVerdict(
            attack_blocked=self.attack.passed,
            valid_controls_passed=(
                self.valid_controls.passed
            ),
            regression_passed=self.regression.passed,
        )


class ReplayCommandExecutor(Protocol):
    def run(
        self,
        selectors: tuple[str, ...],
    ) -> PytestRunResult: ...


class PytestReplayExecutor:
    """
    Execute pytest selectors in the current trusted checkout.

    No source mutation occurs here.
    """

    def __init__(
        self,
        *,
        project_root: Path,
    ) -> None:
        self.project_root = project_root.resolve()

    def run(
        self,
        selectors: tuple[str, ...],
    ) -> PytestRunResult:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                *selectors,
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        return PytestRunResult(
            selectors=selectors,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def execute_replay_plans(
    plans: tuple[ReplayPlan, ...],
    *,
    executor: ReplayCommandExecutor,
) -> tuple[CertificateReplayResult, ...]:
    """
    Execute unique selector groups once.

    Shared controls/regressions are cached so four failure
    certificates do not run the same 62-test suite four times.
    """

    cache: dict[
        tuple[str, ...],
        PytestRunResult,
    ] = {}

    def execute(
        selectors: tuple[str, ...],
    ) -> PytestRunResult:
        existing = cache.get(selectors)

        if existing is not None:
            return existing

        result = executor.run(selectors)
        cache[selectors] = result

        return result

    results: list[CertificateReplayResult] = []

    for plan in plans:
        results.append(
            CertificateReplayResult(
                certificate_id=plan.certificate_id,
                attack=execute(
                    plan.attack_selectors
                ),
                valid_controls=execute(
                    plan.valid_control_selectors
                ),
                regression=execute(
                    plan.regression_selectors
                ),
            )
        )

    return tuple(results)


def load_replay_plans(
    path: Path,
) -> tuple[ReplayPlan, ...]:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    records = payload.get("plans")

    if not isinstance(records, list):
        raise ValueError(
            "replay plan document requires plans"
        )

    return tuple(
        ReplayPlan(
            plan_id=record["plan_id"],
            certificate_id=record["certificate_id"],
            attack_selectors=tuple(
                record["attack_selectors"]
            ),
            valid_control_selectors=tuple(
                record["valid_control_selectors"]
            ),
            regression_selectors=tuple(
                record["regression_selectors"]
            ),
        )
        for record in records
    )
