from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field


class HistoricalEntityType(StrEnum):
    PLACE = "place"

    REGION = "region"

    POLITY = "polity"

    TRIBE = "tribe"

    PERSON = "person"

    INSTITUTION = "institution"

    OTHER = "other"


class HistoricalAliasRelation(StrEnum):
    CANONICAL_LABEL = (
        "canonical_label"
    )

    HISTORICAL_NAME = (
        "historical_name"
    )

    MODERN_NAME = "modern_name"

    ALTERNATE_NAME = (
        "alternate_name"
    )

    TRANSLITERATION = (
        "transliteration"
    )

    ADMINISTRATIVE_SUCCESSOR = (
        "administrative_successor"
    )

    GEOGRAPHIC_OVERLAP = (
        "geographic_overlap"
    )


class HistoricalEntityAmbiguity(StrEnum):
    UNAMBIGUOUS = "unambiguous"

    TIME_DEPENDENT = (
        "time_dependent"
    )

    GEOGRAPHICALLY_AMBIGUOUS = (
        "geographically_ambiguous"
    )

    MULTIPLE_CANDIDATES = (
        "multiple_candidates"
    )

    UNKNOWN = "unknown"


class HistoricalEntityResolutionDecision(StrEnum):
    NO_MATCH = "no_match"

    EXPAND_RETRIEVAL = (
        "expand_retrieval"
    )

    EXPAND_WITH_AMBIGUITY = (
        "expand_with_ambiguity"
    )


class HistoricalEntityAlias(BaseModel):
    text: str

    relation: HistoricalAliasRelation

    valid_from_ah: int | None = None

    valid_to_ah: int | None = None

    geographic_scope: str | None = None

    evidence_ids: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


class HistoricalEntityRecord(BaseModel):
    canonical_entity_id: str

    entity_type: HistoricalEntityType

    canonical_label: str

    aliases: tuple[
        HistoricalEntityAlias,
        ...
    ] = Field(
        default_factory=tuple
    )

    ambiguity_status: HistoricalEntityAmbiguity = (
        HistoricalEntityAmbiguity.UNKNOWN
    )

    geographic_scope: str | None = None

    evidence_ids: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


class HistoricalEntityMatch(BaseModel):
    canonical_entity_id: str

    entity_type: HistoricalEntityType

    canonical_label: str

    matched_text: str

    matched_relation: HistoricalAliasRelation

    retrieval_expansions: tuple[
        str,
        ...
    ]

    decision: HistoricalEntityResolutionDecision

    ambiguity_status: HistoricalEntityAmbiguity

    # Entity Resolver is retrieval infrastructure.
    #
    # It is not allowed to assert historical identity
    # inside the final answer.
    may_assert_identity: bool = False

    may_rewrite_answer_entity_as_equivalent: bool = False

    evidence_ids: tuple[
        str,
        ...
    ] = Field(
        default_factory=tuple
    )


_ARABIC_DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


