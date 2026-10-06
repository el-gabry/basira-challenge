from types import SimpleNamespace

from basira.evidence.bundle import (
    EvidenceBundleBuilder,
    EvidenceConflictType,
    EvidenceRequirementState,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)


def _result(
    *nodes: EvidenceNode,
):
    return SimpleNamespace(
        evidence=tuple(nodes),
        unavailable_domains=(
            frozenset()
        ),
    )


def _node(
    *,
    evidence_id: str,
    claim_type: str,
    text: str,
    authority_scope: str | None = None,
    topic: str | None = "باب المسألة",
):
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=EvidenceDomain.FIQH,
        text=text,
        source_id="governed-fiqh",
        work_id="book-1",
        work_title="كتاب فقهي",
        claim_type=claim_type,
        authority_scope=(
            authority_scope
        ),
        topic=topic,
    )


def test_fiqh_evidence_is_not_satisfied_by_condition_only():
    result = _result(
        _node(
            evidence_id="c1",
            claim_type="fiqh_condition",
            text="يشترط القبض",
        )
    )

    assessment = (
        EvidenceBundleBuilder()
        ._assess_need(
            result=result,
            need=(
                EvidenceNeed
                .FIQH_EVIDENCE
            ),
        )
    )

    assert (
        assessment.state
        is EvidenceRequirementState
        .MISSING_EVIDENCE
    )


def test_fiqh_position_satisfies_fiqh_evidence():
    result = _result(
        _node(
            evidence_id="p1",
            claim_type="fiqh_position",
            text="نص المذهب في المسألة",
            authority_scope="shafii",
        )
    )

    assessment = (
        EvidenceBundleBuilder()
        ._assess_need(
            result=result,
            need=(
                EvidenceNeed
                .FIQH_EVIDENCE
            ),
        )
    )

    assert (
        assessment.state
        is EvidenceRequirementState
        .SATISFIED
    )

    assert (
        assessment.evidence_ids
        == ("p1",)
    )


def test_madhhab_scope_requires_explicit_authority_scope():
    unscoped = _result(
        _node(
            evidence_id="p1",
            claim_type="fiqh_position",
            text="نص فقهي",
        )
    )

    missing = (
        EvidenceBundleBuilder()
        ._assess_need(
            result=unscoped,
            need=(
                EvidenceNeed
                .FIQH_MADHHAB_SCOPE
            ),
        )
    )

    assert (
        missing.state
        is EvidenceRequirementState
        .MISSING_EVIDENCE
    )

    scoped = _result(
        _node(
            evidence_id="p2",
            claim_type="fiqh_position",
            text="نص فقهي",
            authority_scope="maliki",
        )
    )

    satisfied = (
        EvidenceBundleBuilder()
        ._assess_need(
            result=scoped,
            need=(
                EvidenceNeed
                .FIQH_MADHHAB_SCOPE
            ),
        )
    )

    assert (
        satisfied.state
        is EvidenceRequirementState
        .SATISFIED
    )


def test_condition_cannot_substitute_for_exception():
    result = _result(
        _node(
            evidence_id="c1",
            claim_type="fiqh_condition",
            text="يشترط القبض",
        )
    )

    conditions = (
        EvidenceBundleBuilder()
        ._assess_need(
            result=result,
            need=(
                EvidenceNeed
                .FIQH_CONDITIONS
            ),
        )
    )

    exceptions = (
        EvidenceBundleBuilder()
        ._assess_need(
            result=result,
            need=(
                EvidenceNeed
                .FIQH_EXCEPTIONS
            ),
        )
    )

    assert (
        conditions.state
        is EvidenceRequirementState
        .SATISFIED
    )

    assert (
        exceptions.state
        is EvidenceRequirementState
        .MISSING_EVIDENCE
    )


