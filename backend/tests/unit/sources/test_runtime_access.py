from __future__ import annotations

import pytest

from basira.models.source_manifest import (
    IntegrityStatus,
    SourceDomain,
    SourceManifest,
    SourceRole,
    SourceStatus,
)
from basira.models.source_usage import RuntimeUse
from basira.sources.registry import TrustedSourceRegistry
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
    SourceAccessReason,
    SourceRuntimeAccessDeniedError,
)


def _manifest(
    *,
    source_id: str,
    status: SourceStatus = SourceStatus.APPROVED,
    integrity_status: IntegrityStatus = (
        IntegrityStatus.VERIFIED
    ),
) -> SourceManifest:
    return SourceManifest(
        source_id=source_id,
        source_name=source_id,
        domain=SourceDomain.QURAN,
        role=SourceRole.INDEPENDENT_VERIFIER,
        status=status,
        integrity_status=integrity_status,
    )


def test_unknown_source_is_denied() -> None:
    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry()
    )

    decision = runtime.decide(
        source_id="unknown-source",
        runtime_use=RuntimeUse.CITE_TO_USER,
    )

    assert decision.denied
    assert not decision.allowed
    assert (
        decision.reason
        is SourceAccessReason.SOURCE_NOT_REGISTERED
    )


def test_registered_but_pending_source_is_denied() -> None:
    registry = TrustedSourceRegistry(
        [
            _manifest(
                source_id=(
                    "tanzil-quran-v1.1-uthmani"
                ),
                status=SourceStatus.PENDING,
            )
        ]
    )

    runtime = FailClosedSourceRuntime(
        registry
    )

    decision = runtime.decide(
        source_id=(
            "tanzil-quran-v1.1-uthmani"
        ),
        runtime_use=(
            RuntimeUse.VERIFY_CANONICAL_TEXT
        ),
    )

    assert decision.denied
    assert (
        decision.reason
        is SourceAccessReason.SOURCE_NOT_APPROVED
    )


def test_approved_but_unverified_source_is_denied() -> None:
    registry = TrustedSourceRegistry(
        [
            _manifest(
                source_id=(
                    "tanzil-quran-v1.1-uthmani"
                ),
                status=SourceStatus.APPROVED,
                integrity_status=(
                    IntegrityStatus
                    .REVIEW_REQUIRED
                ),
            )
        ]
    )

    runtime = FailClosedSourceRuntime(
        registry
    )

    decision = runtime.decide(
        source_id=(
            "tanzil-quran-v1.1-uthmani"
        ),
        runtime_use=(
            RuntimeUse.VERIFY_CANONICAL_TEXT
        ),
    )

    assert decision.denied

    assert (
        decision.reason
        is SourceAccessReason
        .INTEGRITY_NOT_VERIFIED
    )


def test_source_without_catalog_policy_is_denied() -> None:
    registry = TrustedSourceRegistry(
        [
            _manifest(
                source_id="new-unknown-source"
            )
        ]
    )

    runtime = FailClosedSourceRuntime(
        registry
    )

    decision = runtime.decide(
        source_id="new-unknown-source",
        runtime_use=RuntimeUse.RETRIEVE_PASSAGES,
    )

    assert decision.denied

    assert (
        decision.reason
        is SourceAccessReason.POLICY_NOT_FOUND
    )


def test_disallowed_runtime_operation_is_denied() -> None:
    registry = TrustedSourceRegistry(
        [
            _manifest(
                source_id=(
                    "tanzil-quran-v1.1-uthmani"
                )
            )
        ]
    )

    runtime = FailClosedSourceRuntime(
        registry
    )

    decision = runtime.decide(
        source_id=(
            "tanzil-quran-v1.1-uthmani"
        ),
        runtime_use=RuntimeUse.SUPPORT_ANSWER,
    )

    assert decision.denied

    assert (
        decision.reason
        is SourceAccessReason
        .RUNTIME_USE_NOT_ALLOWED
    )


def test_approved_verified_and_allowed_source_is_allowed() -> None:
    registry = TrustedSourceRegistry(
        [
            _manifest(
                source_id=(
                    "tanzil-quran-v1.1-uthmani"
                )
            )
        ]
    )

    runtime = FailClosedSourceRuntime(
        registry
    )

    decision = runtime.decide(
        source_id=(
            "tanzil-quran-v1.1-uthmani"
        ),
        runtime_use=(
            RuntimeUse.VERIFY_CANONICAL_TEXT
        ),
    )

    assert decision.allowed
    assert not decision.denied

    assert (
        decision.reason
        is SourceAccessReason.ALLOWED
    )


def test_kfgqpc_mirror_cannot_be_cited_even_if_manifest_is_approved() -> None:
    registry = TrustedSourceRegistry(
        [
            _manifest(
                source_id=(
                    "kfgqpc-hafs-mirror-v18"
                )
            )
        ]
    )

    runtime = FailClosedSourceRuntime(
        registry
    )

    decision = runtime.decide(
        source_id="kfgqpc-hafs-mirror-v18",
        runtime_use=RuntimeUse.CITE_TO_USER,
    )

    assert decision.denied

    assert (
        decision.reason
        is SourceAccessReason
        .RUNTIME_USE_NOT_ALLOWED
    )


def test_benchmark_cannot_support_answer() -> None:
    manifest = SourceManifest(
        source_id="islamic-faith-qa",
        source_name="Islamic Faith QA",
        domain=SourceDomain.GENERAL,
        role=SourceRole.SECONDARY_REFERENCE,
        status=SourceStatus.APPROVED,
        integrity_status=IntegrityStatus.VERIFIED,
    )

    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [manifest]
        )
    )

    decision = runtime.decide(
        source_id="islamic-faith-qa",
        runtime_use=RuntimeUse.SUPPORT_ANSWER,
    )

    assert decision.denied

    assert (
        decision.reason
        is SourceAccessReason
        .RUNTIME_USE_NOT_ALLOWED
    )


