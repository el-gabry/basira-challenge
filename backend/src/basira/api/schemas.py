from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class QueryRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )

    quran_reference: str | None = Field(
        default=None,
        pattern=r"^\d{1,3}:\d{1,3}$",
    )

    language: str = Field(
        default="ar",
        pattern=r"^(ar|en)$",
    )

    @field_validator("question")
    @classmethod
    def normalize_question(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError("Question must not be blank.")

        return normalized


class QueryEntityResponse(BaseModel):
    entity_type: str
    value: str


class RequirementResponse(BaseModel):
    need: str
    state: str

    evidence_ids: list[str] = Field(default_factory=list)


class SourceVerificationResponse(BaseModel):
    status: str
    verified_at: str
    reverify_after_seconds: int = 86400
    methods: list[str] = Field(default_factory=list)


class CitationResponse(BaseModel):
    marker: str

    evidence_id: str
    domain: str
    source_id: str

    source_version: str | None = None
    reference: str | None = None
    source_url: str | None = None

    work_title: str | None = None
    author_name: str | None = None
    institution: str | None = None
    publisher: str | None = None

    source_verification: SourceVerificationResponse | None = None


class LocalizedEvidenceResponse(BaseModel):
    """
    Source-native presentation companion.

    This representation does not replace the canonical
    evidence identity used by reasoning or publication.
    """

    language: str

    evidence_id: str
    claim_type: str

    text: str

    source_id: str
    source_version: str | None = None

    reference: str | None = None
    source_url: str | None = None

    work_title: str | None = None
    authority_scope: str | None = None

    source_verification: SourceVerificationResponse | None = None


class EvidenceResponse(BaseModel):
    evidence_id: str

    domain: str

    source_id: str
    source_version: str | None = None

    reference: str | None = None
    source_url: str | None = None

    work_title: str | None = None
    author_name: str | None = None
    institution: str | None = None
    publisher: str | None = None

    source_verification: SourceVerificationResponse | None = None

    localized: LocalizedEvidenceResponse | None = None

    claim_type: str | None = None

    authority_scope: str | None = None
    conflict_group: str | None = None
    conflict_type: str | None = None

    # Provenance relation only. This does not grant publication
    # authority to the related evidence and does not weaken the
    # evidence-text display gate.
    related_hadith: list[str] = Field(default_factory=list)

    # Short structured claim value. This is deliberately
    # narrower than full evidence text; currently only
    # publishable Hadith grade claims may populate it.
    claim_value: str | None = None

    used_in_answer: bool = False

    # Only evidence already authorized and selected by
    # GroundedAnswerComposer may expose full user-facing text.
    text: str | None = None

    # Short verbatim preview for supporting evidence.
    # The presenter exposes this only after the same
    # fail-closed publication policy used by composition.
    display_excerpt: str | None = None


class EvidenceDetailResponse(BaseModel):
    evidence_id: str
    domain: str

    source_id: str
    source_version: str | None = None

    reference: str | None = None
    source_url: str | None = None

    work_title: str | None = None
    author_name: str | None = None
    institution: str | None = None
    publisher: str | None = None

    text: str


class ContextRequirementResponse(BaseModel):
    required: list[str] = Field(default_factory=list)

    optional: list[str] = Field(default_factory=list)


class UnderstandingResponse(BaseModel):
    intent: str

    risk_tags: list[str] = Field(default_factory=list)

    entities: list[QueryEntityResponse] = Field(default_factory=list)

    context_requirement: ContextRequirementResponse

    confidence: float


class StructuredClaimResponse(BaseModel):
    """
    Claim-level provenance contract.

    evidence_ids are provenance links only.
    They do not imply semantic entailment.
    """

    axis_id: str

    claim_id: str

    text: str

    evidence_ids: list[str] = Field(default_factory=list)


class IntegrityReportResponse(BaseModel):
    """
    Deterministic answer-integrity summary.

    This does not represent semantic claim
    verification.
    """

    literal_source_integrity: str

    claims_checked: int

    claim_ids: list[str] = Field(default_factory=list)

    linked_evidence_ids: list[str] = Field(default_factory=list)

    has_limitations: bool

    limitation_count: int

    potential_source_conflict: bool

    conflict_count: int

    conflict_types: list[str] = Field(default_factory=list)

    conflict_group_ids: list[str] = Field(default_factory=list)

    semantic_claim_verification: str
    semantic_verification_issues: list[str] = Field(default_factory=list)


class ConflictResponse(BaseModel):
    type: str

    group_id: str

    evidence_ids: list[str] = Field(default_factory=list)


class ExperienceTraceStepResponse(BaseModel):
    key: str
    label: str
    status: str
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class ExperienceResponse(BaseModel):
    state: str
    severity: str
    label: str
    headline: str
    detail: str
    can_publish: bool
    evidence_count: int
    used_evidence_count: int
    source_count: int
    trace: list[ExperienceTraceStepResponse] = Field(default_factory=list)


class QuranDifferenceResponse(BaseModel):
    kind: str

    expected: list[str] = Field(default_factory=list)

    received: list[str] = Field(default_factory=list)

    is_substantive: bool


class QuranVerificationCandidateResponse(BaseModel):
    reference: str

    canonical_text: str

    source_id: str

    score: float


class QuranVerificationResponse(BaseModel):
    status: str

    input_text: str

    candidates: list[QuranVerificationCandidateResponse] = Field(default_factory=list)

    differences: list[QuranDifferenceResponse] = Field(default_factory=list)

    has_substantive_difference: bool


class FiqhOpinionResponse(BaseModel):
    """
    Presentation-only grouping of already-governed
    Fiqh position evidence.

    This model does not infer a ruling, majority,
    consensus, or tarjih.
    """

    opinion_id: str
    ordinal: int

    madhhabs: list[str] = Field(default_factory=list)

    evidence_ids: list[str] = Field(default_factory=list)

    position_text: str

    source_id: str
    source_version: str | None = None
    reference: str | None = None
    source_url: str | None = None

    conflict_group: str | None = None
    documented_disagreement: bool = False


class GeneralMaterialItemResponse(BaseModel):
    """
    Source-governed display material.

    This is intentionally NOT EvidenceResponse.
    """

    material_id: str

    source_id: str

    role: str

    text: str

    source_url: str | None = None


class GeneralMaterialResponse(BaseModel):
    """
    General first-layer display contract.

    Evidence proves.
    Materials explain.
    """

    topic: str

    language: str

    lane: str

    official_domain: str | None = None

    unavailable_reason: str | None = None

    materials: list[GeneralMaterialItemResponse] = Field(default_factory=list)


class QueryResponse(BaseModel):
    request_id: str

    question: str

    language: str = "ar"

    understanding: UnderstandingResponse

    action: str
    has_answer: bool

    answer: str | None = None

    limitations: list[str] = Field(default_factory=list)

    citations: list[CitationResponse] = Field(default_factory=list)

    claims: list[StructuredClaimResponse] = Field(default_factory=list)

    integrity_report: IntegrityReportResponse | None = None

    experience: ExperienceResponse | None = None

    evidence_coverage: float
    resolution_coverage: float

    requirements: list[RequirementResponse] = Field(default_factory=list)

    conflicts: list[ConflictResponse] = Field(default_factory=list)

    evidence: list[EvidenceResponse] = Field(default_factory=list)

    fiqh_opinions: list[FiqhOpinionResponse] = Field(default_factory=list)

    general_material: GeneralMaterialResponse | None = None

    unavailable_domains: list[str] = Field(default_factory=list)

    quran_verification: QuranVerificationResponse | None = None

    expert_review: (
        dict[
            str,
            Any,
        ]
        | None
    ) = None
