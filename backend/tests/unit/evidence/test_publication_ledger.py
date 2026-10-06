from __future__ import annotations

from dataclasses import replace

import pytest

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNode,
)
from basira.evidence.publication import (
    GovernedPublicationLedger,
)


def node(
    *,
    claim_type: str | None = ("tafsir_linguistic_explanation"),
) -> EvidenceNode:
    return EvidenceNode(
        evidence_id="dorar:test:1",
        domain=EvidenceDomain.TAFSIR,
        text=("قال المفسر إن معنى الكرسي في هذا الموضع كذا."),
        source_id="dorar-tafsir-v1",
        reference=("https://dorar.net/tafseer/2/43#tt7"),
        related_quran=(
            "2:254",
            "2:255",
            "2:256",
            "2:257",
        ),
        claim_type=claim_type,
    )


def test_source_id_alone_cannot_publish():
    ledger = GovernedPublicationLedger()

    assert not ledger.may_publish(node())


def test_exact_admitted_node_can_publish():
    ledger = GovernedPublicationLedger()

    original = node()

    ledger.admit(original)

    assert ledger.may_publish(original)


def test_literal_source_excerpt_can_publish():
    ledger = GovernedPublicationLedger()

    original = node()

    ledger.admit(original)

    excerpt = replace(
        original,
        text=("معنى الكرسي في هذا الموضع كذا."),
    )

    assert ledger.may_publish(excerpt)


def test_forged_text_with_same_source_id_is_blocked():
    ledger = GovernedPublicationLedger()

    original = node()

    ledger.admit(original)

    forged = replace(
        original,
        text=("نص مزور لا يوجد في المصدر."),
    )

    assert not ledger.may_publish(forged)


def test_changed_reference_is_blocked():
    ledger = GovernedPublicationLedger()

    original = node()

    ledger.admit(original)

    forged = replace(
        original,
        reference=("https://dorar.net/tafseer/2/99#tt7"),
    )

    assert not ledger.may_publish(forged)


def test_collision_fails_closed():
    ledger = GovernedPublicationLedger()

    original = node()

    ledger.admit(original)

    with pytest.raises(
        ValueError,
        match=("publication evidence_id collision"),
    ):
        ledger.admit(
            replace(
                original,
                text="different",
            )
        )
