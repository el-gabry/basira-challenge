import pytest
from pydantic import ValidationError

from basira.models.source_usage import (
    EvidenceAuthorityLevel,
    RuntimeUse,
    SourceUsagePolicy,
    SourceUsageRole,
)


def test_canonical_source_can_verify_text() -> None:
    policy = SourceUsagePolicy(
        source_id="official-quran-source",
        roles=frozenset(
            {
                SourceUsageRole.CANONICAL_TEXT,
                SourceUsageRole.PRIMARY_EVIDENCE,
            }
        ),
        authority_level=(
            EvidenceAuthorityLevel.CANONICAL
        ),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse
                .VERIFY_CANONICAL_TEXT,
                RuntimeUse.CROSS_VALIDATE,
                RuntimeUse.CITE_TO_USER,
            }
        ),
    )

    assert (
        policy.may_verify_canonical_text
    )

    assert policy.may_be_cited


def test_canonical_verification_requires_canonical_role() -> None:
    with pytest.raises(
        ValidationError,
        match="CANONICAL_TEXT",
    ):
        SourceUsagePolicy(
            source_id="bad-source",
            roles=frozenset(
                {
                    SourceUsageRole
                    .CROSS_CHECK,
                }
            ),
            authority_level=(
                EvidenceAuthorityLevel
                .CANONICAL
            ),
            allowed_runtime_uses=frozenset(
                {
                    RuntimeUse
                    .VERIFY_CANONICAL_TEXT,
                }
            ),
        )


def test_benchmark_can_evaluate_model() -> None:
    policy = SourceUsagePolicy(
        source_id="benchmark-source",
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

    assert policy.allows(
        RuntimeUse.EVALUATE_MODEL
    )

    assert not policy.may_be_cited
    assert not policy.may_support_answer


def test_benchmark_cannot_support_religious_answer() -> None:
    with pytest.raises(
        ValidationError,
        match="Benchmark sources cannot",
    ):
        SourceUsagePolicy(
            source_id="benchmark-source",
            roles=frozenset(
                {
                    SourceUsageRole.EVALUATION,
                }
            ),
            authority_level=(
                EvidenceAuthorityLevel
                .BENCHMARK
            ),
            allowed_runtime_uses=frozenset(
                {
                    RuntimeUse.EVALUATE_MODEL,
                    RuntimeUse.SUPPORT_ANSWER,
                }
            ),
        )


def test_benchmark_cannot_be_cited_as_evidence() -> None:
    with pytest.raises(
        ValidationError,
    ):
        SourceUsagePolicy(
            source_id="benchmark-source",
            roles=frozenset(
                {
                    SourceUsageRole.EVALUATION,
                }
            ),
            authority_level=(
                EvidenceAuthorityLevel
                .BENCHMARK
            ),
            allowed_runtime_uses=frozenset(
                {
                    RuntimeUse.EVALUATE_MODEL,
                    RuntimeUse.CITE_TO_USER,
                }
            ),
        )


def test_discovery_only_source_is_restricted() -> None:
    policy = SourceUsagePolicy(
        source_id="aggregator",
        roles=frozenset(
            {
                SourceUsageRole.DISCOVERY_ONLY,
                SourceUsageRole.METADATA,
            }
        ),
        authority_level=(
            EvidenceAuthorityLevel.AGGREGATOR
        ),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse.DISCOVER_SOURCES,
                RuntimeUse.ENRICH_METADATA,
            }
        ),
    )

    assert policy.allows(
        RuntimeUse.DISCOVER_SOURCES
    )

    assert not policy.may_support_answer
    assert not policy.may_be_cited


def test_discovery_only_source_cannot_support_answer() -> None:
    with pytest.raises(
        ValidationError,
        match="DISCOVERY_ONLY",
    ):
        SourceUsagePolicy(
            source_id="aggregator",
            roles=frozenset(
                {
                    SourceUsageRole
                    .DISCOVERY_ONLY,
                }
            ),
            authority_level=(
                EvidenceAuthorityLevel
                .AGGREGATOR
            ),
            allowed_runtime_uses=frozenset(
                {
                    RuntimeUse
                    .DISCOVER_SOURCES,
                    RuntimeUse.SUPPORT_ANSWER,
                }
            ),
        )


def test_research_corpus_can_be_retrieval_only() -> None:
    policy = SourceUsagePolicy(
        source_id="research-corpus",
        roles=frozenset(
            {
                SourceUsageRole
                .RETRIEVAL_CORPUS,
                SourceUsageRole.METADATA,
            }
        ),
        authority_level=(
            EvidenceAuthorityLevel
            .RESEARCH_CORPUS
        ),
        allowed_runtime_uses=frozenset(
            {
                RuntimeUse
                .RETRIEVE_PASSAGES,
                RuntimeUse
                .ENRICH_METADATA,
            }
        ),
    )

    assert policy.allows(
        RuntimeUse.RETRIEVE_PASSAGES
    )

    assert not policy.may_support_answer
    assert not policy.may_be_cited


def test_unverified_source_cannot_be_cited() -> None:
    with pytest.raises(
        ValidationError,
        match="cannot be cited",
    ):
        SourceUsagePolicy(
            source_id="unknown-source",
            roles=frozenset(
                {
                    SourceUsageRole
                    .RETRIEVAL_CORPUS,
                }
            ),
            authority_level=(
                EvidenceAuthorityLevel
                .UNVERIFIED
            ),
            allowed_runtime_uses=frozenset(
                {
                    RuntimeUse
                    .CITE_TO_USER,
                }
            ),
        )