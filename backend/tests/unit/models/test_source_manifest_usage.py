from __future__ import annotations

import pytest
from pydantic import ValidationError

from basira.models.source_manifest import (
    IntegrityStatus,
    SourceDomain,
    SourceManifest,
    SourceRole,
    SourceStatus,
)
from basira.models.source_usage import (
    EvidenceAuthorityLevel,
    RuntimeUse,
    SourceUsagePolicy,
    SourceUsageRole,
)


def _canonical_policy(
    source_id: str = "trusted-quran-source",
) -> SourceUsagePolicy:
    return SourceUsagePolicy(
        source_id=source_id,
        roles=frozenset(
            {
                SourceUsageRole.CANONICAL_TEXT,
                SourceUsageRole.PRIMARY_EVIDENCE,
                SourceUsageRole.CROSS_CHECK,
            }
        ),
        authority_level=(
            EvidenceAuthorityLevel.CANONICAL
        ),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.VERIFY_CANONICAL_TEXT,
                RuntimeUse.CROSS_VALIDATE,
                RuntimeUse.CITE_TO_USER,
                RuntimeUse.SUPPORT_ANSWER,
            }
        ),
    )


def _approved_manifest(
    *,
    source_id: str = "trusted-quran-source",
    usage_policy: SourceUsagePolicy | None = None,
) -> SourceManifest:
    return SourceManifest(
        source_id=source_id,
        source_name="Trusted Quran Source",
        domain=SourceDomain.QURAN,
        role=SourceRole.PRIMARY_CANONICAL,
        status=SourceStatus.APPROVED,
        integrity_status=IntegrityStatus.VERIFIED,
        usage_policy=usage_policy,
    )


def test_approved_verified_source_without_policy_has_no_runtime_permission() -> None:
    manifest = _approved_manifest()

    assert manifest.is_runtime_approved
    assert not manifest.has_usage_policy

    assert not manifest.allows_runtime_use(
        RuntimeUse.CITE_TO_USER
    )
    assert not manifest.allows_runtime_use(
        RuntimeUse.SUPPORT_ANSWER
    )
    assert not manifest.allows_runtime_use(
        RuntimeUse.VERIFY_CANONICAL_TEXT
    )

    assert not manifest.may_be_cited
    assert not manifest.may_support_answer
    assert not manifest.may_verify_canonical_text


def test_approved_verified_source_can_use_explicitly_allowed_operations() -> None:
    manifest = _approved_manifest(
        usage_policy=_canonical_policy()
    )

    assert manifest.is_runtime_approved
    assert manifest.has_usage_policy

    assert manifest.allows_runtime_use(
        RuntimeUse.VERIFY_CANONICAL_TEXT
    )
    assert manifest.allows_runtime_use(
        RuntimeUse.CROSS_VALIDATE
    )
    assert manifest.allows_runtime_use(
        RuntimeUse.CITE_TO_USER
    )
    assert manifest.allows_runtime_use(
        RuntimeUse.SUPPORT_ANSWER
    )

    assert manifest.may_verify_canonical_text
    assert manifest.may_be_cited
    assert manifest.may_support_answer


def test_usage_policy_does_not_override_pending_source_status() -> None:
    manifest = SourceManifest(
        source_id="trusted-quran-source",
        source_name="Trusted Quran Source",
        domain=SourceDomain.QURAN,
        role=SourceRole.PRIMARY_CANONICAL,
        status=SourceStatus.PENDING,
        integrity_status=IntegrityStatus.VERIFIED,
        usage_policy=_canonical_policy(),
    )

    assert not manifest.is_runtime_approved

    assert not manifest.allows_runtime_use(
        RuntimeUse.CITE_TO_USER
    )

    assert not manifest.allows_runtime_use(
        RuntimeUse.VERIFY_CANONICAL_TEXT
    )