def test_exception_cannot_substitute_for_condition():
    result = _result(
        _node(
            evidence_id="e1",
            claim_type="fiqh_exception",
            text="إلا حال الضرورة",
        )
    )

    conditions = (
        EvidenceBundleBuilder()
        ._assess_need(
            result=result,
            need=(
                EvidenceNeed
                .FIQH_CONDITIONS
            ),
        )
    )

    exceptions = (
        EvidenceBundleBuilder()
        ._assess_need(
            result=result,
            need=(
                EvidenceNeed
                .FIQH_EXCEPTIONS
            ),
        )
    )

    assert (
        conditions.state
        is EvidenceRequirementState
        .MISSING_EVIDENCE
    )

    assert (
        exceptions.state
        is EvidenceRequirementState
        .SATISFIED
    )


def test_same_ruling_across_madhhabs_is_not_a_conflict():
    result = _result(
        _node(
            evidence_id="h",
            claim_type="fiqh_ruling",
            text="يشترط القبض",
            authority_scope="hanafi",
        ),
        _node(
            evidence_id="s",
            claim_type="fiqh_ruling",
            text="يشترط القبض",
            authority_scope="shafii",
        ),
    )

    conflicts = (
        EvidenceBundleBuilder()
        ._detect_fiqh_conflicts(
            result
        )
    )

    assert conflicts == ()


def test_distinct_explicit_rulings_across_madhhabs_are_preserved():
    result = _result(
        _node(
            evidence_id="h",
            claim_type="fiqh_ruling",
            text="ينتقض الوضوء باللمس",
            authority_scope="shafii",
        ),
        _node(
            evidence_id="m",
            claim_type="fiqh_ruling",
            text="لا ينتقض الوضوء باللمس",
            authority_scope="hanafi",
        ),
    )

    conflicts = (
        EvidenceBundleBuilder()
        ._detect_fiqh_conflicts(
            result
        )
    )

    assert len(conflicts) == 1

    conflict = conflicts[0]

    assert (
        conflict.conflict_type
        is EvidenceConflictType
        .FIQH_POSITION
    )

    assert set(
        conflict.evidence_ids
    ) == {
        "h",
        "m",
    }


def test_distinct_wording_without_explicit_rulings_is_not_auto_conflict():
    result = _result(
        _node(
            evidence_id="h",
            claim_type="fiqh_position",
            text="عبارة من كتاب حنفي",
            authority_scope="hanafi",
        ),
        _node(
            evidence_id="s",
            claim_type="fiqh_position",
            text="عبارة أخرى من كتاب شافعي",
            authority_scope="shafii",
        ),
    )

    conflicts = (
        EvidenceBundleBuilder()
        ._detect_fiqh_conflicts(
            result
        )
    )

    assert conflicts == ()


def test_source_explicit_disagreement_satisfies_disagreement_need():
    result = _result(
        _node(
            evidence_id="d1",
            claim_type="fiqh_disagreement",
            text=(
                "واختلف أهل العلم "
                "في المسألة"
            ),
            authority_scope="shafii",
        )
    )

    assessment = (
        EvidenceBundleBuilder()
        ._assess_need(
            result=result,
            need=(
                EvidenceNeed
                .FIQH_DISAGREEMENT
            ),
        )
    )

    assert (
        assessment.state
        is EvidenceRequirementState
        .SATISFIED
    )

    assert (
        assessment.evidence_ids
        == ("d1",)
    )


def test_multi_madhhab_distinct_rulings_satisfy_disagreement_without_voting():
    result = _result(
        _node(
            evidence_id="a",
            claim_type="fiqh_ruling",
            text="يجوز",
            authority_scope="maliki",
        ),
        _node(
            evidence_id="b",
            claim_type="fiqh_ruling",
            text="لا يجوز",
            authority_scope="hanbali",
        ),
    )

    assessment = (
        EvidenceBundleBuilder()
        ._assess_need(
            result=result,
            need=(
                EvidenceNeed
                .FIQH_DISAGREEMENT
            ),
        )
    )

    assert (
        assessment.state
        is EvidenceRequirementState
        .SATISFIED
    )

    assert set(
        assessment.evidence_ids
    ) == {
        "a",
        "b",
    }
