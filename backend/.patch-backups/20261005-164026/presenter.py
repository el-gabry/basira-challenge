from __future__ import annotations

from dataclasses import (
    asdict,
    is_dataclass,
)
from enum import Enum
from typing import Any
from uuid import uuid4

from basira.answer.report import (
    AnswerIntegrityReportBuilder,
)
from basira.api.experience import (
    build_competition_experience,
)
from basira.api.schemas import (
    CitationResponse,
    ConflictResponse,
    ContextRequirementResponse,
    EvidenceResponse,
    ExperienceResponse,
    ExperienceTraceStepResponse,
    IntegrityReportResponse,
    QueryEntityResponse,
    QueryResponse,
    RequirementResponse,
    UnderstandingResponse,
)
from basira.api.service import (
    QueryExecution,
)
from basira.models.source_usage import (
    RuntimeUse,
)
from basira.sources.policy_catalog import (
    SourceUsagePolicyNotFoundError,
    get_source_usage_policy,
)


def _jsonable(
    value: Any,
) -> Any:
    if isinstance(value, Enum):
        return value.value

    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}

    if isinstance(
        value,
        (tuple, list, set, frozenset),
    ):
        return [_jsonable(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}

    return value


def _may_display_supporting_text(
    *,
    source_id: str,
) -> bool:
    try:
        policy = get_source_usage_policy(source_id)
    except SourceUsagePolicyNotFoundError:
        return False

    if policy.requires_human_review:
        return False

    return policy.allows(RuntimeUse.SUPPORT_ANSWER) and policy.allows(
        RuntimeUse.CITE_TO_USER
    )


def _display_excerpt(
    text: str,
    *,
    limit: int = 320,
) -> str:
    normalized = " ".join(text.split())

    if len(normalized) <= limit:
        return normalized

    candidate = normalized[: limit + 1]

    minimum = min(
        120,
        limit // 2,
    )

    sentence_end = max(
        (
            candidate.rfind(mark)
            for mark in (
                ".",
                "؟",
                "!",
                "؛",
            )
        ),
        default=-1,
    )

    if sentence_end >= minimum:
        return candidate[: sentence_end + 1].strip()

    shortened = (
        candidate[:limit]
        .rsplit(
            " ",
            1,
        )[0]
        .rstrip("،؛:")
    )

    if not shortened:
        shortened = candidate[:limit].strip()

    return shortened + "…"


def _public_claim_value(
    node: Any,
) -> str | None:
    # Do not weaken the general evidence-text gate.
    # A Hadith grade is a short attributed scholarly
    # claim that the UI needs in order to represent
    # disagreement without selecting one grade.
    if node.domain.value != "hadith" or node.claim_type != "hadith_grade":
        return None

    if not _may_display_supporting_text(
        source_id=node.source_id,
    ):
        return None

    normalized = " ".join(node.text.split())

    return normalized or None


def _supporting_excerpt(
    node: Any,
) -> str | None:
    # Supporting previews are intentionally narrower
    # than the general evidence payload. For now Basira
    # publishes them only for approved Tafsir evidence.
    if node.domain.value != "tafsir":
        return None

    if not _may_display_supporting_text(
        source_id=node.source_id,
    ):
        return None

    if not node.text.strip():
        return None

    return _display_excerpt(node.text)


def present_query(
    execution: QueryExecution,
) -> QueryResponse:
    answer = execution.answer
    bundle = execution.outcome.bundle

    used_ids = frozenset(answer.used_evidence_ids)

    citations = [
        CitationResponse(
            marker=citation.marker,
            evidence_id=(citation.evidence_id),
            domain=(citation.domain.value),
            source_id=(citation.source_id),
            source_version=(citation.source_version),
            reference=(citation.reference),
            source_url=(citation.source_url),
            work_title=(citation.work_title),
            author_name=(citation.author_name),
            institution=(citation.institution),
            publisher=(citation.publisher),
        )
        for citation in answer.citations
    ]

    evidence = [
        EvidenceResponse(
            evidence_id=node.evidence_id,
            domain=node.domain.value,
            source_id=node.source_id,
            source_version=(node.source_version),
            reference=node.reference,
            source_url=node.source_url,
            work_title=node.work_title,
            author_name=node.author_name,
            institution=node.institution,
            publisher=node.publisher,
            claim_type=node.claim_type,
            claim_value=(_public_claim_value(node)),
            used_in_answer=(node.evidence_id in used_ids),
            text=(node.text if node.evidence_id in used_ids else None),
            display_excerpt=(_supporting_excerpt(node)),
        )
        for node in execution.retrieval.evidence
    ]

    claims = [
        {
            "axis_id": claim.axis_id,
            "claim_id": claim.claim_id,
            "text": claim.text,
            "evidence_ids": list(claim.evidence_ids),
        }
        for claim in answer.claims
    ]

    report = AnswerIntegrityReportBuilder().build(
        claims=tuple(answer.claims),
        used_evidence_ids=tuple(answer.used_evidence_ids),
        evidence=tuple(execution.retrieval.evidence),
        limitations=tuple(answer.limitations),
        conflicts=tuple(bundle.conflicts),
        semantic_claim_verification=getattr(
            answer,
            "semantic_claim_verification",
            "not_enabled",
        ),
        semantic_verification_issues=tuple(
            getattr(
                answer,
                "semantic_verification_issues",
                (),
            )
        ),
    )

    integrity_report = IntegrityReportResponse(
        literal_source_integrity=(report.literal_source_integrity.value),
        claims_checked=(report.claims_checked),
        claim_ids=list(report.claim_ids),
        linked_evidence_ids=list(report.linked_evidence_ids),
        has_limitations=(report.has_limitations),
        limitation_count=(report.limitation_count),
        potential_source_conflict=(report.potential_source_conflict),
        conflict_count=(report.conflict_count),
        conflict_types=list(report.conflict_types),
        conflict_group_ids=list(report.conflict_group_ids),
        semantic_claim_verification=(report.semantic_claim_verification),
        semantic_verification_issues=list(report.semantic_verification_issues),
    )

    requirements = [
        RequirementResponse(
            need=assessment.need.value,
            state=assessment.state.value,
            evidence_ids=list(assessment.evidence_ids),
        )
        for assessment in bundle.required_assessments
    ]

    conflicts = [
        ConflictResponse(
            type=(conflict.conflict_type.value),
            group_id=(conflict.group_id),
            evidence_ids=list(conflict.evidence_ids),
        )
        for conflict in bundle.conflicts
    ]

    understanding = execution.understanding

    expert_review = (
        _jsonable(answer.expert_review) if answer.expert_review is not None else None
    )

    experience_view = build_competition_experience(
        action=answer.action.value,
        has_answer=answer.has_answer,
        intent=(understanding.primary_intent.value),
        confidence=(understanding.confidence),
        evidence=tuple(execution.retrieval.evidence),
        used_evidence_ids=tuple(answer.used_evidence_ids),
        requirements=tuple(bundle.required_assessments),
        conflicts=tuple(bundle.conflicts),
        limitations=tuple(answer.limitations),
        unavailable_domains=frozenset(execution.retrieval.unavailable_domains),
        semantic_claim_verification=(report.semantic_claim_verification),
        semantic_verification_issues=(report.semantic_verification_issues),
    )

    experience = ExperienceResponse(
        state=experience_view.state.value,
        severity=(experience_view.severity.value),
        label=experience_view.label,
        headline=experience_view.headline,
        detail=experience_view.detail,
        can_publish=(experience_view.can_publish),
        evidence_count=(experience_view.evidence_count),
        used_evidence_count=(experience_view.used_evidence_count),
        source_count=(experience_view.source_count),
        trace=[
            ExperienceTraceStepResponse(
                key=step.key,
                label=step.label,
                status=step.status.value,
                summary=step.summary,
                evidence_ids=list(step.evidence_ids),
                source_ids=list(step.source_ids),
            )
            for step in experience_view.trace
        ],
    )

    return QueryResponse(
        request_id=str(uuid4()),
        question=execution.question,
        understanding=(
            UnderstandingResponse(
                intent=(understanding.primary_intent.value),
                risk_tags=sorted(risk.value for risk in understanding.risk_tags),
                entities=[
                    QueryEntityResponse(
                        entity_type=(entity.entity_type),
                        value=(entity.value),
                    )
                    for entity in understanding.entities
                ],
                context_requirement=ContextRequirementResponse(
                    required=sorted(
                        need.value
                        for need in understanding.context_requirement.required
                    ),
                    optional=sorted(
                        need.value
                        for need in understanding.context_requirement.optional
                    ),
                ),
                confidence=(understanding.confidence),
            )
        ),
        action=answer.action.value,
        has_answer=(answer.has_answer),
        answer=answer.answer,
        limitations=list(answer.limitations),
        citations=citations,
        claims=claims,
        integrity_report=integrity_report,
        experience=experience,
        evidence_coverage=(answer.evidence_coverage),
        resolution_coverage=(answer.resolution_coverage),
        requirements=requirements,
        conflicts=conflicts,
        evidence=evidence,
        unavailable_domains=sorted(
            domain.value for domain in execution.retrieval.unavailable_domains
        ),
        expert_review=expert_review,
    )