def test_usage_policy_does_not_override_unverified_integrity() -> None:
    manifest = SourceManifest(
        source_id="trusted-quran-source",
        source_name="Trusted Quran Source",
        domain=SourceDomain.QURAN,
        role=SourceRole.PRIMARY_CANONICAL,
        status=SourceStatus.APPROVED,
        integrity_status=IntegrityStatus.REVIEW_REQUIRED,
        usage_policy=_canonical_policy(),
    )

    assert not manifest.is_runtime_approved

    assert not manifest.allows_runtime_use(
        RuntimeUse.SUPPORT_ANSWER
    )

    assert not manifest.allows_runtime_use(
        RuntimeUse.CITE_TO_USER
    )


def test_usage_policy_source_id_must_match_manifest_source_id() -> None:
    policy = _canonical_policy(
        source_id="different-source"
    )

    with pytest.raises(
        ValidationError,
        match=(
            "SourceUsagePolicy.source_id "
            "must match SourceManifest.source_id"
        ),
    ):
        _approved_manifest(
            source_id="trusted-quran-source",
            usage_policy=policy,
        )


def test_policy_permission_is_operation_specific() -> None:
    policy = SourceUsagePolicy(
        source_id="cross-check-source",
        roles=frozenset(
            {
                SourceUsageRole.CROSS_CHECK,
            }
        ),
        authority_level=(
            EvidenceAuthorityLevel.RESEARCH_CORPUS
        ),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.CROSS_VALIDATE,
            }
        ),
    )

    manifest = SourceManifest(
        source_id="cross-check-source",
        source_name="Cross Check Source",
        domain=SourceDomain.QURAN,
        role=SourceRole.INDEPENDENT_VERIFIER,
        status=SourceStatus.APPROVED,
        integrity_status=IntegrityStatus.VERIFIED,
        usage_policy=policy,
    )

    assert manifest.allows_runtime_use(
        RuntimeUse.CROSS_VALIDATE
    )

    assert not manifest.allows_runtime_use(
        RuntimeUse.CITE_TO_USER
    )

    assert not manifest.allows_runtime_use(
        RuntimeUse.SUPPORT_ANSWER
    )


def test_evaluation_source_can_run_evaluation_but_not_support_answers() -> None:
    policy = SourceUsagePolicy(
        source_id="evaluation-benchmark",
        roles=frozenset(
            {
                SourceUsageRole.EVALUATION,
            }
        ),
        authority_level=(
            EvidenceAuthorityLevel.BENCHMARK
        ),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.EVALUATE_MODEL,
            }
        ),
    )

    manifest = SourceManifest(
        source_id="evaluation-benchmark",
        source_name="Evaluation Benchmark",
        domain=SourceDomain.GENERAL,
        role=SourceRole.SECONDARY_REFERENCE,
        status=SourceStatus.APPROVED,
        integrity_status=IntegrityStatus.VERIFIED,
        usage_policy=policy,
    )

    assert manifest.is_runtime_approved

    assert manifest.allows_runtime_use(
        RuntimeUse.EVALUATE_MODEL
    )

    assert not manifest.allows_runtime_use(
        RuntimeUse.SUPPORT_ANSWER
    )

    assert not manifest.allows_runtime_use(
        RuntimeUse.CITE_TO_USER
    )

    assert not manifest.may_support_answer
    assert not manifest.may_be_cited


def test_quarantined_source_remains_blocked_even_with_canonical_policy() -> None:
    manifest = SourceManifest(
        source_id="trusted-quran-source",
        source_name="Trusted Quran Source",
        domain=SourceDomain.QURAN,
        role=SourceRole.PRIMARY_CANONICAL,
        status=SourceStatus.QUARANTINED,
        integrity_status=IntegrityStatus.VERIFIED,
        usage_policy=_canonical_policy(),
    )

    assert not manifest.is_runtime_approved

    assert not manifest.may_verify_canonical_text
    assert not manifest.may_be_cited
    assert not manifest.may_support_answer