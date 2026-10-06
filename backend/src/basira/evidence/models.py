from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EvidenceDomain(StrEnum):
    QURAN = "quran"
    HADITH = "hadith"
    TAFSIR = "tafsir"
    REVELATION_CONTEXT = "revelation_context"
    FIQH = "fiqh"
    FATWA = "fatwa"
    AQIDAH = "aqidah"
    SIRA = "sira"
    HISTORY = "history"
    LANGUAGE = "language"

    GENERAL = "general"


class EvidenceNeed(StrEnum):
    """
    Evidence capabilities that a retrieval plan may
    require.

    These describe what evidence is needed, not which
    source must provide it.
    """

    CANONICAL_TEXT = "canonical_text"
    SURROUNDING_CONTEXT = "surrounding_context"

    HADITH_TEXT = "hadith_text"
    HADITH_GRADE = "hadith_grade"

    TAFSIR = "tafsir"
    REVELATION_CONTEXT = "revelation_context"
    RELATED_HADITH = "related_hadith"

    FIQH_EVIDENCE = "fiqh_evidence"

    # Legacy aggregate constraint need. Kept for
    # backwards compatibility, but precise Fiqh routes
    # also require the typed needs below.
    FIQH_CONSTRAINTS = "fiqh_constraints"

    FIQH_MADHHAB_SCOPE = (
        "fiqh_madhhab_scope"
    )

    FIQH_CONDITIONS = (
        "fiqh_conditions"
    )

    FIQH_EXCEPTIONS = (
        "fiqh_exceptions"
    )

    FIQH_DISAGREEMENT = (
        "fiqh_disagreement"
    )

    ACTOR_AUTHORITY = "actor_authority"
    APPLICABILITY_CONDITIONS = "applicability_conditions"

    CONTEMPORARY_GUIDANCE = "contemporary_guidance"

    TRANSLATION = "translation"
    SOURCE_PROVENANCE = "source_provenance"


@dataclass(
    frozen=True,
    slots=True,
)
class ContextRequirement:
    """
    Evidence requirements for one user request.

    Baseline RAG initially uses this for planning.

    During the protected Basira pipeline this same
    object will become enforceable by a context
    completeness validator.
    """

    required: frozenset[EvidenceNeed] = field(default_factory=frozenset)

    optional: frozenset[EvidenceNeed] = field(default_factory=frozenset)

    def requires(
        self,
        need: EvidenceNeed,
    ) -> bool:
        return need in self.required

    def requests(
        self,
        need: EvidenceNeed,
    ) -> bool:
        return need in self.required or need in self.optional


@dataclass(
    frozen=True,
    slots=True,
)
class EvidenceNode:
    """
    Unified evidence contract consumed by the future
    RAG layer.

    Empty context fields are valid in the baseline.
    The protected pipeline will later require selected
    fields according to ContextRequirement.
    """

    evidence_id: str

    domain: EvidenceDomain

    text: str

    source_id: str

    source_version: str | None = None

    reference: str | None = None

    source_url: str | None = None

    work_id: str | None = None
    work_title: str | None = None
    author_name: str | None = None
    institution: str | None = None
    publisher: str | None = None

    volume: str | None = None
    page: str | None = None

    topic: str | None = None

    claim_type: str | None = None

    historical_context: str | None = None

    applicability: str | None = None

    restrictions: tuple[
        str,
        ...,
    ] = ()

    authority_scope: str | None = None

    related_quran: tuple[
        str,
        ...,
    ] = ()

    related_hadith: tuple[
        str,
        ...,
    ] = ()

    related_tafsir: tuple[
        str,
        ...,
    ] = ()

    related_fiqh: tuple[
        str,
        ...,
    ] = ()

    conflict_group: str | None = None

    conflict_type: str | None = None
