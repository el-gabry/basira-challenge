from basira.competition.source_trust import (
    ReleaseRelation,
    SourceFreshnessState,
    SourceUpdateSentinel,
)


def test_same_release_same_hash_is_current() -> None:
    result = SourceUpdateSentinel().assess(
        source_id="quran:test",
        governed_release="2026-10-04",
        observed_release="2026-10-04",
        release_relation=ReleaseRelation.SAME,
        current_artifact_sha256="a" * 64,
        observed_artifact_sha256="a" * 64,
    )

    assert (
        result.freshness
        is SourceFreshnessState.CURRENT
    )

    assert result.auto_promote is False
    assert result.keep_governed_snapshot is True


def test_newer_release_is_candidate_only() -> None:
    result = SourceUpdateSentinel().assess(
        source_id="quran:test",
        governed_release="2026-10-04",
        observed_release="2026-10-05",
        release_relation=ReleaseRelation.NEWER,
    )

    assert (
        result.freshness
        is SourceFreshnessState.UPDATE_AVAILABLE
    )

    assert result.auto_promote is False

    assert (
        "candidate_requires_reverification"
        in result.reasons
    )


def test_older_release_is_not_called_update() -> None:
    result = SourceUpdateSentinel().assess(
        source_id="quran:test",
        governed_release="2026-10-04",
        observed_release="2026-10-03",
        release_relation=ReleaseRelation.OLDER,
    )

    assert (
        result.freshness
        is SourceFreshnessState.OLDER_PROVIDER_VIEW
    )

    assert result.auto_promote is False
    assert result.keep_governed_snapshot is True

    assert (
        "possible_cache_or_provider_rollback"
        in result.reasons
    )


def test_same_release_changed_hash_is_drift() -> None:
    result = SourceUpdateSentinel().assess(
        source_id="quran:test",
        governed_release="2026-10-04",
        observed_release="2026-10-04",
        release_relation=ReleaseRelation.SAME,
        current_artifact_sha256="a" * 64,
        observed_artifact_sha256="b" * 64,
    )

    assert (
        result.freshness
        is SourceFreshnessState
        .SAME_RELEASE_ARTIFACT_DRIFT
    )

    assert result.auto_promote is False


def test_unordered_release_change_fails_safe() -> None:
    result = SourceUpdateSentinel().assess(
        source_id="source:test",
        governed_release="release-alpha",
        observed_release="release-beta",
        release_relation=ReleaseRelation.UNORDERED,
    )

    assert (
        result.freshness
        is SourceFreshnessState
        .RELEASE_CHANGE_UNORDERED
    )

    assert result.keep_governed_snapshot is True


def test_provider_failure_keeps_governed_snapshot() -> None:
    result = SourceUpdateSentinel().assess(
        source_id="quran:test",
        governed_release="2026-10-04",
        observed_release=None,
        release_relation=None,
    )

    assert (
        result.freshness
        is SourceFreshnessState
        .PROVIDER_UNAVAILABLE
    )

    assert result.keep_governed_snapshot is True
