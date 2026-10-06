from basira.competition.history_entities import (
    HistoricalAliasRelation,
    HistoricalEntityAlias,
    HistoricalEntityAmbiguity,
    HistoricalEntityRecord,
    HistoricalEntityResolutionDecision,
    HistoricalEntityType,
    resolve_historical_entities_for_retrieval,
)


def sample_place():
    return HistoricalEntityRecord(
        canonical_entity_id=(
            "place:test-city"
        ),
        entity_type=(
            HistoricalEntityType.PLACE
        ),
        canonical_label=(
            "المدينة الحديثة"
        ),
        aliases=(
            HistoricalEntityAlias(
                text="الاسم التاريخي",
                relation=(
                    HistoricalAliasRelation
                    .HISTORICAL_NAME
                ),
                valid_to_ah=500,
                evidence_ids=(
                    "entity:test:historical",
                ),
            ),
            HistoricalEntityAlias(
                text="الاسم الحديث",
                relation=(
                    HistoricalAliasRelation
                    .MODERN_NAME
                ),
                valid_from_ah=1200,
                evidence_ids=(
                    "entity:test:modern",
                ),
            ),
        ),
        ambiguity_status=(
            HistoricalEntityAmbiguity
            .UNAMBIGUOUS
        ),
        evidence_ids=(
            "entity:test",
        ),
    )


def test_modern_name_can_expand_to_historical_alias_for_retrieval() -> None:
    result = (
        resolve_historical_entities_for_retrieval(
            query_text=(
                "ماذا حدث في الاسم الحديث؟"
            ),
            registry=(
                sample_place(),
            ),
            query_year_ah=200,
        )
    )

    assert len(result) == 1

    match = result[0]

    assert (
        match.canonical_entity_id
        == "place:test-city"
    )

    assert (
        "الاسم التاريخي"
        in match.retrieval_expansions
    )

    assert (
        "الاسم الحديث"
        not in match.retrieval_expansions
    )


def test_entity_resolution_is_retrieval_only() -> None:
    result = (
        resolve_historical_entities_for_retrieval(
            query_text=(
                "الاسم الحديث"
            ),
            registry=(
                sample_place(),
            ),
        )
    )

    assert len(result) == 1

    assert (
        result[0].may_assert_identity
        is False
    )

    assert (
        result[
            0
        ].may_rewrite_answer_entity_as_equivalent
        is False
    )


def test_time_sensitive_alias_without_time_context_preserves_ambiguity() -> None:
    result = (
        resolve_historical_entities_for_retrieval(
            query_text=(
                "الاسم التاريخي"
            ),
            registry=(
                sample_place(),
            ),
        )
    )

    assert len(result) == 1

    assert (
        result[0].decision
        is HistoricalEntityResolutionDecision
        .EXPAND_WITH_AMBIGUITY
    )


def test_administrative_successor_never_becomes_identity_proof() -> None:
    record = HistoricalEntityRecord(
        canonical_entity_id="region:test",
        entity_type=(
            HistoricalEntityType.REGION
        ),
        canonical_label="إقليم تاريخي",
        aliases=(
            HistoricalEntityAlias(
                text="دولة حديثة",
                relation=(
                    HistoricalAliasRelation
                    .ADMINISTRATIVE_SUCCESSOR
                ),
                evidence_ids=(
                    "entity:successor:test",
                ),
            ),
        ),
        ambiguity_status=(
            HistoricalEntityAmbiguity
            .GEOGRAPHICALLY_AMBIGUOUS
        ),
        evidence_ids=(
            "entity:region:test",
        ),
    )

    result = (
        resolve_historical_entities_for_retrieval(
            query_text="دولة حديثة",
            registry=(
                record,
            ),
        )
    )

    assert len(result) == 1

    assert (
        result[0].decision
        is HistoricalEntityResolutionDecision
        .EXPAND_WITH_AMBIGUITY
    )

    assert (
        result[0].may_assert_identity
        is False
    )


def test_multiple_entity_candidates_do_not_select_silent_winner() -> None:
    first = HistoricalEntityRecord(
        canonical_entity_id="place:1",
        entity_type=(
            HistoricalEntityType.PLACE
        ),
        canonical_label="الموضع الأول",
        aliases=(
            HistoricalEntityAlias(
                text="الاسم المشترك",
                relation=(
                    HistoricalAliasRelation
                    .ALTERNATE_NAME
                ),
            ),
        ),
        ambiguity_status=(
            HistoricalEntityAmbiguity
            .UNAMBIGUOUS
        ),
    )

    second = HistoricalEntityRecord(
        canonical_entity_id="place:2",
        entity_type=(
            HistoricalEntityType.PLACE
        ),
        canonical_label="الموضع الثاني",
        aliases=(
            HistoricalEntityAlias(
                text="الاسم المشترك",
                relation=(
                    HistoricalAliasRelation
                    .ALTERNATE_NAME
                ),
            ),
        ),
        ambiguity_status=(
            HistoricalEntityAmbiguity
            .UNAMBIGUOUS
        ),
    )

    result = (
        resolve_historical_entities_for_retrieval(
            query_text="الاسم المشترك",
            registry=(
                first,
                second,
            ),
        )
    )

    assert len(result) == 2

    assert all(
        item.decision
        is HistoricalEntityResolutionDecision
        .EXPAND_WITH_AMBIGUITY
        for item in result
    )

    assert all(
        item.ambiguity_status
        is HistoricalEntityAmbiguity
        .MULTIPLE_CANDIDATES
        for item in result
    )


def test_no_registry_match_does_not_invent_entity() -> None:
    result = (
        resolve_historical_entities_for_retrieval(
            query_text="اسم غير موجود",
            registry=(
                sample_place(),
            ),
        )
    )

    assert result == ()
