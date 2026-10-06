#!/usr/bin/env python3
"""
Execute replay and promote verified Basira safety constraints.

A stored replay report is NEVER accepted as promotion proof.
"""

from __future__ import annotations

import json
from pathlib import Path

from basira.trust.promotion import (
    promote_from_executable_replay,
    promoted_constraints_document,
)
from basira.trust.replay import (
    PytestReplayExecutor,
    load_replay_plans,
)
from basira.trust.self_hardening import (
    load_failure_certificates,
)


def main() -> int:
    root = Path.cwd()

    certificate_path = (
        root
        / "data/trust/self-hardening/"
        "failure-certificates-v1.json"
    )

    replay_path = (
        root
        / "data/trust/self-hardening/"
        "replay-plans-v1.json"
    )

    output_path = (
        root
        / "data/trust/self-hardening/"
        "promoted-constraints-v1.json"
    )

    certificates = load_failure_certificates(
        certificate_path
    )

    plans = load_replay_plans(
        replay_path
    )

    batch = promote_from_executable_replay(
        certificates=certificates,
        plans=plans,
        executor=PytestReplayExecutor(
            project_root=root,
        ),
    )

    document = promoted_constraints_document(
        batch.constraints
    )

    output_path.write_text(
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()

    for result, constraint in zip(
        batch.replay_results,
        batch.constraints,
        strict=True,
    ):
        print(
            "✅",
            result.certificate_id,
        )
        print(
            "   replay.safe_to_promote =",
            result.verdict.safe_to_promote,
        )
        print(
            "   constraint =",
            constraint.constraint_id,
        )
        print(
            "   religious authority =",
            constraint.evidence_authority,
        )

    print()
    print(
        "Promoted constraints:",
        len(batch.constraints),
    )
    print(
        "Religious evidence authority: 0"
    )
    print(
        "output =",
        output_path,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
