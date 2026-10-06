from __future__ import annotations

import pytest

from basira.answer.integrity import (
    ClaimIntegrityError,
)
from basira.answer.models import (
    StructuredClaim,
)
from basira.answer.report import (
    AnswerIntegrityReportBuilder,
    LiteralSourceIntegrityState,
)
from basira.evidence.bundle import (
    EvidenceConflict,
    EvidenceConflictType,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)


def _node(
    evidence_id: str = "evidence-1",
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=EvidenceDomain.TAFSIR,
        text=("هذا نص تفسيري أصلي من المصدر."),
        source_id=("surahapp-tafsir-saadi"),
        reference="2:153",
    )


def _claim(
    *,
    text: str = ("هذا نص تفسيري أصلي من المصدر."),
    evidence_id: str = "evidence-1",
) -> StructuredClaim:
    return StructuredClaim(
        axis_id="tafsir",
        claim_id="claim-1",
        text=text,
        evidence_ids=(evidence_id,),
    )


def test_report_marks_literal_claims_passed() -> None:
    node = _node()

    report = AnswerIntegrityReportBuilder().build(
        claims=(_claim(),),
        used_evidence_ids=(node.evidence_id,),
        evidence=(node,),
        limitations=(),
        conflicts=(),
    )

    assert report.literal_source_integrity is LiteralSourceIntegrityState.PASSED

    assert report.claims_checked == 1

    assert report.claim_ids == ("claim-1",)

    assert report.linked_evidence_ids == ("evidence-1",)

    assert not report.has_limitations

    assert not (report.potential_source_conflict)

    assert report.semantic_claim_verification == "not_enabled"


def test_report_without_claims_is_not_applicable() -> None:
    report = AnswerIntegrityReportBuilder().build(
        claims=(),
        used_evidence_ids=(),
        evidence=(),
        limitations=("الأدلة غير كافية.",),
        conflicts=(),
    )

    assert report.literal_source_integrity is LiteralSourceIntegrityState.NOT_APPLICABLE

    assert report.claims_checked == 0

    assert report.has_limitations

    assert report.limitation_count == 1


def test_report_fails_if_claim_not_linked_to_published_evidence() -> None:
    node = _node()

    with pytest.raises(ClaimIntegrityError):
        (
            AnswerIntegrityReportBuilder().build(
                claims=(_claim(),),
                used_evidence_ids=(),
                evidence=(node,),
                limitations=(),
                conflicts=(),
            )
        )


def test_report_preserves_bundle_level_conflict_summary() -> None:
    conflict = EvidenceConflict(
        conflict_type=(EvidenceConflictType.HADITH_GRADE),
        group_id=("hadeethenc:5457"),
        evidence_ids=(
            "grade-a",
            "grade-b",
        ),
    )

    report = AnswerIntegrityReportBuilder().build(
        claims=(),
        used_evidence_ids=(),
        evidence=(),
        limitations=("يوجد تعارض في الأدلة.",),
        conflicts=(conflict,),
    )

    assert report.potential_source_conflict

    assert report.conflict_count == 1

    assert report.conflict_types == ("hadith_grade",)

    assert report.conflict_group_ids == ("hadeethenc:5457",)

    assert report.has_limitations


def test_report_does_not_claim_semantic_verification() -> None:
    report = AnswerIntegrityReportBuilder().build(
        claims=(),
        used_evidence_ids=(),
        evidence=(),
        limitations=(),
        conflicts=(),
    )

    assert report.semantic_claim_verification == "not_enabled"
