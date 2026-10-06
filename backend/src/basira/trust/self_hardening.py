"""
Deterministic Self-Hardening Memory for Basira.

Core invariant:

    Basira does not learn beliefs.
    Basira learns constraints.

Artifacts stored here have ZERO religious-evidence authority.
They may influence safety / governance rules only after
successful counterfactual regression replay.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

MEMORY_EVIDENCE_AUTHORITY = 0


class FailureKind(StrEnum):
    TYPED_ROLE_SPOOFING = "typed_role_spoofing"
    ROLE_LAUNDERING = "role_laundering"
    PUBLICATION_AUTHORITY_FORGERY = (
        "publication_authority_forgery"
    )
    SOURCE_DOMAIN_IDENTITY_SPOOFING = (
        "source_domain_identity_spoofing"
    )
    QURAN_VERIFICATION_INTENT_FALLTHROUGH = (
        "quran_verification_intent_fallthrough"
    )


class FailureDisposition(StrEnum):
    REPAIRABLE_SYSTEM_FAILURE = (
        "repairable_system_failure"
    )
    PROTECTED_DISAGREEMENT = "protected_disagreement"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNRESOLVED = "unresolved"


class RepairPromotionError(RuntimeError):
    """Raised when a repair is not safe to promote."""


@dataclass(frozen=True, slots=True)
class FailureCertificate:
    certificate_id: str
    failure_kind: FailureKind
    disposition: FailureDisposition
    observed_failure: str
    violated_invariant: str
    repair_constraint: str
    replay_test_ids: tuple[str, ...]

    @property
    def evidence_authority(self) -> int:
        return MEMORY_EVIDENCE_AUTHORITY

    @property
    def can_support_religious_claim(self) -> bool:
        return False

    def __post_init__(self) -> None:
        required = (
            self.certificate_id,
            self.observed_failure,
            self.violated_invariant,
            self.repair_constraint,
        )

        if any(not value.strip() for value in required):
            raise ValueError(
                "failure certificate fields must not be blank"
            )

        if not self.replay_test_ids:
            raise ValueError(
                "failure certificate requires replay tests"
            )


@dataclass(frozen=True, slots=True)
class ReplayVerdict:
    """
    Counterfactual replay result.

    Promotion requires:
    - the original attack is blocked;
    - valid controls still pass;
    - wider regression remains green.
    """

    attack_blocked: bool
    valid_controls_passed: bool
    regression_passed: bool

    @property
    def safe_to_promote(self) -> bool:
        return (
            self.attack_blocked
            and self.valid_controls_passed
            and self.regression_passed
        )


@dataclass(frozen=True, slots=True)
class LearnedConstraint:
    """
    A promoted safety constraint.

    This is governance memory, never religious evidence.
    """

    constraint_id: str
    source_certificate_id: str
    rule: str
    replay_test_ids: tuple[str, ...]

    @property
    def evidence_authority(self) -> int:
        return MEMORY_EVIDENCE_AUTHORITY

    @property
    def can_support_religious_claim(self) -> bool:
        return False


def promote_failure(
    certificate: FailureCertificate,
    verdict: ReplayVerdict,
) -> LearnedConstraint:
    """
    Promote only verified repairable system failures.

    Scholarly disagreement, insufficient evidence, and
    unresolved cases must never become learned repairs.
    """

    if (
        certificate.disposition
        is not FailureDisposition.REPAIRABLE_SYSTEM_FAILURE
    ):
        raise RepairPromotionError(
            "only repairable system failures may be promoted"
        )

    if not verdict.safe_to_promote:
        raise RepairPromotionError(
            "counterfactual replay did not pass all gates"
        )

    return LearnedConstraint(
        constraint_id=(
            "constraint:"
            + certificate.certificate_id
        ),
        source_certificate_id=certificate.certificate_id,
        rule=certificate.repair_constraint,
        replay_test_ids=certificate.replay_test_ids,
    )


class SelfHardeningMemory:
    """
    Deterministic append-only logical memory.

    It stores failure certificates and promoted constraints.
    It does not expose any evidence-authority interface.
    """

    def __init__(self) -> None:
        self._certificates: dict[
            str,
            FailureCertificate,
        ] = {}

        self._constraints: dict[
            str,
            LearnedConstraint,
        ] = {}

    def remember_failure(
        self,
        certificate: FailureCertificate,
    ) -> None:
        existing = self._certificates.get(
            certificate.certificate_id
        )

        if (
            existing is not None
            and existing != certificate
        ):
            raise ValueError(
                "failure certificate identity collision"
            )

        self._certificates[
            certificate.certificate_id
        ] = certificate

    def promote(
        self,
        certificate_id: str,
        verdict: ReplayVerdict,
    ) -> LearnedConstraint:
        certificate = self._certificates[
            certificate_id
        ]

        constraint = promote_failure(
            certificate,
            verdict,
        )

        existing = self._constraints.get(
            constraint.constraint_id
        )

        if (
            existing is not None
            and existing != constraint
        ):
            raise ValueError(
                "learned constraint identity collision"
            )

        self._constraints[
            constraint.constraint_id
        ] = constraint

        return constraint

    def certificates(
        self,
    ) -> tuple[FailureCertificate, ...]:
        return tuple(
            self._certificates.values()
        )

    def constraints(
        self,
    ) -> tuple[LearnedConstraint, ...]:
        return tuple(
            self._constraints.values()
        )


def load_failure_certificates(
    path: Path,
) -> tuple[FailureCertificate, ...]:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    records = payload.get("certificates")

    if not isinstance(records, list):
        raise ValueError(
            "failure certificate document requires certificates"
        )

    result: list[FailureCertificate] = []

    for record in records:
        result.append(
            FailureCertificate(
                certificate_id=record["certificate_id"],
                failure_kind=FailureKind(
                    record["failure_kind"]
                ),
                disposition=FailureDisposition(
                    record["disposition"]
                ),
                observed_failure=record["observed_failure"],
                violated_invariant=record[
                    "violated_invariant"
                ],
                repair_constraint=record[
                    "repair_constraint"
                ],
                replay_test_ids=tuple(
                    record["replay_test_ids"]
                ),
            )
        )

    return tuple(result)
