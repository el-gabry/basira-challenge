from basira.api.presenter import (
    _fiqh_opinion_payloads,
)
from basira.api.schemas import QueryResponse
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)


def _position(
    *,
    evidence_id: str,
    text: str,
    madhhab: str,
    source_id: str = "dorar:fiqh:424",
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id=evidence_id,
        domain=EvidenceDomain.FIQH,
        text=text,
        source_id=source_id,
        source_version="sha256-test",
        reference="مس المرأة فرجها",
        source_url=(
            "https://dorar.net/feqhia/424"
        ),
        claim_type="fiqh_position",
        authority_scope=madhhab,
        conflict_group="fiqh:dorar:fiqh:424",
        conflict_type="fiqh_position",
    )


def test_fiqh_opinions_group_exact_position_by_madhhab() -> None:
    first_text = (
        "القول الأول: لا ينقض الوضوء."
    )

    second_text = (
        "القول الثاني: ينقض الوضوء."
    )

    nodes = (
        _position(
            evidence_id="p1-hanafi",
            text=first_text,
            madhhab="hanafi",
        ),
        _position(
            evidence_id="p1-maliki",
            text=first_text,
            madhhab="maliki",
        ),
        _position(
            evidence_id="p2-shafii",
            text=second_text,
            madhhab="shafii",
        ),
        _position(
            evidence_id="p2-hanbali",
            text=second_text,
            madhhab="hanbali",
        ),
    )

    used_ids = frozenset(
        node.evidence_id
        for node in nodes
    )

    opinions = _fiqh_opinion_payloads(
        evidence=nodes,
        used_ids=used_ids,
    )

    assert len(opinions) == 2

    assert opinions[0].ordinal == 1
    assert opinions[0].position_text == first_text
    assert opinions[0].madhhabs == [
        "hanafi",
        "maliki",
    ]
    assert opinions[0].evidence_ids == [
        "p1-hanafi",
        "p1-maliki",
    ]

    assert opinions[1].ordinal == 2
    assert opinions[1].position_text == second_text
    assert opinions[1].madhhabs == [
        "shafii",
        "hanbali",
    ]

    assert all(
        item.documented_disagreement
        for item in opinions
    )


def test_fiqh_opinions_never_group_across_sources() -> None:
    text = "قول فقهي واحد"

    nodes = (
        _position(
            evidence_id="source-a",
            text=text,
            madhhab="hanafi",
            source_id="dorar:fiqh:100",
        ),
        _position(
            evidence_id="source-b",
            text=text,
            madhhab="maliki",
            source_id="dorar:fiqh:200",
        ),
    )

    opinions = _fiqh_opinion_payloads(
        evidence=nodes,
        used_ids=frozenset(
            node.evidence_id
            for node in nodes
        ),
    )

    assert len(opinions) == 2


def test_fiqh_opinions_expose_only_used_evidence() -> None:
    nodes = (
        _position(
            evidence_id="published",
            text="قول منشور",
            madhhab="hanafi",
        ),
        _position(
            evidence_id="not-published",
            text="قول غير منشور",
            madhhab="maliki",
        ),
    )

    opinions = _fiqh_opinion_payloads(
        evidence=nodes,
        used_ids=frozenset(
            {"published"}
        ),
    )

    assert len(opinions) == 1
    assert opinions[0].evidence_ids == [
        "published"
    ]


def test_query_response_schema_exposes_fiqh_opinions() -> None:
    schema = (
        QueryResponse.model_json_schema()
    )

    properties = schema[
        "properties"
    ]

    assert "fiqh_opinions" in properties

    evidence_schema = schema[
        "$defs"
    ][
        "EvidenceResponse"
    ][
        "properties"
    ]

    assert "authority_scope" in evidence_schema
    assert "conflict_group" in evidence_schema
    assert "conflict_type" in evidence_schema
