from __future__ import annotations

from dataclasses import (
    asdict,
    is_dataclass,
)
from datetime import UTC, datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path
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
    FiqhOpinionResponse,
    GeneralMaterialItemResponse,
    GeneralMaterialResponse,
    IntegrityReportResponse,
    LocalizedEvidenceResponse,
    QueryEntityResponse,
    QueryResponse,
    QuranDifferenceResponse,
    QuranVerificationCandidateResponse,
    QuranVerificationResponse,
    RequirementResponse,
    UnderstandingResponse,
)
from basira.api.service import (
    QueryExecution,
)
from basira.competition.quranpedia_translation_adapter import (
    QuranpediaTranslationAdmissionError,
    QuranpediaTranslationEvidenceAdapter,
)
from basira.models.source_usage import (
    RuntimeUse,
)
from basira.sources.policy_catalog import (
    SourceUsagePolicyNotFoundError,
    get_source_usage_policy,
)


def _source_verification_payload(
    item: object,
) -> dict[str, object] | None:
    """
    Public attestation timestamp.

    The item has already crossed Basira's governed source
    boundary before it reaches the presenter. This timestamp
    records that successful runtime attestation. It is NOT a
    browser clock and does not fabricate scholar attribution.
    """

    raw_domain = getattr(
        item,
        "domain",
        None,
    )

    domain = getattr(
        raw_domain,
        "value",
        raw_domain,
    )

    if domain not in {
        "quran",
        "hadith",
        "tafsir",
    }:
        return None

    if domain == "quran":
        methods = [
            "canonical_identity",
            "passport_manifest",
            "governed_admission",
        ]

    elif domain == "hadith":
        methods = [
            "source_identity",
            "response_sha256",
            "governed_admission",
        ]

    else:
        methods = [
            "source_identity",
            "response_sha256",
            "governed_admission",
        ]

    verified_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )

    return {
        "status": "verified",
        "verified_at": verified_at,
        "reverify_after_seconds": 86400,
        "methods": methods,
    }


@lru_cache(maxsize=1)
def _quran_english_translation_adapter() -> QuranpediaTranslationEvidenceAdapter:
    repo_root = Path(__file__).resolve().parents[3]

    return QuranpediaTranslationEvidenceAdapter(repo_root=repo_root)


