from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class SourceUsageRole(StrEnum):
    """
    What Basira is allowed to use a source for.

    A source may have several roles.

    Example:
        A dataset may be useful for evaluation,
        but must never be used as religious evidence.
    """

    CANONICAL_TEXT = "canonical_text"

    PRIMARY_EVIDENCE = "primary_evidence"

    SECONDARY_EVIDENCE = "secondary_evidence"

    CROSS_CHECK = "cross_check"

    RETRIEVAL_CORPUS = "retrieval_corpus"

    TRANSLATION = "translation"

    METADATA = "metadata"

    TRAINING = "training"

    EVALUATION = "evaluation"

    DISCOVERY_ONLY = "discovery_only"


class EvidenceAuthorityLevel(StrEnum):
    """
    Authority level is deliberately separate from
    source quality and dataset usefulness.

    Example:
        A high-quality academic benchmark may still
        have authority_level=NONE because Basira
        must not cite benchmark answers as religious
        rulings.
    """

    CANONICAL = "canonical"

    OFFICIAL_PRIMARY = "official_primary"

    ATTRIBUTED_SCHOLARLY = (
        "attributed_scholarly"
    )

    RESEARCH_CORPUS = "research_corpus"

    AGGREGATOR = "aggregator"

    BENCHMARK = "benchmark"

    UNVERIFIED = "unverified"

    NONE = "none"


class RuntimeUse(StrEnum):
    """
    Concrete operations Basira may perform using a
    source.

    These are stricter than broad source roles.
    """

    VERIFY_CANONICAL_TEXT = (
        "verify_canonical_text"
    )

    SUPPORT_ANSWER = "support_answer"

    CITE_TO_USER = "cite_to_user"

    RETRIEVE_PASSAGES = (
        "retrieve_passages"
    )

    CROSS_VALIDATE = "cross_validate"

    PROVIDE_TRANSLATION = (
        "provide_translation"
    )

    ENRICH_METADATA = "enrich_metadata"

    TRAIN_MODEL = "train_model"

    EVALUATE_MODEL = "evaluate_model"

    DISCOVER_SOURCES = "discover_sources"


class SourceUsagePolicy(BaseModel):
    """
    Runtime usage policy for one registered source.

    This object answers:

        "What is Basira allowed to do with this
        source?"

    It does NOT describe the source file hash,
    lifecycle status, or provenance itself.
    Those remain responsibilities of SourceManifest.
    """

    source_id: str = Field(
        min_length=1,
    )

    roles: frozenset[
        SourceUsageRole
    ]

    authority_level: (
        EvidenceAuthorityLevel
    )

    allowed_runtime_uses: frozenset[
        RuntimeUse
    ]

    requires_attribution: bool = True

    requires_human_review: bool = False

    notes: str | None = None

    @model_validator(
        mode="after"
    )
    def validate_safety_policy(
        self,
    ) -> SourceUsagePolicy:
        self._validate_canonical_text()
        self._validate_user_citation()
        self._validate_benchmark()
        self._validate_discovery_only()

        return self

    def _validate_canonical_text(
        self,
    ) -> None:
        if (
            RuntimeUse.VERIFY_CANONICAL_TEXT
            not in self.allowed_runtime_uses
        ):
            return

        if (
            SourceUsageRole.CANONICAL_TEXT
            not in self.roles
        ):
            raise ValueError(
                "VERIFY_CANONICAL_TEXT requires "
                "the CANONICAL_TEXT source role."
            )

        if self.authority_level not in {
            EvidenceAuthorityLevel.CANONICAL,
            EvidenceAuthorityLevel
            .OFFICIAL_PRIMARY,
        }:
            raise ValueError(
                "Canonical text verification "
                "requires canonical or official "
                "primary authority."
            )

    def _validate_user_citation(
        self,
    ) -> None:
        if (
            RuntimeUse.CITE_TO_USER
            not in self.allowed_runtime_uses
        ):
            return

        if self.authority_level in {
            EvidenceAuthorityLevel.NONE,
            EvidenceAuthorityLevel.BENCHMARK,
            EvidenceAuthorityLevel.UNVERIFIED,
        }:
            raise ValueError(
                "A benchmark, unverified, or "
                "non-authoritative source cannot "
                "be cited to the user as religious "
                "evidence."
            )

    def _validate_benchmark(
        self,
    ) -> None:
        if (
            self.authority_level
            != EvidenceAuthorityLevel.BENCHMARK
        ):
            return

        forbidden = {
            RuntimeUse.SUPPORT_ANSWER,
            RuntimeUse.CITE_TO_USER,
            RuntimeUse
            .VERIFY_CANONICAL_TEXT,
        }

        invalid = (
            self.allowed_runtime_uses
            & forbidden
        )

        if invalid:
            raise ValueError(
                "Benchmark sources cannot support "
                "religious answers, be cited as "
                "religious evidence, or verify "
                "canonical text."
            )

        if (
            RuntimeUse.EVALUATE_MODEL
            not in self.allowed_runtime_uses
        ):
            raise ValueError(
                "A BENCHMARK source must allow "
                "EVALUATE_MODEL."
            )

    def _validate_discovery_only(
        self,
    ) -> None:
        if (
            SourceUsageRole.DISCOVERY_ONLY
            not in self.roles
        ):
            return

        forbidden = {
            RuntimeUse.SUPPORT_ANSWER,
            RuntimeUse.CITE_TO_USER,
            RuntimeUse
            .VERIFY_CANONICAL_TEXT,
        }

        invalid = (
            self.allowed_runtime_uses
            & forbidden
        )

        if invalid:
            raise ValueError(
                "DISCOVERY_ONLY sources cannot "
                "directly support answers, be "
                "cited as religious evidence, or "
                "verify canonical text."
            )

    def allows(
        self,
        runtime_use: RuntimeUse,
    ) -> bool:
        return (
            runtime_use
            in self.allowed_runtime_uses
        )

    @property
    def may_support_answer(
        self,
    ) -> bool:
        return self.allows(
            RuntimeUse.SUPPORT_ANSWER
        )

    @property
    def may_be_cited(
        self,
    ) -> bool:
        return self.allows(
            RuntimeUse.CITE_TO_USER
        )

    @property
    def may_verify_canonical_text(
        self,
    ) -> bool:
        return self.allows(
            RuntimeUse
            .VERIFY_CANONICAL_TEXT
        )