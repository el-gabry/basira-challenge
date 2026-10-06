from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.orchestration.evidence_acceptance import (
    AnchorKind,
    AnchorOrigin,
    EvidenceAcceptanceReason,
    EvidenceAnchor,
    RetrievalShape,
    TaskEvidenceAcceptanceContract,
    TaskEvidenceAcceptanceGate,
)


def contract() -> TaskEvidenceAcceptanceContract:
    return TaskEvidenceAcceptanceContract(
        task_id="claim:chair",
        retrieval_shape=(RetrievalShape.HYBRID),
        allowed_domains=frozenset(
            {
                EvidenceDomain.QURAN,
                EvidenceDomain.TAFSIR,
            }
        ),
        required_domains=frozenset(
            {
                EvidenceDomain.QURAN,
                EvidenceDomain.TAFSIR,
            }
        ),
        anchors=(
            EvidenceAnchor(
                reference="2:255",
                domains=frozenset(
                    {
                        EvidenceDomain.QURAN,
                        EvidenceDomain.TAFSIR,
                    }
                ),
                kind=(AnchorKind.QURAN_AYAH),
                origin=(AnchorOrigin.CANONICAL_TEXT_MATCH),
            ),
        ),
    )


def quran_node() -> EvidenceNode:
    return EvidenceNode(
        evidence_id="quran:2:255",
        domain=EvidenceDomain.QURAN,
        text="canonical Quran",
        source_id="quran:canonical",
        reference="2:255",
    )


def test_dorar_passage_43_can_cover_quran_2_255():
    tafsir = EvidenceNode(
        evidence_id="dorar:2:43#tt7",
        domain=EvidenceDomain.TAFSIR,
        text="كرسيه",
        source_id="dorar:tafsir",
        reference=("https://dorar.net/tafseer/2/43#tt7"),
        source_url=("https://dorar.net/tafseer/2/43#tt7"),
        related_quran=(
            "2:254",
            "2:255",
            "2:256",
            "2:257",
        ),
    )

    result = TaskEvidenceAcceptanceGate().evaluate(
        contract=contract(),
        evidence=(
            quran_node(),
            tafsir,
        ),
    )

    assert tuple(node.evidence_id for node in result.accepted_evidence) == (
        "quran:2:255",
        "dorar:2:43#tt7",
    )

    assert result.structural_contract_satisfied


def test_unrelated_tafsir_coverage_is_rejected():
    tafsir = EvidenceNode(
        evidence_id="dorar:57:1#tt7",
        domain=EvidenceDomain.TAFSIR,
        text="unrelated",
        source_id="dorar:tafsir",
        reference=("https://dorar.net/tafseer/57/1#tt7"),
        related_quran=(
            "57:1",
            "57:2",
        ),
    )

    result = TaskEvidenceAcceptanceGate().evaluate(
        contract=contract(),
        evidence=(
            quran_node(),
            tafsir,
        ),
    )

    record = next(
        item for item in result.records if (item.evidence_id == "dorar:57:1#tt7")
    )

    assert record.reason is EvidenceAcceptanceReason.HARD_ANCHOR_MISMATCH


def test_source_url_alone_is_not_quran_identity():
    tafsir = EvidenceNode(
        evidence_id="dorar:no-coverage",
        domain=EvidenceDomain.TAFSIR,
        text="source locator only",
        source_id="dorar:tafsir",
        reference=("https://dorar.net/tafseer/2/43#tt7"),
    )

    result = TaskEvidenceAcceptanceGate().evaluate(
        contract=contract(),
        evidence=(
            quran_node(),
            tafsir,
        ),
    )

    record = next(
        item for item in result.records if (item.evidence_id == "dorar:no-coverage")
    )

    assert record.reason is EvidenceAcceptanceReason.MISSING_REQUIRED_REFERENCE


def test_legacy_quran_range_still_works():
    tafsir = EvidenceNode(
        evidence_id="legacy:tafsir",
        domain=EvidenceDomain.TAFSIR,
        text="legacy local passage",
        source_id="legacy:tafsir",
        reference="2:254-257",
    )

    result = TaskEvidenceAcceptanceGate().evaluate(
        contract=contract(),
        evidence=(
            quran_node(),
            tafsir,
        ),
    )

    assert result.structural_contract_satisfied
