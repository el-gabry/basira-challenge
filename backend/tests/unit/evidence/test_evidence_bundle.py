from basira.evidence.bundle import (
    EvidenceBundleBuilder,
    EvidenceRequirementState,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstandingService,
)
from basira.retrieval.retrieval_plan import (
    BasiraRetrievalPlanner,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)


def node(
    *,
    evidence_id: str,
    domain: EvidenceDomain,
    reference: str,
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=domain,
        text=f"text:{evidence_id}",
        source_id=(
            f"source:{evidence_id}"
        ),
        reference=reference,
    )


def build_plan(
    query: str,
):
    understanding = (
        BasiraQueryUnderstandingService()
        .understand(query)
    )

    return (
        BasiraRetrievalPlanner()
        .build(
            understanding
        )
    )


def test_bundle_is_complete_when_all_required_evidence_exists() -> None:
    plan = build_plan(
        "ما سبب نزول الآية 58:1؟"
    )

    result = UnifiedRetrievalResult(
        plan=plan,
        evidence=(
            node(
                evidence_id="quran:58:1",
                domain=(
                    EvidenceDomain.QURAN
                ),
                reference="58:1",
            ),
            node(
                evidence_id="katheer:58:1",
                domain=(
                    EvidenceDomain.TAFSIR
                ),
                reference="58:1",
            ),
            node(
                evidence_id="saadi:58:1",
                domain=(
                    EvidenceDomain.TAFSIR
                ),
                reference="58:1",
            ),
            node(
                evidence_id="nozool:58:1",
                domain=(
                    EvidenceDomain
                    .REVELATION_CONTEXT
                ),
                reference="58:1",
            ),
        ),
        unavailable_domains=frozenset(),
    )

    bundle = (
        EvidenceBundleBuilder()
        .build(result)
    )

    assert bundle.evidence_complete
    assert bundle.resolution_complete

    assert bundle.evidence_coverage == 1.0
    assert bundle.resolution_coverage == 1.0

    assessment = (
        bundle.assessment_for(
            EvidenceNeed
            .REVELATION_CONTEXT
        )
    )

    assert assessment is not None

    assert (
        assessment.state
        == EvidenceRequirementState
        .SATISFIED
    )


def test_no_attested_entry_is_resolved_but_not_evidence_complete() -> None:
    plan = build_plan(
        "ما سبب نزول الآية 2:255؟"
    )

    result = UnifiedRetrievalResult(
        plan=plan,
        evidence=(
            node(
                evidence_id="quran:2:255",
                domain=(
                    EvidenceDomain.QURAN
                ),
                reference="2:255",
            ),
            node(
                evidence_id="katheer:2:255",
                domain=(
                    EvidenceDomain.TAFSIR
                ),
                reference="2:255",
            ),
            node(
                evidence_id="saadi:2:255",
                domain=(
                    EvidenceDomain.TAFSIR
                ),
                reference="2:255",
            ),
        ),
        unavailable_domains=frozenset(),
    )

    bundle = (
        EvidenceBundleBuilder()
        .build(result)
    )

    assessment = (
        bundle.assessment_for(
            EvidenceNeed
            .REVELATION_CONTEXT
        )
    )

    assert assessment is not None

    assert (
        assessment.state
        == EvidenceRequirementState
        .NO_ATTESTED_ENTRY
    )

    assert not bundle.evidence_complete
    assert bundle.resolution_complete

    assert bundle.evidence_coverage < 1.0
    assert bundle.resolution_coverage == 1.0


def test_hadith_text_and_grade_are_assessed_independently() -> None:
    plan = build_plan(
        "ما صحة حديث رقم 5457؟"
    )

    result = UnifiedRetrievalResult(
        plan=plan,
        evidence=(
            EvidenceNode(
                evidence_id=(
                    "hadeethenc:5457:text"
                ),
                domain=(
                    EvidenceDomain.HADITH
                ),
                text="نص الحديث",
                source_id=(
                    "hadeethenc-official"
                ),
                reference="5457",
                claim_type="hadith_text",
            ),
            EvidenceNode(
                evidence_id=(
                    "hadeethenc:5457:grade"
                ),
                domain=(
                    EvidenceDomain.HADITH
                ),
                text="صحيح",
                source_id=(
                    "hadeethenc-official"
                ),
                reference="5457",
                topic="sahih",
                claim_type="hadith_grade",
            ),
        ),
        unavailable_domains=frozenset(),
    )

    bundle = (
        EvidenceBundleBuilder()
        .build(result)
    )

    text = bundle.assessment_for(
        EvidenceNeed.HADITH_TEXT
    )

    grade = bundle.assessment_for(
        EvidenceNeed.HADITH_GRADE
    )

    assert text is not None
    assert grade is not None

    assert (
        text.state
        == EvidenceRequirementState
        .SATISFIED
    )

    assert (
        grade.state
        == EvidenceRequirementState
        .SATISFIED
    )

    assert text.evidence_ids == (
        "hadeethenc:5457:text",
    )

    assert grade.evidence_ids == (
        "hadeethenc:5457:grade",
    )


