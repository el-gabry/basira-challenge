from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.models.source_manifest import (
    IntegrityStatus,
    SourceStatus,
)
from basira.models.source_usage import RuntimeUse
from basira.sources.policy_catalog import (
    SourceUsagePolicyNotFoundError,
    get_source_usage_policy,
)
from basira.sources.registry import TrustedSourceRegistry


class SourceAccessReason(StrEnum):
    """
    Machine-readable reason for a runtime source access decision.
    """

    ALLOWED = "allowed"

    SOURCE_NOT_REGISTERED = "source_not_registered"

    SOURCE_NOT_APPROVED = "source_not_approved"

    INTEGRITY_NOT_VERIFIED = "integrity_not_verified"

    POLICY_NOT_FOUND = "policy_not_found"

    RUNTIME_USE_NOT_ALLOWED = "runtime_use_not_allowed"


@dataclass(
    frozen=True,
    slots=True,
)
class SourceAccessDecision:
    """
    Structured fail-closed runtime access decision.

    A source is usable only when every required
    governance gate succeeds.
    """

    source_id: str
    runtime_use: RuntimeUse
    allowed: bool
    reason: SourceAccessReason

    @property
    def denied(self) -> bool:
        return not self.allowed


class FailClosedSourceRuntime:
    """
    Runtime source access gate for Basira.

    Decision order:

        1. Source must be registered.
        2. Source status must be APPROVED.
        3. Source integrity must be VERIFIED.
        4. Source must have a catalog policy.
        5. Requested RuntimeUse must be explicitly allowed.

    Any missing or failed condition produces DENY.

    The policy catalog is treated as the runtime
    policy authority. An embedded manifest policy
    cannot bypass catalog restrictions.
    """

    def __init__(
        self,
        registry: TrustedSourceRegistry,
    ) -> None:
        self._registry = registry

    def decide(
        self,
        *,
        source_id: str,
        runtime_use: RuntimeUse,
    ) -> SourceAccessDecision:
        """
        Evaluate whether a source may perform a
        requested runtime operation.
        """

        normalized_source_id = " ".join(
            source_id.split()
        )

        manifest = self._registry.get(
            normalized_source_id
        )

        if manifest is None:
            return SourceAccessDecision(
                source_id=normalized_source_id,
                runtime_use=runtime_use,
                allowed=False,
                reason=(
                    SourceAccessReason
                    .SOURCE_NOT_REGISTERED
                ),
            )

        if manifest.status is not SourceStatus.APPROVED:
            return SourceAccessDecision(
                source_id=normalized_source_id,
                runtime_use=runtime_use,
                allowed=False,
                reason=(
                    SourceAccessReason
                    .SOURCE_NOT_APPROVED
                ),
            )

        if (
            manifest.integrity_status
            is not IntegrityStatus.VERIFIED
        ):
            return SourceAccessDecision(
                source_id=normalized_source_id,
                runtime_use=runtime_use,
                allowed=False,
                reason=(
                    SourceAccessReason
                    .INTEGRITY_NOT_VERIFIED
                ),
            )

        try:
            policy = get_source_usage_policy(
                normalized_source_id
            )
        except SourceUsagePolicyNotFoundError:
            return SourceAccessDecision(
                source_id=normalized_source_id,
                runtime_use=runtime_use,
                allowed=False,
                reason=(
                    SourceAccessReason
                    .POLICY_NOT_FOUND
                ),
            )

        if not policy.allows(runtime_use):
            return SourceAccessDecision(
                source_id=normalized_source_id,
                runtime_use=runtime_use,
                allowed=False,
                reason=(
                    SourceAccessReason
                    .RUNTIME_USE_NOT_ALLOWED
                ),
            )

        return SourceAccessDecision(
            source_id=normalized_source_id,
            runtime_use=runtime_use,
            allowed=True,
            reason=SourceAccessReason.ALLOWED,
        )

    def allows(
        self,
        *,
        source_id: str,
        runtime_use: RuntimeUse,
    ) -> bool:
        """
        Convenience boolean wrapper around decide().
        """

        return self.decide(
            source_id=source_id,
            runtime_use=runtime_use,
        ).allowed

    def require(
        self,
        *,
        source_id: str,
        runtime_use: RuntimeUse,
    ) -> SourceAccessDecision:
        """
        Return an allowed decision or raise
        SourceRuntimeAccessDeniedError.
        """

        decision = self.decide(
            source_id=source_id,
            runtime_use=runtime_use,
        )

        if decision.denied:
            raise SourceRuntimeAccessDeniedError(
                decision
            )

        return decision


class SourceRuntimeAccessDeniedError(
    PermissionError
):
    """
    Raised when fail-closed source access is denied.
    """

    def __init__(
        self,
        decision: SourceAccessDecision,
    ) -> None:
        self.decision = decision

        super().__init__(
            "Runtime source access denied: "
            f"source='{decision.source_id}', "
            f"use='{decision.runtime_use.value}', "
            f"reason='{decision.reason.value}'."
        )
