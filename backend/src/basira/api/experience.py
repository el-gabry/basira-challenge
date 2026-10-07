from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ExperienceState(StrEnum):
    VERIFIED = "verified"
    GROUNDED = "grounded"
    LIMITED = "limited"
    CONFLICT = "conflict"
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    REGENERATE = "regenerate"
    BLOCKED = "blocked"
    EXPERT_REVIEW = "expert_review"
    ABSTAINED = "abstained"


class ExperienceSeverity(StrEnum):
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


class TraceStepStatus(StrEnum):
    COMPLETE = "complete"
    WARNING = "warning"
    BLOCKED = "blocked"


@dataclass(
    frozen=True,
    slots=True,
)
class ExperienceTraceStep:
    key: str
    label: str
    status: TraceStepStatus
    summary: str
    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class CompetitionExperience:
    state: ExperienceState
    severity: ExperienceSeverity
    label: str
    headline: str
    detail: str
    can_publish: bool
    evidence_count: int
    used_evidence_count: int
    source_count: int
    trace: tuple[
        ExperienceTraceStep,
        ...,
    ]


_LABELS: dict[
    ExperienceState,
    tuple[str, str, str],
] = {
    ExperienceState.VERIFIED: (
        "إجابة موثقة",
        "الإجابة اجتازت بوابة التحقق",
        ("الادعاءات المنشورة مرتبطة بالأدلة المستشهد بها واجتازت التحقق الدلالي."),
    ),
    ExperienceState.GROUNDED: (
        "إجابة مرتبطة بالمصادر",
        "الإجابة مبنية على أدلة قابلة للتتبع",
        (
            "تم التحقق من الارتباط بالمصادر، "
            "لكن التحقق الدلالي الآلي غير مفعّل "
            "لهذا المسار."
        ),
    ),
    ExperienceState.LIMITED: (
        "إجابة مع قيود",
        "يمكن عرض الإجابة مع توضيح القيود",
        ("الأدلة تسمح بالإجابة، مع وجود قيود يجب أن تبقى ظاهرة للمستخدم."),
    ),
    ExperienceState.CONFLICT: (
        "يوجد خلاف في الأدلة",
        "تم الحفاظ على الخلاف بدل إخفائه",
        ("المصادر تحتوي على تعارض أو اختلاف معتبر؛ لا تختار بصيرة رأيًا تلقائيًا."),
    ),
    ExperienceState.NEEDS_CLARIFICATION: (
        "نحتاج تحديد الآية",
        "يلزم تحديد الآية المقصودة",
        (
            "تعذر تثبيت هوية آية واحدة بشكل قاطع. "
            "هذه ليست حالة نقص في الأدلة؛ "
            "يلزم تحديد الموضع المقصود قبل متابعة التفسير."
        ),
    ),
    ExperienceState.NEEDS_MORE_EVIDENCE: (
        "الأدلة غير كافية",
        "يلزم استرجاع أدلة إضافية",
        ("لم تتحقق متطلبات الأدلة اللازمة لإجابة قابلة للنشر."),
    ),
    ExperienceState.REGENERATE: (
        "تحتاج الصياغة إلى إعادة توليد",
        "الأدلة موجودة لكن الصياغة لم تجتز التحقق",
        ("تم منع نشر الصياغة الحالية لأنها غير مدعومة دلاليًا بما يكفي."),
    ),
    ExperienceState.BLOCKED: (
        "تم حجب الإجابة",
        "فشل تحقق حاسم قبل النشر",
        ("لا يسمح مسار التحقق بنشر الإجابة الحالية."),
    ),
    ExperienceState.EXPERT_REVIEW: (
        "تحتاج مراجعة خبير",
        "تم تحويل الحالة إلى مراجعة بشرية مؤهلة",
        ("لا تصدر بصيرة حكمًا مستقلًا في هذه الحالة عالية الحساسية."),
    ),
    ExperienceState.ABSTAINED: (
        "لم تُنشر إجابة",
        "اختارت بصيرة الامتناع عن الإجابة",
        ("حالة الأدلة الحالية لا تسمح بإجابة موثوقة."),
    ),
}