def test_hadith_text_does_not_satisfy_grade_requirement() -> None:
    plan = build_plan(
        "ما صحة حديث رقم 5457؟"
    )

    result = UnifiedRetrievalResult(
        plan=plan,
        evidence=(
            EvidenceNode(
                evidence_id=(
                    "hadeethenc:5457:text"
                ),
                domain=(
                    EvidenceDomain.HADITH
                ),
                text="نص الحديث",
                source_id=(
                    "hadeethenc-official"
                ),
                reference="5457",
                claim_type="hadith_text",
            ),
        ),
        unavailable_domains=frozenset(),
    )

    bundle = (
        EvidenceBundleBuilder()
        .build(result)
    )

    text = bundle.assessment_for(
        EvidenceNeed.HADITH_TEXT
    )

    grade = bundle.assessment_for(
        EvidenceNeed.HADITH_GRADE
    )

    assert text is not None
    assert grade is not None

    assert (
        text.state
        == EvidenceRequirementState
        .SATISFIED
    )

    assert (
        grade.state
        == EvidenceRequirementState
        .MISSING_EVIDENCE
    )


def test_hadith_unavailable_marks_both_requirements_unavailable() -> None:
    plan = build_plan(
        "ما صحة حديث رقم 5457؟"
    )

    result = UnifiedRetrievalResult(
        plan=plan,
        evidence=(),
        unavailable_domains=frozenset(
            {
                EvidenceDomain.HADITH,
            }
        ),
    )

    bundle = (
        EvidenceBundleBuilder()
        .build(result)
    )

    for need in (
        EvidenceNeed.HADITH_TEXT,
        EvidenceNeed.HADITH_GRADE,
    ):
        assessment = (
            bundle.assessment_for(
                need
            )
        )

        assert assessment is not None

        assert (
            assessment.state
            == EvidenceRequirementState
            .UNAVAILABLE_DOMAIN
        )


def test_hadith_grade_conflict_is_preserved() -> None:
    plan = build_plan(
        "ما صحة حديث رقم 5457؟"
    )

    result = UnifiedRetrievalResult(
        plan=plan,
        evidence=(
            EvidenceNode(
                evidence_id=(
                    "source-a:5457:text"
                ),
                domain=(
                    EvidenceDomain.HADITH
                ),
                text="نص الحديث",
                source_id="source-a",
                reference="5457",
                claim_type="hadith_text",
                conflict_group=(
                    "hadeethenc:5457"
                ),
            ),
            EvidenceNode(
                evidence_id=(
                    "source-a:5457:grade"
                ),
                domain=(
                    EvidenceDomain.HADITH
                ),
                text="صحيح",
                source_id="source-a",
                reference="5457",
                topic="sahih",
                claim_type="hadith_grade",
                conflict_group=(
                    "hadeethenc:5457"
                ),
            ),
            EvidenceNode(
                evidence_id=(
                    "source-b:5457:grade"
                ),
                domain=(
                    EvidenceDomain.HADITH
                ),
                text="ضعيف",
                source_id="source-b",
                reference="5457",
                topic="daif",
                claim_type="hadith_grade",
                conflict_group=(
                    "hadeethenc:5457"
                ),
            ),
        ),
        unavailable_domains=frozenset(),
    )

    bundle = (
        EvidenceBundleBuilder()
        .build(result)
    )

    assert len(bundle.conflicts) == 1

    conflict = bundle.conflicts[0]

    assert (
        conflict.conflict_type.value
        == "hadith_grade"
    )

    assert (
        conflict.group_id
        == "hadeethenc:5457"
    )

    assert conflict.evidence_ids == (
        "source-a:5457:grade",
        "source-b:5457:grade",
    )

    grade = bundle.assessment_for(
        EvidenceNeed.HADITH_GRADE
    )

    assert grade is not None

    assert (
        grade.state
        == EvidenceRequirementState
        .SATISFIED
    )


def test_explicit_hadith_grade_conflict_survives_same_category() -> None:
    plan = build_plan(
        "ما صحة حديث رقم 65065؟"
    )

    group = (
        "hadeethenc:65065:"
        "grade:cross-version"
    )

    result = UnifiedRetrievalResult(
        plan=plan,
        evidence=(
            EvidenceNode(
                evidence_id=(
                    "official-ar:65065:grade"
                ),
                domain=(
                    EvidenceDomain.HADITH
                ),
                text="صحيح لغيره",
                source_id=(
                    "hadeethenc-official"
                ),
                reference="65065",
                topic="sahih",
                claim_type="hadith_grade",
                conflict_group=group,
                conflict_type=(
                    "cross_version_grade_conflict"
                ),
            ),
            EvidenceNode(
                evidence_id=(
                    "official-en:65065:grade"
                ),
                domain=(
                    EvidenceDomain.HADITH
                ),
                text="صحيح",
                source_id=(
                    "hadeethenc-official"
                ),
                reference="65065",
                topic="sahih",
                claim_type="hadith_grade",
                conflict_group=group,
                conflict_type=(
                    "cross_version_grade_conflict"
                ),
            ),
        ),
        unavailable_domains=frozenset(),
    )

    bundle = (
        EvidenceBundleBuilder()
        .build(result)
    )

    assert len(bundle.conflicts) == 1

    conflict = bundle.conflicts[0]

    assert conflict.group_id == group

    assert len(
        conflict.evidence_ids
    ) == 2
