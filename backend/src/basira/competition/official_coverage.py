from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class OfficialDomain(StrEnum):
    QURAN = "quran"

    TAFSIR = "tafsir"

    HADITH = "hadith"

    AQEEDAH_INTRO_TO_ISLAM = (
        "aqeedah_intro_to_islam"
    )

    GENERAL_FIQH = "general_fiqh"

    SEERAH_HISTORY = "seerah_history"

    SHUBUHAT_FAQ = "shubuhat_faq"

    TRANSLATION_TERMINOLOGY = (
        "translation_terminology"
    )

    DAWAH_GENERAL_CONTENT = (
        "dawah_general_content"
    )

    AKHLAQ_VALUES_ADAB = (
        "akhlaq_values_adab"
    )

    RELIGIONS_SECTS_COMPARATIVE = (
        "religions_sects_comparative"
    )


class CoverageStatus(StrEnum):
    """
    Runtime coverage is deliberately distinct from merely
    knowing that an official source family exists.
    """

    GOVERNED_RUNTIME = "governed_runtime"

    GOVERNED_DISCOVERY_ONLY = (
        "governed_discovery_only"
    )

    GOVERNED_POLICY_ONLY = (
        "governed_policy_only"
    )

    APPROVED_FAMILY_NOT_IMPLEMENTED = (
        "approved_family_not_implemented"
    )

    NOT_COVERED = "not_covered"

    OUT_OF_SCOPE = "out_of_scope"


class OfficialDomainCoverage(BaseModel):
    domain: OfficialDomain

    official_source_rule: str

    status: CoverageStatus

    required_for_coverage_v1: bool = True

    runtime_source_ids: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    policy_artifacts: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    notes: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    generic_shamela_fallback_allowed: bool = False


class OfficialCoverageMatrix(BaseModel):
    schema_version: int

    matrix_id: str

    domains: tuple[
        OfficialDomainCoverage,
        ...
    ]

    global_invariants: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    out_of_scope: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )

    def get(
        self,
        domain: OfficialDomain,
    ) -> OfficialDomainCoverage:

        for item in self.domains:
            if item.domain is domain:
                return item

        raise KeyError(
            domain
        )

    def required_domains(
        self,
    ) -> tuple[
        OfficialDomainCoverage,
        ...
    ]:

        return tuple(
            item
            for item in self.domains
            if item.required_for_coverage_v1
        )

    def runtime_domains(
        self,
    ) -> tuple[
        OfficialDomainCoverage,
        ...
    ]:

        return tuple(
            item
            for item in self.domains
            if (
                item.status
                is CoverageStatus.GOVERNED_RUNTIME
            )
        )

    def incomplete_required_domains(
        self,
    ) -> tuple[
        OfficialDomainCoverage,
        ...
    ]:
        """
        Coverage V1 is not considered closed by policy alone.

        A required domain must have at least a governed
        discovery/runtime execution path.
        """

        accepted = {
            CoverageStatus.GOVERNED_RUNTIME,
            CoverageStatus.GOVERNED_DISCOVERY_ONLY,
        }

        return tuple(
            item
            for item in self.required_domains()
            if item.status not in accepted
        )

    @property
    def coverage_v1_ready(
        self,
    ) -> bool:

        return not (
            self.incomplete_required_domains()
        )


def load_official_coverage_matrix(
    path: Path,
) -> OfficialCoverageMatrix:

    return OfficialCoverageMatrix(
        **json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    )
