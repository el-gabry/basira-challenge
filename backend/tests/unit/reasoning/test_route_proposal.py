from __future__ import annotations

from dataclasses import fields

import pytest

from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
)
from basira.reasoning.route_proposal import (
    RouteProposal,
    RouteProposer,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
    BasiraQueryUnderstandingService,
    RiskTag,
)


class FakeRouteProposer:
    def propose(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
    ) -> RouteProposal:
        del understanding

        return RouteProposal(
            proposed_intent=(BasiraIntent.QURAN_MEANING),
            proposed_primary_discipline=(ReligiousDiscipline.QURAN),
            proposed_secondary_disciplines=(ReligiousDiscipline.TAFSIR,),
            proposed_reasoning_mode=(ReasoningMode.INTERPRETATION),
            additional_risk_tags=frozenset(),
            ambiguity=False,
            confidence=0.92,
            reason_codes=("semantic:quran_meaning",),
        )


def accepts_proposer(
    proposer: RouteProposer,
) -> RouteProposer:
    return proposer


def test_route_proposer_returns_non_authoritative_proposal():
    proposer = accepts_proposer(FakeRouteProposer())

    understanding = BasiraQueryUnderstandingService().understand("ما معنى آية الكرسي؟")

    proposal = proposer.propose(
        understanding=understanding,
    )

    assert proposal.proposed_intent is BasiraIntent.QURAN_MEANING

    assert proposal.proposed_primary_discipline is ReligiousDiscipline.QURAN

    assert proposal.proposed_reasoning_mode is ReasoningMode.INTERPRETATION

    assert proposal.confidence == 0.92


def test_route_proposal_has_no_authority_fields():
    names = {field.name for field in fields(RouteProposal)}

    forbidden = {
        "canonical_reference",
        "canonical_anchor",
        "required_evidence",
        "required_needs",
        "allowed_domains",
        "allowed_sources",
        "source_ids",
        "can_publish",
        "publication_authorized",
    }

    assert not (names & forbidden)


def test_route_proposal_can_only_express_additional_risks():
    proposal = RouteProposal(
        additional_risk_tags=frozenset(
            {
                RiskTag.CONTEXT_SENSITIVE,
            }
        )
    )

    assert RiskTag.CONTEXT_SENSITIVE in proposal.additional_risk_tags

    assert not hasattr(
        proposal,
        "removed_risk_tags",
    )

    assert not hasattr(
        proposal,
        "suppressed_risk_tags",
    )


def test_route_proposal_rejects_invalid_confidence():
    with pytest.raises(
        ValueError,
    ):
        RouteProposal(
            confidence=1.1,
        )


def test_route_proposal_rejects_primary_as_secondary():
    with pytest.raises(
        ValueError,
    ):
        RouteProposal(
            proposed_primary_discipline=(ReligiousDiscipline.QURAN),
            proposed_secondary_disciplines=(ReligiousDiscipline.QURAN,),
        )


def test_route_proposal_rejects_duplicate_secondary_disciplines():
    with pytest.raises(
        ValueError,
    ):
        RouteProposal(
            proposed_secondary_disciplines=(
                ReligiousDiscipline.TAFSIR,
                ReligiousDiscipline.TAFSIR,
            ),
        )


def test_route_proposal_rejects_blank_reason_code():
    with pytest.raises(
        ValueError,
    ):
        RouteProposal(
            reason_codes=(
                "semantic:quran",
                " ",
            ),
        )
