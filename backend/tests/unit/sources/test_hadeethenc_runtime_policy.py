from __future__ import annotations

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
    SourceUsageRole,
)
from basira.sources.policy_catalog import (
    get_source_usage_policy,
)
from basira.sources.registry import (
    TrustedSourceRegistry,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
    SourceAccessReason,
)

SOURCE_ID = "hadeethenc-official"


def manifest(
    *,
    status: SourceStatus = SourceStatus.APPROVED,
    integrity: IntegrityStatus = IntegrityStatus.VERIFIED,
) -> SourceManifest:
    return SourceManifest(
        source_id=SOURCE_ID,
        source_name=(
            "HadeethEnc Official Hadith Releases"
        ),
        domain=SourceDomain.HADITH,
        role=SourceRole.AUTHORITATIVE_REFERENCE,
        status=status,
        integrity_status=integrity,
    )


def runtime_for(
    source: SourceManifest,
) -> FailClosedSourceRuntime:
    return FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [source]
        )
    )


def test_hadeethenc_policy_is_attributed_scholarly() -> None:
    policy = get_source_usage_policy(
        SOURCE_ID
    )

    assert (
        policy.authority_level
        is EvidenceAuthorityLevel
        .ATTRIBUTED_SCHOLARLY
    )

    assert (
        SourceUsageRole.SECONDARY_EVIDENCE
        in policy.roles
    )

    assert (
        SourceUsageRole.CROSS_CHECK
        in policy.roles
    )

    assert policy.requires_attribution


def test_hadeethenc_policy_supports_answer_and_citation() -> None:
    policy = get_source_usage_policy(
        SOURCE_ID
    )

    assert policy.allows(
        RuntimeUse.SUPPORT_ANSWER
    )

    assert policy.allows(
        RuntimeUse.CITE_TO_USER
    )

    assert policy.allows(
        RuntimeUse.RETRIEVE_PASSAGES
    )

    assert policy.allows(
        RuntimeUse.CROSS_VALIDATE
    )

    assert policy.allows(
        RuntimeUse.PROVIDE_TRANSLATION
    )


def test_hadeethenc_cannot_verify_canonical_text() -> None:
    policy = get_source_usage_policy(
        SOURCE_ID
    )

    assert not policy.allows(
        RuntimeUse.VERIFY_CANONICAL_TEXT
    )


def test_hadeethenc_cannot_train_model_by_default() -> None:
    policy = get_source_usage_policy(
        SOURCE_ID
    )

    assert not policy.allows(
        RuntimeUse.TRAIN_MODEL
    )


def test_pending_hadeethenc_source_is_denied() -> None:
    runtime = runtime_for(
        manifest(
            status=SourceStatus.PENDING,
            integrity=IntegrityStatus.VERIFIED,
        )
    )

    decision = runtime.decide(
        source_id=SOURCE_ID,
        runtime_use=RuntimeUse.RETRIEVE_PASSAGES,
    )

    assert decision.denied

    assert (
        decision.reason
        is SourceAccessReason.SOURCE_NOT_APPROVED
    )


def test_unverified_hadeethenc_source_is_denied() -> None:
    runtime = runtime_for(
        manifest(
            status=SourceStatus.APPROVED,
            integrity=IntegrityStatus.NOT_CHECKED,
        )
    )

    decision = runtime.decide(
        source_id=SOURCE_ID,
        runtime_use=RuntimeUse.CITE_TO_USER,
    )

    assert decision.denied

    assert (
        decision.reason
        is SourceAccessReason.INTEGRITY_NOT_VERIFIED
    )


def test_verified_hadeethenc_source_may_support_answer() -> None:
    runtime = runtime_for(
        manifest()
    )

    decision = runtime.decide(
        source_id=SOURCE_ID,
        runtime_use=RuntimeUse.SUPPORT_ANSWER,
    )

    assert decision.allowed
    assert (
        decision.reason
        is SourceAccessReason.ALLOWED
    )


def test_verified_hadeethenc_source_may_be_cited() -> None:
    runtime = runtime_for(
        manifest()
    )

    decision = runtime.decide(
        source_id=SOURCE_ID,
        runtime_use=RuntimeUse.CITE_TO_USER,
    )

    assert decision.allowed
    assert (
        decision.reason
        is SourceAccessReason.ALLOWED
    )


def test_verified_hadeethenc_still_blocks_canonical_verification() -> None:
    runtime = runtime_for(
        manifest()
    )

    decision = runtime.decide(
        source_id=SOURCE_ID,
        runtime_use=(
            RuntimeUse.VERIFY_CANONICAL_TEXT
        ),
    )

    assert decision.denied

    assert (
        decision.reason
        is SourceAccessReason.RUNTIME_USE_NOT_ALLOWED
    )