def _value(
    value: Any,
) -> str:
    raw = getattr(
        value,
        "value",
        value,
    )

    return str(raw)


def _experience_state(
    *,
    action: str,
    has_answer: bool,
    conflicts: tuple[Any, ...],
    limitations: tuple[str, ...],
    semantic_status: str,
) -> ExperienceState:
    if semantic_status == "block":
        return ExperienceState.BLOCKED

    if semantic_status == "regenerate":
        return ExperienceState.REGENERATE

    if action == "escalate_to_expert":
        return ExperienceState.EXPERT_REVIEW

    if action == "clarify":
        return ExperienceState.NEEDS_CLARIFICATION

    if action == "retrieve_more":
        return ExperienceState.NEEDS_MORE_EVIDENCE

    if action == "abstain":
        return ExperienceState.ABSTAINED

    if conflicts:
        return ExperienceState.CONFLICT

    if action == "answer_with_limitation" or limitations:
        return ExperienceState.LIMITED

    if semantic_status == "pass" and has_answer:
        return ExperienceState.VERIFIED

    if has_answer:
        return ExperienceState.GROUNDED

    return ExperienceState.ABSTAINED


def _severity(
    state: ExperienceState,
) -> ExperienceSeverity:
    if state is ExperienceState.VERIFIED:
        return ExperienceSeverity.SUCCESS

    if state is ExperienceState.GROUNDED:
        return ExperienceSeverity.INFO

    if state in {
        ExperienceState.LIMITED,
        ExperienceState.CONFLICT,
        ExperienceState.NEEDS_CLARIFICATION,
        ExperienceState.NEEDS_MORE_EVIDENCE,
        ExperienceState.REGENERATE,
        ExperienceState.EXPERT_REVIEW,
    }:
        return ExperienceSeverity.WARNING

    return ExperienceSeverity.DANGER


def _publication_status(
    state: ExperienceState,
    *,
    can_publish: bool,
) -> TraceStepStatus:
    if can_publish:
        return TraceStepStatus.COMPLETE

    if state in {
        ExperienceState.NEEDS_CLARIFICATION,
        ExperienceState.NEEDS_MORE_EVIDENCE,
        ExperienceState.REGENERATE,
        ExperienceState.EXPERT_REVIEW,
    }:
        return TraceStepStatus.WARNING

    return TraceStepStatus.BLOCKED


