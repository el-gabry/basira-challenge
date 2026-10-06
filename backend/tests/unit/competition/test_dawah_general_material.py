import pytest

from basira.competition.general_material_runtime import (
    DAWA_CENTER_SOURCE_ID,
    DAWA_CENTER_URL,
    DawaCenterRoutingMaterialAdapter,
    GeneralMaterialLane,
    GeneralMaterialRuntime,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionAuthorityBoundaryError,
    CompetitionMaterialRole,
    CompetitionRetrievalRequest,
)


def test_dawa_adapter_is_routing_context_only() -> None:
    adapter = DawaCenterRoutingMaterialAdapter()

    materials = adapter.retrieve(
        CompetitionRetrievalRequest(
            official_domain=(OfficialDomain.DAWAH_GENERAL_CONTENT),
            query=("كيف أدعو صديقي إلى الإسلام؟"),
        )
    )

    assert len(materials) == 1

    item = materials[0]

    assert item.source_id == DAWA_CENTER_SOURCE_ID

    assert item.role is CompetitionMaterialRole.ROUTING_CONTEXT

    assert item.text == "Dawa Center"

    assert item.source_url == DAWA_CENTER_URL

    # User input must not be recycled as
    # alleged source content.
    assert "كيف أدعو" not in item.text


def test_dawa_adapter_cannot_cross_authority_boundary() -> None:
    adapter = DawaCenterRoutingMaterialAdapter()

    with pytest.raises(CompetitionAuthorityBoundaryError):
        adapter.retrieve(
            CompetitionRetrievalRequest(
                official_domain=(OfficialDomain.SHUBUHAT_FAQ),
                query="test",
            )
        )


def test_dawah_runtime_returns_material_not_evidence() -> None:
    result = GeneralMaterialRuntime().retrieve(
        question=("كيف أدعو صديقي إلى الإسلام؟"),
        language="ar",
    )

    assert result.lane is GeneralMaterialLane.DAWAH

    assert result.official_domain is OfficialDomain.DAWAH_GENERAL_CONTENT

    assert len(result.materials) == 1

    item = result.materials[0]

    assert item.role is CompetitionMaterialRole.ROUTING_CONTEXT

    assert item.source_id == DAWA_CENTER_SOURCE_ID

    assert item.source_url == DAWA_CENTER_URL

    assert result.unavailable_reason is None


def test_general_concept_still_fails_closed() -> None:
    result = GeneralMaterialRuntime().retrieve(
        question="ما هو الكرسي؟",
        language="ar",
    )

    assert result.lane is GeneralMaterialLane.GENERAL

    assert result.materials == ()

    assert result.unavailable_reason == ("governed_general_runtime_not_implemented")
