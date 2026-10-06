from basira.evidence.fiqh_structural_adapter import (
    FiqhStructuralEvidenceAdapter,
)
from basira.evidence.fiqh_units import (
    FiqhStructuralUnitBuilder,
)
from basira.evidence.models import (
    EvidenceDomain,
)
from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)


def _passage(
    *,
    metadata=None,
):
    text = (
        "الحكم: ينتقض الوضوء باللمس. "
        "والشرط: أن يكون بلا حائل. "
        "والشرط الثاني: أن يكون اللمس مباشرا. "
        "والدليل: قوله تعالى كذا. "
        "ووجه الدلالة: دل النص على الحكم. "
        "ويستثنى حال الضرورة. "
        "واختلف أهل العلم في المسألة."
    )

    values = {
        "projection_kind":
            "fiqh_targeted_exact_slice",
        "parent_passage_id":
            "book:1:page:10",
        "projection_char_start":
            "100",
        "projection_char_end":
            str(100 + len(text)),
        "madhhab":
            "shafii",
    }

    if metadata:
        values.update(
            metadata
        )

    return ScholarlyPassage(
        passage_id=(
            "book:1:page:10:"
            "fiqh-projection:100:300"
        ),
        source_id="shamela-governed",
        domain=ScholarlyDomain.FIQH,
        work_id="book-1",
        work_title="كتاب فقهي",
        text=text,
        author_name="مصنف الكتاب",
        publisher="ناشر محقق",
        source_version="snapshot-v1",
        section_title=(
            "باب نواقض الوضوء"
        ),
        volume="1",
        page="10",
        source_url=(
            "https://example.invalid/book/1/10"
        ),
        metadata=values,
    )


def test_minimal_unit_becomes_position_node_only():
    passage = _passage()

    unit = (
        FiqhStructuralUnitBuilder()
        .from_projected_passage(
            passage
        )
    )

    nodes = (
        FiqhStructuralEvidenceAdapter()
        .from_unit(
            unit
        )
    )

    assert len(nodes) == 1

    position = nodes[0]

    assert (
        position.domain
        is EvidenceDomain.FIQH
    )

    assert (
        position.claim_type
        == "fiqh_position"
    )

    assert (
        position.text
        == passage.text
    )

    assert (
        position.authority_scope
        == "shafii"
    )

    assert (
        position.work_id
        == "book-1"
    )

    assert (
        position.page
        == "10"
    )

    assert (
        position.source_version
        == "snapshot-v1"
    )


def test_explicit_structure_becomes_typed_linked_nodes():
    passage = _passage(
        metadata={
            "fiqh_ruling":
                (
                    "ينتقض الوضوء "
                    "باللمس"
                ),
            "fiqh_conditions":
                (
                    "أن يكون بلا حائل"
                    "||"
                    "أن يكون اللمس مباشرا"
                ),
            "fiqh_dalil":
                "قوله تعالى كذا",
            "fiqh_wajh_al_dalala":
                (
                    "دل النص على الحكم"
                ),
            "fiqh_exceptions":
                "حال الضرورة",
            "fiqh_disagreement":
                (
                    "واختلف أهل العلم "
                    "في المسألة"
                ),
        }
    )

    unit = (
        FiqhStructuralUnitBuilder()
        .from_projected_passage(
            passage
        )
    )

    nodes = (
        FiqhStructuralEvidenceAdapter()
        .from_unit(
            unit
        )
    )

    claim_types = tuple(
        node.claim_type
        for node in nodes
    )

    assert claim_types == (
        "fiqh_position",
        "fiqh_ruling",
        "fiqh_dalil",
        "fiqh_wajh_al_dalala",
        "fiqh_condition",
        "fiqh_condition",
        "fiqh_exception",
        "fiqh_disagreement",
    )

    position = nodes[0]

    for child in nodes[1:]:
        assert (
            child.related_fiqh
            == (
                position.evidence_id,
            )
        )

        assert (
            child.text
            in position.text
        )

        assert (
            child.authority_scope
            == "shafii"
        )


def test_no_ruling_node_when_source_structure_has_no_ruling():
    passage = _passage(
        metadata={
            "fiqh_dalil":
                "قوله تعالى كذا",
        }
    )

    unit = (
        FiqhStructuralUnitBuilder()
        .from_projected_passage(
            passage
        )
    )

    nodes = (
        FiqhStructuralEvidenceAdapter()
        .from_unit(
            unit
        )
    )

    assert not any(
        node.claim_type
        == "fiqh_ruling"
        for node in nodes
    )

    assert any(
        node.claim_type
        == "fiqh_dalil"
        for node in nodes
    )


def test_adapter_never_rewrites_source_text():
    passage = _passage(
        metadata={
            "fiqh_ruling":
                (
                    "ينتقض الوضوء "
                    "باللمس"
                ),
        }
    )

    unit = (
        FiqhStructuralUnitBuilder()
        .from_projected_passage(
            passage
        )
    )

    nodes = (
        FiqhStructuralEvidenceAdapter()
        .from_unit(
            unit
        )
    )

    for node in nodes:
        assert (
            node.text
            in passage.text
        )