def build_competition_experience(
    *,
    action: str,
    has_answer: bool,
    intent: str,
    confidence: float,
    evidence: tuple[Any, ...],
    used_evidence_ids: tuple[str, ...],
    requirements: tuple[Any, ...],
    conflicts: tuple[Any, ...],
    limitations: tuple[str, ...],
    unavailable_domains: frozenset[Any],
    semantic_claim_verification: str,
    semantic_verification_issues: tuple[
        str,
        ...,
    ] = (),
) -> CompetitionExperience:
    """
    Translate already-resolved backend state for UI rendering.

    This layer never upgrades evidence authority, invents
    semantic support, or changes the publication decision.
    """

    state = _experience_state(
        action=action,
        has_answer=has_answer,
        conflicts=conflicts,
        limitations=limitations,
        semantic_status=(semantic_claim_verification),
    )

    label, headline, detail = _LABELS[state]

    can_publish = bool(
        has_answer
        and state
        not in {
            ExperienceState.NEEDS_CLARIFICATION,
            ExperienceState.NEEDS_MORE_EVIDENCE,
            ExperienceState.REGENERATE,
            ExperienceState.BLOCKED,
            ExperienceState.EXPERT_REVIEW,
            ExperienceState.ABSTAINED,
        }
    )

    evidence_ids = tuple(str(node.evidence_id) for node in evidence)

    source_ids = tuple(dict.fromkeys(str(node.source_id) for node in evidence))

    unavailable = tuple(sorted(_value(domain) for domain in unavailable_domains))

    evidence_status = TraceStepStatus.COMPLETE if evidence else TraceStepStatus.WARNING

    if evidence:
        evidence_summary = (
            f"تم استرجاع {len(evidence)} دليلًا من {len(source_ids)} مصدر."
        )
    elif unavailable:
        evidence_summary = (
            "تعذر الوصول إلى بعض مجالات الأدلة: " + "، ".join(unavailable) + "."
        )
    else:
        evidence_summary = "لم تُسترجع أدلة قابلة للاستخدام."

    resolved_states = {
        "satisfied",
        "no_attested_entry",
    }

    requirement_states = tuple(_value(item.state) for item in requirements)

    resolved_count = sum(
        state_value in resolved_states for state_value in requirement_states
    )

    requirements_ok = not requirement_states or resolved_count == len(
        requirement_states
    )

    requirement_status = (
        TraceStepStatus.COMPLETE if requirements_ok else TraceStepStatus.WARNING
    )

    if requirement_states:
        requirement_summary = (
            f"تم حسم {resolved_count} من {len(requirement_states)} من متطلبات الأدلة."
        )
    else:
        requirement_summary = "لا توجد متطلبات أدلة إضافية معلنة لهذا المسار."

    conflict_status = TraceStepStatus.WARNING if conflicts else TraceStepStatus.COMPLETE

    conflict_summary = (
        f"تم الحفاظ على {len(conflicts)} حالة خلاف أو تعارض."
        if conflicts
        else "لم يُكتشف تعارض بين الأدلة المنشورة."
    )

    publication_status = _publication_status(
        state,
        can_publish=can_publish,
    )

    if can_publish:
        publication_summary = "سمحت بوابة النشر بعرض الإجابة."
    elif state is ExperienceState.REGENERATE:
        publication_summary = "تم إيقاف النشر وطلب إعادة توليد الصياغة."
    elif state is ExperienceState.EXPERT_REVIEW:
        publication_summary = "تم إيقاف النشر التلقائي وإحالة الحالة لخبير."
    else:
        publication_summary = "لم تسمح بوابة النشر بعرض إجابة موضوعية."

    semantic_summary = f"التحقق الدلالي: {semantic_claim_verification}."

    if semantic_verification_issues:
        semantic_summary += " أسباب: " + "، ".join(semantic_verification_issues) + "."

    trace = (
        ExperienceTraceStep(
            key="understanding",
            label="فهم السؤال",
            status=TraceStepStatus.COMPLETE,
            summary=(f"تم تحديد نوع السؤال: {intent} (ثقة {confidence:.0%})."),
        ),
        ExperienceTraceStep(
            key="evidence",
            label="استرجاع الأدلة",
            status=evidence_status,
            summary=evidence_summary,
            evidence_ids=evidence_ids,
            source_ids=source_ids,
        ),
        ExperienceTraceStep(
            key="requirements",
            label="كفاية متطلبات الأدلة",
            status=requirement_status,
            summary=requirement_summary,
            evidence_ids=tuple(
                dict.fromkeys(
                    evidence_id
                    for item in requirements
                    for evidence_id in getattr(
                        item,
                        "evidence_ids",
                        (),
                    )
                )
            ),
        ),
        ExperienceTraceStep(
            key="conflicts",
            label="فحص الخلاف والتعارض",
            status=conflict_status,
            summary=conflict_summary,
            evidence_ids=tuple(
                dict.fromkeys(
                    evidence_id
                    for conflict in conflicts
                    for evidence_id in getattr(
                        conflict,
                        "evidence_ids",
                        (),
                    )
                )
            ),
        ),
        ExperienceTraceStep(
            key="publication",
            label="قرار النشر",
            status=publication_status,
            summary=(publication_summary + " " + semantic_summary),
            evidence_ids=used_evidence_ids,
        ),
    )

    return CompetitionExperience(
        state=state,
        severity=_severity(state),
        label=label,
        headline=headline,
        detail=detail,
        can_publish=can_publish,
        evidence_count=len(evidence),
        used_evidence_count=len(used_evidence_ids),
        source_count=len(source_ids),
        trace=trace,
    )