def test_benchmark_can_be_used_for_evaluation() -> None:
    manifest = SourceManifest(
        source_id="islamic-faith-qa",
        source_name="Islamic Faith QA",
        domain=SourceDomain.GENERAL,
        role=SourceRole.SECONDARY_REFERENCE,
        status=SourceStatus.APPROVED,
        integrity_status=IntegrityStatus.VERIFIED,
    )

    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [manifest]
        )
    )

    decision = runtime.decide(
        source_id="islamic-faith-qa",
        runtime_use=RuntimeUse.EVALUATE_MODEL,
    )

    assert decision.allowed

    assert (
        decision.reason
        is SourceAccessReason.ALLOWED
    )


def test_allows_returns_boolean() -> None:
    registry = TrustedSourceRegistry(
        [
            _manifest(
                source_id=(
                    "tanzil-quran-v1.1-uthmani"
                )
            )
        ]
    )

    runtime = FailClosedSourceRuntime(
        registry
    )

    assert runtime.allows(
        source_id=(
            "tanzil-quran-v1.1-uthmani"
        ),
        runtime_use=(
            RuntimeUse.VERIFY_CANONICAL_TEXT
        ),
    )

    assert not runtime.allows(
        source_id=(
            "tanzil-quran-v1.1-uthmani"
        ),
        runtime_use=RuntimeUse.SUPPORT_ANSWER,
    )


def test_require_returns_allowed_decision() -> None:
    registry = TrustedSourceRegistry(
        [
            _manifest(
                source_id=(
                    "tanzil-quran-v1.1-uthmani"
                )
            )
        ]
    )

    runtime = FailClosedSourceRuntime(
        registry
    )

    decision = runtime.require(
        source_id=(
            "tanzil-quran-v1.1-uthmani"
        ),
        runtime_use=(
            RuntimeUse.VERIFY_CANONICAL_TEXT
        ),
    )

    assert decision.allowed


def test_require_raises_with_structured_decision() -> None:
    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry()
    )

    with pytest.raises(
        SourceRuntimeAccessDeniedError
    ) as exc_info:
        runtime.require(
            source_id="unknown-source",
            runtime_use=RuntimeUse.CITE_TO_USER,
        )

    decision = exc_info.value.decision

    assert decision.denied

    assert (
        decision.reason
        is SourceAccessReason
        .SOURCE_NOT_REGISTERED
    )


def test_quranlab_pending_manifest_is_denied_before_policy_use() -> None:
    manifest = SourceManifest(
        source_id="quranlab-hadith",
        source_name="QuranLab Hadith Dataset",
        domain=SourceDomain.HADITH,
        role=SourceRole.SECONDARY_REFERENCE,
        status=SourceStatus.PENDING,
        integrity_status=IntegrityStatus.NOT_CHECKED,
    )

    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [manifest]
        )
    )

    decision = runtime.decide(
        source_id="quranlab-hadith",
        runtime_use=RuntimeUse.RETRIEVE_PASSAGES,
    )

    assert decision.denied
    assert (
        decision.reason
        is SourceAccessReason.SOURCE_NOT_APPROVED
    )


def test_quranlab_approved_but_unverified_manifest_is_denied() -> None:
    manifest = SourceManifest(
        source_id="quranlab-hadith",
        source_name="QuranLab Hadith Dataset",
        domain=SourceDomain.HADITH,
        role=SourceRole.SECONDARY_REFERENCE,
        status=SourceStatus.APPROVED,
        integrity_status=IntegrityStatus.NOT_CHECKED,
    )

    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [manifest]
        )
    )

    decision = runtime.decide(
        source_id="quranlab-hadith",
        runtime_use=RuntimeUse.RETRIEVE_PASSAGES,
    )

    assert decision.denied
    assert (
        decision.reason
        is SourceAccessReason.INTEGRITY_NOT_VERIFIED
    )


def test_quranlab_policy_still_blocks_user_citation_when_verified() -> None:
    manifest = SourceManifest(
        source_id="quranlab-hadith",
        source_name="QuranLab Hadith Dataset",
        domain=SourceDomain.HADITH,
        role=SourceRole.SECONDARY_REFERENCE,
        status=SourceStatus.APPROVED,
        integrity_status=IntegrityStatus.VERIFIED,
    )

    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [manifest]
        )
    )

    decision = runtime.decide(
        source_id="quranlab-hadith",
        runtime_use=RuntimeUse.CITE_TO_USER,
    )

    assert decision.denied
    assert (
        decision.reason
        is SourceAccessReason.RUNTIME_USE_NOT_ALLOWED
    )


def test_quranlab_retrieval_allowed_only_after_all_gates_pass() -> None:
    manifest = SourceManifest(
        source_id="quranlab-hadith",
        source_name="QuranLab Hadith Dataset",
        domain=SourceDomain.HADITH,
        role=SourceRole.SECONDARY_REFERENCE,
        status=SourceStatus.APPROVED,
        integrity_status=IntegrityStatus.VERIFIED,
    )

    runtime = FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [manifest]
        )
    )

    decision = runtime.decide(
        source_id="quranlab-hadith",
        runtime_use=RuntimeUse.RETRIEVE_PASSAGES,
    )

    assert decision.allowed
    assert decision.reason is SourceAccessReason.ALLOWED
