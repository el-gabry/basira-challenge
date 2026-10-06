"""
Verified promotion pipeline for Basira Self-Hardening Memory.

Promotion authority comes from executable counterfactual replay,
never from a mutable report file.

Promoted constraints remain governance artifacts with
ZERO religious-evidence authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from basira.trust.replay import (
    CertificateReplayResult,
    ReplayCommandExecutor,
    ReplayPlan,
    execute_replay_plans,
)
from basira.trust.self_hardening import (
    MEMORY_EVIDENCE_AUTHORITY,
    FailureCertificate,
    LearnedConstraint,
    SelfHardeningMemory,
)


@dataclass(frozen=True, slots=True)
class PromotionBatch:
    replay_results: tuple[
        CertificateReplayResult,
        ...,
    ]
    constraints: tuple[
        LearnedConstraint,
        ...,
    ]


def promote_from_executable_replay(
    *,
    certificates: tuple[
        FailureCertificate,
        ...,
    ],
    plans: tuple[
        ReplayPlan,
        ...,
    ],
    executor: ReplayCommandExecutor,
) -> PromotionBatch:
    """
    Replay first, promote second.

    No JSON replay report is accepted as promotion proof.
    """

    certificates_by_id = {
        certificate.certificate_id: certificate
        for certificate in certificates
    }

    plan_certificate_ids = {
        plan.certificate_id
        for plan in plans
    }

    if (
        set(certificates_by_id)
        != plan_certificate_ids
    ):
        raise ValueError(
            "failure certificates and replay plans differ"
        )

    replay_results = execute_replay_plans(
        plans,
        executor=executor,
    )

    memory = SelfHardeningMemory()

    for certificate in certificates:
        memory.remember_failure(certificate)

    constraints: list[
        LearnedConstraint
    ] = []

    for result in replay_results:
        constraint = memory.promote(
            result.certificate_id,
            result.verdict,
        )

        constraints.append(constraint)

    return PromotionBatch(
        replay_results=replay_results,
        constraints=tuple(constraints),
    )


def promoted_constraints_document(
    constraints: tuple[
        LearnedConstraint,
        ...,
    ],
) -> dict:
    """
    Serialize governance memory.

    This document can never act as religious evidence.
    """

    return {
        "schema_version": "1",
        "principle": (
            "Basira does not learn beliefs; "
            "it learns constraints."
        ),
        "religious_evidence_authority": (
            MEMORY_EVIDENCE_AUTHORITY
        ),
        "constraints": [
            {
                "constraint_id": (
                    constraint.constraint_id
                ),
                "source_certificate_id": (
                    constraint.source_certificate_id
                ),
                "rule": constraint.rule,
                "replay_test_ids": list(
                    constraint.replay_test_ids
                ),
                "religious_evidence_authority": (
                    constraint.evidence_authority
                ),
            }
            for constraint in constraints
        ],
    }
