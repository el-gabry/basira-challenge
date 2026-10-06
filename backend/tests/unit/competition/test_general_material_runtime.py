from __future__ import annotations

from dataclasses import dataclass

from basira.competition.general_material_runtime import (
    GeneralMaterialLane,
    GeneralMaterialRuntime,
    _select_general_lane,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_bridge import (
    CompetitionMaterialRole,
    CompetitionRetrievalRequest,
    CompetitionSourceMaterial,
)
from basira.retrieval.hybrid_query_resolver import (
    resolve_hybrid_query,
)


@dataclass
class FakeAdapter:
    materials: tuple[
        CompetitionSourceMaterial,
        ...,
    ]

    calls: int = 0

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        CompetitionSourceMaterial,
        ...,
    ]:
        self.calls += 1

        return self.materials


def test_shubuhat_is_general_material_lane() -> None:
    question = "لماذا يعبد المسلمون الكعبة؟"

    resolution = resolve_hybrid_query(
        question=question,
        language="ar",
    )

    assert (
        _select_general_lane(
            question=question,
            resolution=resolution,
        )
        is GeneralMaterialLane.SHUBUHAT
    )


def test_dawah_is_separate_general_lane() -> None:
    question = "كيف أدعو صديقي إلى الإسلام؟"

    resolution = resolve_hybrid_query(
        question=question,
        language="ar",
    )

    assert (
        _select_general_lane(
            question=question,
            resolution=resolution,
        )
        is GeneralMaterialLane.DAWAH
    )


def test_bare_general_concept_stays_general() -> None:
    question = "ما هو الكرسي؟"

    resolution = resolve_hybrid_query(
        question=question,
        language="ar",
    )

    assert (
        _select_general_lane(
            question=question,
            resolution=resolution,
        )
        is GeneralMaterialLane.GENERAL
    )


def test_arabic_shubuhat_uses_bayyinat_material() -> None:
    material = CompetitionSourceMaterial(
        material_id="b-1",
        source_id="bayyinat-v1",
        role=(CompetitionMaterialRole.CONVERSATIONAL),
        text="نص توضيحي",
        source_url=("https://dawa.center/file/7937"),
    )

    adapter = FakeAdapter(
        materials=(material,),
    )

    runtime = GeneralMaterialRuntime(
        bayyinat_adapter=adapter,
    )

    result = runtime.retrieve(
        question=("لماذا يعبد المسلمون الكعبة؟"),
        language="ar",
    )

    assert result.lane is GeneralMaterialLane.SHUBUHAT

    assert result.official_domain is OfficialDomain.SHUBUHAT_FAQ

    assert result.materials == (material,)

    assert adapter.calls == 1


def test_english_shubuhat_does_not_use_arabic_bayyinat() -> None:
    adapter = FakeAdapter(
        materials=(),
    )

    runtime = GeneralMaterialRuntime(
        bayyinat_adapter=adapter,
    )

    result = runtime.retrieve(
        question=("Why do Muslims worship the Kaaba?"),
        language="en",
    )

    assert result.materials == ()

    assert adapter.calls == 0

    assert result.unavailable_reason == ("source_native_shubuhat_language_unavailable")


def test_dawah_returns_governed_routing_material_only() -> None:
    result = GeneralMaterialRuntime().retrieve(
        question=("كيف أدعو صديقي إلى الإسلام؟"),
        language="ar",
    )

    assert result.lane is GeneralMaterialLane.DAWAH

    assert result.official_domain is OfficialDomain.DAWAH_GENERAL_CONTENT

    assert len(result.materials) == 1

    material = result.materials[0]

    assert material.source_id == "dawa-center-routing-v1"

    assert material.role is CompetitionMaterialRole.ROUTING_CONTEXT

    assert material.source_url == "https://dawa.center/"

    assert material.text == "Dawa Center"

    assert result.unavailable_reason is None


def test_general_concept_does_not_fall_through_to_religious_evidence() -> None:
    result = GeneralMaterialRuntime().retrieve(
        question="ما هو الكرسي؟",
        language="ar",
    )

    assert result.lane is GeneralMaterialLane.GENERAL

    assert result.official_domain is None

    assert result.materials == ()

    assert result.unavailable_reason == ("governed_general_runtime_not_implemented")


def test_hadith_never_enters_general_material_lane() -> None:
    result = GeneralMaterialRuntime().retrieve(
        question="ما صحة حديث 65065؟",
        language="ar",
    )

    assert result.lane is None
    assert result.materials == ()
    assert result.official_domain is None


def test_real_bayyinat_public_projection_is_single_precise_unit() -> None:
    from basira.competition.general_material_runtime import (
        _high_precision_bayyinat_search,
    )

    hits = _high_precision_bayyinat_search(
        "لماذا يعبد المسلمون الكعبة؟",
        5,
    )

    assert len(hits) == 1

    hit = hits[0]

    assert "الكعبة" in str(hit["text"])

    assert len(str(hit["text"])) > len("لماذا يعبد المسلمون الكعبة والحجر الاسود")

    assert hit.get("source_url") == "https://dawa.center/file/7937"


def test_public_bayyinat_returns_only_strongest_unit() -> None:
    from basira.competition.general_material_runtime import (
        GeneralMaterialRuntime,
    )

    result = GeneralMaterialRuntime().retrieve(
        question=("لماذا يعبد المسلمون الكعبة؟"),
        language="ar",
        limit=5,
    )

    assert len(result.materials) == 1

    material = result.materials[0]

    assert material.source_id == "bayyinat-v1"

    assert material.source_url == "https://dawa.center/file/7937"

    assert "الكعبة" in material.text