def _localized_quran_representation(
    node: Any,
    *,
    language: str,
    may_expose_text: bool,
) -> LocalizedEvidenceResponse | None:
    """
    Source-native presentation companion only.

    Canonical Arabic evidence remains the reasoning,
    sufficiency, citation, and publication authority.
    """

    if language != "en" or not may_expose_text:
        return None

    if (
        node.domain.value != "quran"
        or node.claim_type != "quran_text"
        or not node.reference
    ):
        return None

    parts = node.reference.split(
        ":",
        1,
    )

    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None

    try:
        companion = _quran_english_translation_adapter().get(
            surah=int(parts[0]),
            ayah=int(parts[1]),
        )
    except QuranpediaTranslationAdmissionError:
        # Fail closed. Never generate or infer a
        # translation when governed admission fails.
        return None

    if companion is None:
        return None

    if (
        companion.claim_type != "quran_translation"
        or companion.reference != node.reference
        or companion.related_quran != (node.reference,)
    ):
        return None

    verification = _source_verification_payload(companion)

    if verification is None:
        return None

    verification = {
        **verification,
        "methods": [
            "reference_identity",
            "passport_manifest",
            "snapshot_sha256",
            "governed_admission",
        ],
    }

    return LocalizedEvidenceResponse(
        language="en",
        evidence_id=companion.evidence_id,
        claim_type="quran_translation",
        text=companion.text,
        source_id=companion.source_id,
        source_version=(companion.source_version),
        reference=companion.reference,
        source_url=companion.source_url,
        work_title=companion.work_title,
        authority_scope=(companion.authority_scope),
        source_verification=verification,
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


def _fiqh_opinion_payloads(
    *,
    evidence: tuple[Any, ...],
    used_ids: frozenset[str],
) -> list[FiqhOpinionResponse]:
    """
    Group duplicate per-madhhab Fiqh nodes into
    presentation cards without performing semantic
    inference.

    Grouping is exact and source-bound:
        source identity
        + exact position text
        + conflict identity

    Only evidence already selected for the published
    answer may appear here.
    """

    groups: dict[
        tuple[
            str,
            str | None,
            str | None,
            str | None,
            str,
            str | None,
        ],
        dict[str, Any],
    ] = {}

    order: list[
        tuple[
            str,
            str | None,
            str | None,
            str | None,
            str,
            str | None,
        ]
    ] = []

    for node in evidence:
        if (
            node.domain.value != "fiqh"
            or node.claim_type != "fiqh_position"
            or node.evidence_id not in used_ids
        ):
            continue

        if not node.text.strip():
            continue

        key = (
            node.source_id,
            node.source_version,
            node.reference,
            node.source_url,
            node.text,
            node.conflict_group,
        )

        if key not in groups:
            groups[key] = {
                "node": node,
                "evidence_ids": [],
                "madhhabs": [],
            }
            order.append(key)

        group = groups[key]

        if node.evidence_id not in group["evidence_ids"]:
            group["evidence_ids"].append(node.evidence_id)

        scope = (node.authority_scope or "").strip()

        if scope and scope not in group["madhhabs"]:
            group["madhhabs"].append(scope)

    opinions: list[FiqhOpinionResponse] = []

    for ordinal, key in enumerate(
        order,
        start=1,
    ):
        group = groups[key]
        node = group["node"]

        opinions.append(
            FiqhOpinionResponse(
                opinion_id=(f"{node.source_id}:opinion:{ordinal}"),
                ordinal=ordinal,
                madhhabs=list(group["madhhabs"]),
                evidence_ids=list(group["evidence_ids"]),
                position_text=node.text,
                source_id=node.source_id,
                source_version=(node.source_version),
                reference=node.reference,
                source_url=node.source_url,
                conflict_group=(node.conflict_group),
                documented_disagreement=(node.conflict_group is not None),
            )
        )

    return opinions



def _localized_hadith_answer(
    answer_text: str | None,
    *,
    language: str,
    evidence,
    used_ids: frozenset[str],
) -> str | None:
    """
    Presentation-only localization for a published
    Hadith answer.

    This function runs AFTER governed composition.

    It may translate deterministic UI framing only.

    It MUST NOT:
    - alter claim text;
    - alter evidence text;
    - alter Hadith identity;
    - alter grade/authenticity;
    - create authority;
    - change publication decisions.
    """

    if (
        language != "en"
        or answer_text is None
        or not answer_text.strip()
    ):
        return answer_text

    used_nodes = tuple(
        node
        for node in evidence
        if node.evidence_id in used_ids
    )

    if not used_nodes:
        return answer_text

    # Scope this localization strictly to answers whose
    # published evidence is Hadith-only.
    if any(
        getattr(
            getattr(
                node,
                "domain",
                None,
            ),
            "value",
            None,
        )
        != "hadith"
        for node in used_nodes
    ):
        return answer_text

    rendered: list[str] = []

    for line in answer_text.splitlines():
        stripped = line.strip()

        if (
            stripped
            == "وفق الأدلة المعتمدة:"
        ):
            rendered.append(
                "According to the governed evidence:"
            )
            continue

        if (
            stripped
            == (
                "وفق نص الحديث وأحكام المحدّثين "
                "الموجودة في المصادر المعتمدة:"
            )
        ):
            rendered.append(
                "According to the governed Hadith "
                "evidence and source verification:"
            )
            continue

        # Composer label shape:
        #
        # [2] حكم المحدّث (reference): <verified claim>
        #
        # Only the label is localized.
        # Everything after ":" remains byte-for-byte
        # the verified claim text produced upstream.
        if (
            line.startswith("[")
            and "] حكم " in line
        ):
            prefix, remainder = (
                line.split(
                    "] حكم ",
                    1,
                )
            )

            label, separator, claim = (
                remainder.partition(":")
            )

            if separator:
                detail = label.strip()

                if detail.startswith(
                    "المحدّث"
                ):
                    suffix = detail[
                        len("المحدّث"):
                    ].strip()

                    english_label = (
                        "Hadith status / "
                        "source verification"
                    )

                    if suffix:
                        english_label += (
                            " " + suffix
                        )

                else:
                    english_label = (
                        "Hadith status / "
                        "source verification"
                        " — "
                        + detail
                    )

                rendered.append(
                    f"{prefix}] "
                    f"{english_label}:"
                    f"{claim}"
                )

                continue

        rendered.append(line)

    return "\n".join(rendered)


def present_query(
    execution: QueryExecution,
    *,
    language: str = "ar",
) -> QueryResponse:
    if language not in {"ar", "en"}:
        raise ValueError("Unsupported presentation language.")

    answer = execution.answer
    bundle = execution.outcome.bundle

    used_ids = frozenset(answer.used_evidence_ids)

    conflict_ids = frozenset(
        evidence_id
        for conflict in bundle.conflicts
        for evidence_id in conflict.evidence_ids
    )

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
            source_verification=(_source_verification_payload(citation)),
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
            source_verification=(_source_verification_payload(node)),
            localized=(
                _localized_quran_representation(
                    node,
                    language=language,
                    may_expose_text=(node.evidence_id in used_ids),
                )
            ),
            claim_type=node.claim_type,
            authority_scope=node.authority_scope,
            conflict_group=node.conflict_group,
            conflict_type=node.conflict_type,
            related_hadith=list(
                getattr(
                    node,
                    "related_hadith",
                    (),
                )
                or ()
            ),
            claim_value=(
                " ".join(node.text.split())
                if (
                    node.claim_type == "hadith_grade"
                    and node.evidence_id in (used_ids | conflict_ids)
                )
                else _public_claim_value(node)
            ),
            used_in_answer=(node.evidence_id in used_ids),
            text=(node.text if node.evidence_id in used_ids else None),
            display_excerpt=(_supporting_excerpt(node)),
        )
        for node in execution.retrieval.evidence
    ]

    fiqh_opinions = _fiqh_opinion_payloads(
        evidence=tuple(execution.retrieval.evidence),
        used_ids=used_ids,
    )

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

    quote_result = getattr(
        execution,
        "quran_verification",
        None,
    )

    quran_verification = None

    if quote_result is not None:
        quran_verification = QuranVerificationResponse(
            status=quote_result.status.value,
            input_text=quote_result.input_text,
            candidates=[
                QuranVerificationCandidateResponse(
                    reference=candidate.reference,
                    canonical_text=(candidate.canonical_text),
                    source_id=(candidate.source_id),
                    score=candidate.score,
                )
                for candidate in quote_result.candidates
            ],
            differences=[
                QuranDifferenceResponse(
                    kind=(difference.kind.value),
                    expected=list(difference.expected),
                    received=list(difference.received),
                    is_substantive=(difference.is_substantive),
                )
                for difference in quote_result.differences
            ],
            has_substantive_difference=(quote_result.has_substantive_difference),
        )

    general_material = None

    material_result = execution.general_material

    # Core religious questions have no General lane,
    # so no extra response object is emitted.
    if material_result is not None and material_result.lane is not None:
        general_material = GeneralMaterialResponse(
            topic=(material_result.resolution.topic.value),
            language=(material_result.resolution.language),
            lane=(material_result.lane.value),
            official_domain=(
                material_result.official_domain.value
                if (material_result.official_domain is not None)
                else None
            ),
            unavailable_reason=(material_result.unavailable_reason),
            materials=[
                GeneralMaterialItemResponse(
                    material_id=(material.material_id),
                    source_id=(material.source_id),
                    role=(material.role.value),
                    text=(material.text),
                    source_url=(material.source_url),
                )
                for material in material_result.materials
            ],
        )

    return QueryResponse(
        language=language,
        request_id=str(uuid4()),
        quran_verification=(quran_verification),
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
        answer=_localized_hadith_answer(
            answer.answer,
            language=language,
            evidence=(
                execution.retrieval.evidence
            ),
            used_ids=used_ids,
        ),
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
        fiqh_opinions=fiqh_opinions,
        general_material=general_material,
        unavailable_domains=sorted(
            domain.value for domain in execution.retrieval.unavailable_domains
        ),
        expert_review=expert_review,
    )
