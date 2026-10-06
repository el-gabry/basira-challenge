from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ReleaseRelation(StrEnum):
    SAME = "same"
    NEWER = "newer"
    OLDER = "older"
    UNORDERED = "unordered"


class SourceFreshnessState(StrEnum):
    CURRENT = "current"

    UPDATE_AVAILABLE = "update_available"

    OLDER_PROVIDER_VIEW = "older_provider_view"

    SAME_RELEASE_ARTIFACT_DRIFT = (
        "same_release_artifact_drift"
    )

    RELEASE_CHANGE_UNORDERED = (
        "release_change_unordered"
    )

    PROVIDER_UNAVAILABLE = (
        "provider_unavailable"
    )


class CrossSourceRelation(StrEnum):
    NOT_CHECKED = "not_checked"

    INDEPENDENT_ATTESTATION = (
        "independent_attestation"
    )

    CORRELATED_CONFIRMATION = (
        "correlated_confirmation"
    )

    VALID_VARIANT = "valid_variant"

    CONFLICT = "conflict"

    UNRESOLVED = "unresolved"


class SourceUpdateAssessment(BaseModel):
    source_id: str

    governed_release: str

    observed_release: str | None

    release_relation: ReleaseRelation | None

    freshness: SourceFreshnessState

    current_artifact_sha256: str | None = None

    observed_artifact_sha256: str | None = None

    auto_promote: bool = False

    keep_governed_snapshot: bool = True

    reasons: tuple[str, ...]


class SourceUpdateSentinel:
    """
    Fail-safe source freshness policy.

    IMPORTANT:
    A release identifier changing does NOT imply that the
    observed release is newer.

    Ordering belongs to a provider-specific release adapter.

    The sentinel only decides what to do after that relation
    has been established.
    """

    def assess(
        self,
        *,
        source_id: str,
        governed_release: str,
        observed_release: str | None,
        release_relation: ReleaseRelation | None,
        current_artifact_sha256: str | None = None,
        observed_artifact_sha256: str | None = None,
    ) -> SourceUpdateAssessment:

        if observed_release is None:
            return SourceUpdateAssessment(
                source_id=source_id,
                governed_release=governed_release,
                observed_release=None,
                release_relation=None,
                freshness=(
                    SourceFreshnessState
                    .PROVIDER_UNAVAILABLE
                ),
                current_artifact_sha256=(
                    current_artifact_sha256
                ),
                observed_artifact_sha256=None,
                auto_promote=False,
                keep_governed_snapshot=True,
                reasons=(
                    "provider_release_unavailable",
                    "keep_last_governed_snapshot",
                ),
            )

        if release_relation is ReleaseRelation.NEWER:
            return SourceUpdateAssessment(
                source_id=source_id,
                governed_release=governed_release,
                observed_release=observed_release,
                release_relation=release_relation,
                freshness=(
                    SourceFreshnessState
                    .UPDATE_AVAILABLE
                ),
                current_artifact_sha256=(
                    current_artifact_sha256
                ),
                observed_artifact_sha256=(
                    observed_artifact_sha256
                ),
                auto_promote=False,
                keep_governed_snapshot=True,
                reasons=(
                    "newer_provider_release_detected",
                    "candidate_requires_reverification",
                ),
            )

        if release_relation is ReleaseRelation.OLDER:
            return SourceUpdateAssessment(
                source_id=source_id,
                governed_release=governed_release,
                observed_release=observed_release,
                release_relation=release_relation,
                freshness=(
                    SourceFreshnessState
                    .OLDER_PROVIDER_VIEW
                ),
                current_artifact_sha256=(
                    current_artifact_sha256
                ),
                observed_artifact_sha256=(
                    observed_artifact_sha256
                ),
                auto_promote=False,
                keep_governed_snapshot=True,
                reasons=(
                    "provider_exposed_older_release",
                    "possible_cache_or_provider_rollback",
                    "keep_last_governed_snapshot",
                ),
            )

        if release_relation is ReleaseRelation.UNORDERED:
            return SourceUpdateAssessment(
                source_id=source_id,
                governed_release=governed_release,
                observed_release=observed_release,
                release_relation=release_relation,
                freshness=(
                    SourceFreshnessState
                    .RELEASE_CHANGE_UNORDERED
                ),
                current_artifact_sha256=(
                    current_artifact_sha256
                ),
                observed_artifact_sha256=(
                    observed_artifact_sha256
                ),
                auto_promote=False,
                keep_governed_snapshot=True,
                reasons=(
                    "release_changed_but_order_unknown",
                    "manual_or_provider_specific_ordering_required",
                ),
            )

        if release_relation is not ReleaseRelation.SAME:
            raise ValueError(
                "release_relation is required when "
                "an observed release is available"
            )

        if observed_release != governed_release:
            raise ValueError(
                "SAME release relation requires equal release IDs"
            )

        if (
            current_artifact_sha256
            and observed_artifact_sha256
            and (
                current_artifact_sha256
                != observed_artifact_sha256
            )
        ):
            return SourceUpdateAssessment(
                source_id=source_id,
                governed_release=governed_release,
                observed_release=observed_release,
                release_relation=release_relation,
                freshness=(
                    SourceFreshnessState
                    .SAME_RELEASE_ARTIFACT_DRIFT
                ),
                current_artifact_sha256=(
                    current_artifact_sha256
                ),
                observed_artifact_sha256=(
                    observed_artifact_sha256
                ),
                auto_promote=False,
                keep_governed_snapshot=True,
                reasons=(
                    "same_release_hash_changed",
                    "quarantine_candidate",
                ),
            )

        return SourceUpdateAssessment(
            source_id=source_id,
            governed_release=governed_release,
            observed_release=observed_release,
            release_relation=release_relation,
            freshness=SourceFreshnessState.CURRENT,
            current_artifact_sha256=(
                current_artifact_sha256
            ),
            observed_artifact_sha256=(
                observed_artifact_sha256
            ),
            auto_promote=False,
            keep_governed_snapshot=True,
            reasons=(
                "governed_release_matches_provider",
            ),
        )
