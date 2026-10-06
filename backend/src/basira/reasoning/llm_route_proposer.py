from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from basira.reasoning.contracts import (
    ReasoningMode,
    ReligiousDiscipline,
)
from basira.reasoning.route_proposal import (
    RouteProposal,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
    RiskTag,
)


class StructuredLLMClient(Protocol):
    """
    Provider-neutral structured-generation boundary.

    Implementations may call a hosted or local model,
    but callers receive only a structured mapping.

    This interface grants no Basira evidence, source,
    identity, routing, safety, or publication authority.
    """

    def complete_structured(
        self,
        *,
        instruction: str,
        input_data: Mapping[str, object],
        schema: Mapping[str, object],
    ) -> Mapping[str, object]: ...


_ROUTE_FIELDS = frozenset(
    {
        "proposed_intent",
        "proposed_primary_discipline",
        "proposed_secondary_disciplines",
        "proposed_reasoning_mode",
        "additional_risk_tags",
        "ambiguity",
        "confidence",
        "reason_codes",
    }
)


_ROUTE_INSTRUCTION = """
Interpret the user's question for semantic routing only.

Return only fields permitted by the supplied schema.

You may suggest:
- intent
- religious discipline
- reasoning mode
- additional safety/risk hints
- ambiguity
- confidence
- reason codes

You must not decide or return:
- canonical Quran or Hadith identity
- verse or Hadith reference authority
- required evidence
- allowed evidence domains
- allowed sources
- retrieval authorization
- answerability
- publication authorization

Your output is non-authoritative.
Basira's deterministic governor makes the final routing decision.
""".strip()


def _route_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "proposed_intent": {
                "type": ["string", "null"],
                "enum": [
                    *[item.value for item in BasiraIntent],
                    None,
                ],
            },
            "proposed_primary_discipline": {
                "type": ["string", "null"],
                "enum": [
                    *[item.value for item in ReligiousDiscipline],
                    None,
                ],
            },
            "proposed_secondary_disciplines": {
                "type": "array",
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "enum": [item.value for item in ReligiousDiscipline],
                },
            },
            "proposed_reasoning_mode": {
                "type": ["string", "null"],
                "enum": [
                    *[item.value for item in ReasoningMode],
                    None,
                ],
            },
            "additional_risk_tags": {
                "type": "array",
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "enum": [item.value for item in RiskTag],
                },
            },
            "ambiguity": {
                "type": "boolean",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "reason_codes": {
                "type": "array",
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "minLength": 1,
                },
            },
        },
    }


def _optional_enum(
    enum_type,
    value: object,
):
    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise ValueError("enum proposal value must be a string or null")

    return enum_type(value)


def _string_list(
    value: object,
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not isinstance(
        value,
        list,
    ):
        raise ValueError(f"{field_name} must be a JSON array")

    result: list[str] = []

    for item in value:
        if not isinstance(
            item,
            str,
        ):
            raise ValueError(f"{field_name} entries must be strings")

        cleaned = item.strip()

        if not cleaned:
            raise ValueError(f"{field_name} entries must not be blank")

        result.append(cleaned)

    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} entries must be unique")

    return tuple(result)


def parse_route_proposal(
    payload: Mapping[str, object],
) -> RouteProposal:
    """
    Strict parser for untrusted model output.

    Unknown fields reject the whole proposal.
    They are never silently ignored.
    """

    unknown = set(payload) - _ROUTE_FIELDS

    if unknown:
        raise ValueError(
            f"route proposal contains forbidden or unknown fields: {sorted(unknown)!r}"
        )

    secondary_values = _string_list(
        payload.get(
            "proposed_secondary_disciplines",
            [],
        ),
        field_name=("proposed_secondary_disciplines"),
    )

    risk_values = _string_list(
        payload.get(
            "additional_risk_tags",
            [],
        ),
        field_name="additional_risk_tags",
    )

    reason_codes = _string_list(
        payload.get(
            "reason_codes",
            [],
        ),
        field_name="reason_codes",
    )

    ambiguity = payload.get(
        "ambiguity",
        False,
    )

    if not isinstance(
        ambiguity,
        bool,
    ):
        raise ValueError("ambiguity must be boolean")

    confidence_value = payload.get(
        "confidence",
        0.0,
    )

    if isinstance(
        confidence_value,
        bool,
    ) or not isinstance(
        confidence_value,
        (
            int,
            float,
        ),
    ):
        raise ValueError("confidence must be numeric")

    confidence = float(confidence_value)

    return RouteProposal(
        proposed_intent=_optional_enum(
            BasiraIntent,
            payload.get("proposed_intent"),
        ),
        proposed_primary_discipline=(
            _optional_enum(
                ReligiousDiscipline,
                payload.get("proposed_primary_discipline"),
            )
        ),
        proposed_secondary_disciplines=tuple(
            ReligiousDiscipline(value) for value in secondary_values
        ),
        proposed_reasoning_mode=(
            _optional_enum(
                ReasoningMode,
                payload.get("proposed_reasoning_mode"),
            )
        ),
        additional_risk_tags=frozenset(RiskTag(value) for value in risk_values),
        ambiguity=ambiguity,
        confidence=confidence,
        reason_codes=reason_codes,
    )


class LLMRouteProposer:
    """
    Non-authoritative semantic route proposer.

    Any provider failure, malformed output, invalid enum,
    schema violation, or attempted authority injection
    degrades to an exact no-op RouteProposal.

    The deterministic RouteGovernor remains authoritative.
    """

    def __init__(
        self,
        *,
        client: StructuredLLMClient,
    ) -> None:
        self.client = client

    def propose(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
    ) -> RouteProposal:
        input_data: dict[
            str,
            object,
        ] = {
            "question": (understanding.query.original_text),
            "baseline_intent": (understanding.primary_intent.value),
            "baseline_risk_tags": [
                item.value
                for item in sorted(
                    understanding.risk_tags,
                    key=lambda item: item.value,
                )
            ],
        }

        try:
            payload = self.client.complete_structured(
                instruction=(_ROUTE_INSTRUCTION),
                input_data=input_data,
                schema=_route_schema(),
            )

            if not isinstance(
                payload,
                Mapping,
            ):
                return RouteProposal()

            return parse_route_proposal(payload)

        except Exception:  # noqa: BLE001
            # Provider/model output is untrusted.
            # Routing must safely degrade to the existing
            # deterministic Basira path.
            return RouteProposal()