def normalize_historical_entity_text(
    value: str,
) -> str:

    value = _ARABIC_DIACRITICS.sub(
        "",
        value,
    )

    value = value.replace(
        "ـ",
        "",
    )

    value = value.translate(
        str.maketrans(
            {
                "أ": "ا",
                "إ": "ا",
                "آ": "ا",
                "ٱ": "ا",
                "ى": "ي",
            }
        )
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip().casefold()


def _alias_time_compatible(
    alias: HistoricalEntityAlias,
    *,
    query_year_ah: int | None,
) -> bool:

    if query_year_ah is None:
        return True

    if (
        alias.valid_from_ah
        is not None
        and query_year_ah
        < alias.valid_from_ah
    ):
        return False

    if (
        alias.valid_to_ah
        is not None
        and query_year_ah
        > alias.valid_to_ah
    ):
        return False

    return True


def _requires_ambiguity(
    *,
    record: HistoricalEntityRecord,
    matched_alias: HistoricalEntityAlias,
    query_year_ah: int | None,
) -> bool:

    if (
        record.ambiguity_status
        is not HistoricalEntityAmbiguity
        .UNAMBIGUOUS
    ):
        return True

    if (
        matched_alias.relation
        in {
            HistoricalAliasRelation
            .ADMINISTRATIVE_SUCCESSOR,

            HistoricalAliasRelation
            .GEOGRAPHIC_OVERLAP,
        }
    ):
        return True

    if (
        query_year_ah is None
        and (
            matched_alias.valid_from_ah
            is not None
            or matched_alias.valid_to_ah
            is not None
        )
    ):
        return True

    return False


def resolve_historical_entities_for_retrieval(
    *,
    query_text: str,
    registry: tuple[
        HistoricalEntityRecord,
        ...
    ],
    query_year_ah: int | None = None,
) -> tuple[
    HistoricalEntityMatch,
    ...
]:
    """
    Expand retrieval with governed historical aliases.

    Critical:

    ALIAS MATCH != HISTORICAL IDENTITY PROOF

    ENTITY RESOLUTION != ANSWER REWRITE

    ADMINISTRATIVE SUCCESSION != PLACE IDENTITY
    """

    normalized_query = (
        normalize_historical_entity_text(
            query_text
        )
    )

    preliminary: list[
        HistoricalEntityMatch
    ] = []

    for record in registry:

        candidates = [
            HistoricalEntityAlias(
                text=record.canonical_label,
                relation=(
                    HistoricalAliasRelation
                    .CANONICAL_LABEL
                ),
                evidence_ids=(
                    record.evidence_ids
                ),
            ),
            *record.aliases,
        ]

        matched: (
            HistoricalEntityAlias | None
        ) = None

        for alias in candidates:

            normalized_alias = (
                normalize_historical_entity_text(
                    alias.text
                )
            )

            if (
                normalized_alias
                and normalized_alias
                in normalized_query
            ):
                matched = alias
                break

        if matched is None:
            continue

        expansions: list[str] = []

        for alias in candidates:

            if not _alias_time_compatible(
                alias,
                query_year_ah=query_year_ah,
            ):
                continue

            if (
                alias.text
                not in expansions
            ):
                expansions.append(
                    alias.text
                )

        ambiguous = _requires_ambiguity(
            record=record,
            matched_alias=matched,
            query_year_ah=query_year_ah,
        )

        decision = (
            HistoricalEntityResolutionDecision
            .EXPAND_WITH_AMBIGUITY
            if ambiguous
            else
            HistoricalEntityResolutionDecision
            .EXPAND_RETRIEVAL
        )

        evidence_ids = tuple(
            dict.fromkeys(
                (
                    *record.evidence_ids,
                    *matched.evidence_ids,
                )
            )
        )

        preliminary.append(
            HistoricalEntityMatch(
                canonical_entity_id=(
                    record.canonical_entity_id
                ),
                entity_type=(
                    record.entity_type
                ),
                canonical_label=(
                    record.canonical_label
                ),
                matched_text=(
                    matched.text
                ),
                matched_relation=(
                    matched.relation
                ),
                retrieval_expansions=tuple(
                    expansions
                ),
                decision=decision,
                ambiguity_status=(
                    record.ambiguity_status
                ),
                evidence_ids=(
                    evidence_ids
                ),
            )
        )

    if not preliminary:
        return ()

    # Multiple possible entities from one user phrase must
    # remain ambiguous. No silent winner selection.
    canonical_ids = {
        item.canonical_entity_id
        for item in preliminary
    }

    if len(canonical_ids) <= 1:
        return tuple(
            preliminary
        )

    result = []

    for item in preliminary:

        result.append(
            HistoricalEntityMatch(
                canonical_entity_id=(
                    item.canonical_entity_id
                ),
                entity_type=(
                    item.entity_type
                ),
                canonical_label=(
                    item.canonical_label
                ),
                matched_text=(
                    item.matched_text
                ),
                matched_relation=(
                    item.matched_relation
                ),
                retrieval_expansions=(
                    item.retrieval_expansions
                ),
                decision=(
                    HistoricalEntityResolutionDecision
                    .EXPAND_WITH_AMBIGUITY
                ),
                ambiguity_status=(
                    HistoricalEntityAmbiguity
                    .MULTIPLE_CANDIDATES
                ),
                evidence_ids=(
                    item.evidence_ids
                ),
            )
        )

    return tuple(
        result
    )
