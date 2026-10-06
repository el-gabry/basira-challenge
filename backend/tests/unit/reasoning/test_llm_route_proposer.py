from __future__ import annotations

from collections.abc import Mapping

from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
)
from basira.reasoning.llm_route_proposer import (
    LLMRouteProposer,
)
from basira.reasoning.route_governor import (
    RouteGovernor,
)
from basira.reasoning.route_proposal import (
    RouteProposal,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstandingService,
    RiskTag,
)


class FakeStructuredLLMClient:
    def __init__(
        self,
        payload: Mapping[
            str,
            object,
        ]
        | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.payload = payload if payload is not None else {}

        self.error = error

        self.calls: list[
            dict[
                str,
                object,
            ]
        ] = []

    def complete_structured(
        self,
        *,
        instruction: str,
        input_data: Mapping[
            str,
            object,
        ],
        schema: Mapping[
            str,
            object,
        ],
    ) -> Mapping[
        str,
        object,
    ]:
        self.calls.append(
            {
                "instruction": instruction,
                "input_data": dict(input_data),
                "schema": dict(schema),
            }
        )

        if self.error is not None:
            raise self.error

        return self.payload


def _understanding(
    question: str = ("اشرح لي المقصود"),
):
    return BasiraQueryUnderstandingService().understand(question)


def test_valid_structured_proposal_is_parsed():
    client = FakeStructuredLLMClient(
        {
            "proposed_intent": ("quran_meaning"),
            "proposed_primary_discipline": ("quran"),
            "proposed_secondary_disciplines": [
                "tafsir",
            ],
            "proposed_reasoning_mode": ("interpretation"),
            "additional_risk_tags": [
                "context_sensitive",
            ],
            "ambiguity": False,
            "confidence": 0.97,
            "reason_codes": [
                "semantic:quran_meaning",
            ],
        }
    )

    proposal = LLMRouteProposer(client=client).propose(understanding=_understanding())

    assert proposal.proposed_intent is BasiraIntent.QURAN_MEANING

    assert proposal.proposed_primary_discipline is ReligiousDiscipline.QURAN

    assert proposal.proposed_secondary_disciplines == (ReligiousDiscipline.TAFSIR,)

    assert proposal.proposed_reasoning_mode is ReasoningMode.INTERPRETATION

    assert proposal.additional_risk_tags == frozenset(
        {
            RiskTag.CONTEXT_SENSITIVE,
        }
    )

    assert proposal.confidence == 0.97


def test_original_user_question_is_sent_to_client():
    question = "ما معنى الكرسي في قوله تعالى وسع كرسيه السماوات والأرض؟"

    client = FakeStructuredLLMClient()

    LLMRouteProposer(client=client).propose(understanding=(_understanding(question)))

    assert len(client.calls) == 1

    input_data = client.calls[0]["input_data"]

    assert input_data["question"] == question


def test_schema_contains_only_non_authoritative_fields():
    client = FakeStructuredLLMClient()

    LLMRouteProposer(client=client).propose(understanding=_understanding())

    schema = client.calls[0]["schema"]

    properties = schema["properties"]

    assert isinstance(
        properties,
        dict,
    )

    assert set(properties) == {
        "proposed_intent",
        "proposed_primary_discipline",
        "proposed_secondary_disciplines",
        "proposed_reasoning_mode",
        "additional_risk_tags",
        "ambiguity",
        "confidence",
        "reason_codes",
    }

    for forbidden in (
        "canonical_reference",
        "canonical_identity",
        "required_evidence",
        "allowed_domains",
        "allowed_sources",
        "publication_decision",
        "publish",
    ):
        assert forbidden not in properties


def test_authority_injection_rejects_entire_payload():
    client = FakeStructuredLLMClient(
        {
            "proposed_intent": ("quran_meaning"),
            "confidence": 1.0,
            "canonical_reference": ("2:43"),
            "publish": True,
        }
    )

    proposal = LLMRouteProposer(client=client).propose(understanding=_understanding())

    assert proposal == RouteProposal()


def test_invalid_enum_rejects_entire_payload():
    client = FakeStructuredLLMClient(
        {
            "proposed_intent": ("invented_religious_route"),
            "confidence": 1.0,
        }
    )

    proposal = LLMRouteProposer(client=client).propose(understanding=_understanding())

    assert proposal == RouteProposal()


def test_malformed_list_rejects_entire_payload():
    client = FakeStructuredLLMClient(
        {
            "additional_risk_tags": ("context_sensitive"),
            "confidence": 1.0,
        }
    )

    proposal = LLMRouteProposer(client=client).propose(understanding=_understanding())

    assert proposal == RouteProposal()


def test_provider_exception_degrades_to_noop():
    client = FakeStructuredLLMClient(error=RuntimeError("provider unavailable"))

    proposal = LLMRouteProposer(client=client).propose(understanding=_understanding())

    assert proposal == RouteProposal()


def test_governor_remains_authoritative_over_llm_proposal():
    baseline = BasiraQueryUnderstandingService().understand("ما معنى آية الكرسي؟")

    client = FakeStructuredLLMClient(
        {
            "proposed_intent": ("hadith_authenticity"),
            "proposed_primary_discipline": ("hadith"),
            "proposed_reasoning_mode": ("authenticity"),
            "confidence": 1.0,
        }
    )

    proposal = LLMRouteProposer(client=client).propose(understanding=baseline)

    result = RouteGovernor().govern(
        understanding=baseline,
        proposal=proposal,
    )

    assert result.effective_understanding.primary_intent is baseline.primary_intent

    assert not (result.accepted_intent_specialization)
