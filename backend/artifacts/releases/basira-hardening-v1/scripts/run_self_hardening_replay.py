#!/usr/bin/env python3
"""
Run Basira Self-Hardening counterfactual replay.

This script proves promotion eligibility.
It does NOT promote constraints by itself.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from basira.trust.replay import (
    PytestReplayExecutor,
    execute_replay_plans,
    load_replay_plans,
)
from basira.trust.self_hardening import (
    load_failure_certificates,
)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--report",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    root = Path.cwd()

    certificates = load_failure_certificates(
        root
        / "data/trust/self-hardening/"
        "failure-certificates-v1.json"
    )

    plans = load_replay_plans(
        root
        / "data/trust/self-hardening/"
        "replay-plans-v1.json"
    )

    certificate_ids = {
        item.certificate_id
        for item in certificates
    }

    plan_certificate_ids = {
        item.certificate_id
        for item in plans
    }

    if certificate_ids != plan_certificate_ids:
        raise SystemExit(
            "failure certificates and replay plans differ"
        )

    results = execute_replay_plans(
        plans,
        executor=PytestReplayExecutor(
            project_root=root,
        ),
    )

    report = {
        "schema_version": "1",
        "religious_evidence_authority": 0,
        "results": [],
    }

    all_safe = True

    for result in results:
        verdict = result.verdict

        all_safe = (
            all_safe
            and verdict.safe_to_promote
        )

        status = (
            "SAFE_TO_PROMOTE"
            if verdict.safe_to_promote
            else "BLOCKED"
        )

        print()
        print(result.certificate_id)
        print(
            "  attack_blocked       =",
            verdict.attack_blocked,
        )
        print(
            "  valid_controls       =",
            verdict.valid_controls_passed,
        )
        print(
            "  regression           =",
            verdict.regression_passed,
        )
        print(
            "  promotion_eligibility=",
            status,
        )

        report["results"].append(
            {
                "certificate_id": (
                    result.certificate_id
                ),
                "attack_blocked": (
                    verdict.attack_blocked
                ),
                "valid_controls_passed": (
                    verdict.valid_controls_passed
                ),
                "regression_passed": (
                    verdict.regression_passed
                ),
                "safe_to_promote": (
                    verdict.safe_to_promote
                ),
            }
        )

    if args.report is not None:
        args.report.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.report.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        print()
        print("report =", args.report)

    print()

    if all_safe:
        print(
            "✅ ALL FAILURE CERTIFICATES "
            "PASSED EXECUTABLE REPLAY"
        )
        return 0

    print(
        "❌ AT LEAST ONE REPAIR IS NOT "
        "PROMOTION-ELIGIBLE"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
