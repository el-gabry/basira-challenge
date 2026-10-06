from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from basira.competition.bayyinat import (
    search_bayyinat,
)
from basira.competition.jamhara_resolver import (
    resolve_term,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.retrieval_adapters import (
    BayyinatMaterialAdapter,
    JamharaResolverConfig,
    JamharaTerminologyAdapter,
)
from basira.competition.retrieval_bridge import (
    CompetitionAuthorityBoundaryError,
    CompetitionMaterialAdapter,
    CompetitionMaterialRole,
    CompetitionRetrievalRequest,
    CompetitionSourceMaterial,
)
from basira.retrieval.hybrid_query_resolver import (
    HybridQueryResolution,
    HybridTopic,
    resolve_hybrid_query,
)


class GeneralMaterialLane(StrEnum):
    SHUBUHAT = "shubuhat"
    TERMINOLOGY = "terminology"
    DAWAH = "dawah"
    GENERAL = "general_concepts"


@dataclass(
    frozen=True,
    slots=True,
)
class GeneralMaterialResult:
    resolution: HybridQueryResolution

    lane: GeneralMaterialLane | None = None

    official_domain: OfficialDomain | None = None

    materials: tuple[
        CompetitionSourceMaterial,
        ...,
    ] = ()

    unavailable_reason: str | None = None

    @property
    def available(
        self,
    ) -> bool:
        return bool(self.materials)


MaterialFactory = Callable[
    [str],
    CompetitionMaterialAdapter,
]


DAWA_CENTER_SOURCE_ID = "dawa-center-routing-v1"

DAWA_CENTER_URL = "https://dawa.center/"


class DawaCenterRoutingMaterialAdapter:
    """
    Governed routing-only material for Dawa Center.

    The frozen discovery contract exposes Dawa Center
    as routing context.

    This adapter MUST NOT:
    - create EvidenceNodes;
    - manufacture a religious answer;
    - promote routing metadata into authority.
    """

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        CompetitionSourceMaterial,
        ...,
    ]:
        if request.official_domain is not OfficialDomain.DAWAH_GENERAL_CONTENT:
            raise CompetitionAuthorityBoundaryError(
                "dawa_center_material_outside_governed_domain"
            )

        return (
            CompetitionSourceMaterial(
                material_id=("dawa-center-routing"),
                source_id=(DAWA_CENTER_SOURCE_ID),
                role=(CompetitionMaterialRole.ROUTING_CONTEXT),
                # Deliberately source identity only.
                #
                # We do NOT turn the user's question,
                # discovery metadata, or inferred text
                # into a religious answer.
                text="Dawa Center",
                source_url=(DAWA_CENTER_URL),
            ),
        )


_DAWAH_MARKERS = (
    "الدعوة",
    "دعوة",
    "أدعو",
    "ادعو",
    "كيف أدعو",
    "دعوة غير المسلمين",
    "dawah",
    "da'wah",
    "da‘wah",
    "invite to islam",
    "inviting to islam",
    "calling to islam",
    "how to invite",
)


def _is_dawah_question(
    question: str,
) -> bool:
    value = " ".join(question.casefold().split())

    return any(marker.casefold() in value for marker in _DAWAH_MARKERS)


def _select_general_lane(
    *,
    question: str,
    resolution: HybridQueryResolution,
) -> GeneralMaterialLane | None:
    if resolution.topic is HybridTopic.SHUBUHAT:
        return GeneralMaterialLane.SHUBUHAT

    if resolution.topic is HybridTopic.TERMINOLOGY:
        return GeneralMaterialLane.TERMINOLOGY

    if resolution.topic is HybridTopic.DAWAH:
        return GeneralMaterialLane.DAWAH

    if resolution.topic is HybridTopic.GENERAL:
        if _is_dawah_question(question):
            return GeneralMaterialLane.DAWAH

        return GeneralMaterialLane.GENERAL

    # Quran / Hadith / Tafsir / Fiqh and the
    # Phase-2 domains do not enter this layer.
    return None


def _source_native_jamhara_resolver(
    **kwargs: Any,
) -> dict[str, object] | None:
    """
    Jamhara may internally resolve an Arabic fallback.

    The public General layer must not silently expose
    that Arabic unit as source-native English material.
    """

    requested_language = str(
        kwargs.get(
            "language",
            "",
        )
    )

    result = resolve_term(
        **kwargs,
    )

    if result is None:
        return None

    if result.get("requested_language") != requested_language:
        return None

    if result.get("resolved_language") != requested_language:
        return None

    if (
        result.get(
            "fallback_to_arabic",
            False,
        )
        is not False
    ):
        return None

    return result


def _high_precision_bayyinat_search(
    query: str,
    limit: int,
) -> list[dict[str, object]]:
    """
    Precision-first public Bayyinat display.

    Existing search_bayyinat owns ranking.
    BayyinatMaterialAdapter owns runtime admission.
    This function only projects the strongest
    conversational unit for display.
    """

    hits = search_bayyinat(
        query,
        limit=max(
            10,
            limit,
        ),
    )

    if not hits:
        return []

    top = dict(hits[0])

    raw_title = top.get("title") or top.get("question_text") or ""

    raw_answer = top.get("short_answer") or top.get("detailed_answer") or ""

    title = " ".join(str(raw_title).split())

    answer = "\n".join(
        line.strip() for line in str(raw_answer).splitlines() if line.strip()
    )

    display_text = f"{title}\n\n{answer}" if title and answer else answer or title

    if not display_text:
        return []

    provenance = top.get("provenance")

    source_url = None

    if isinstance(
        provenance,
        dict,
    ):
        raw_url = provenance.get("official_locator")

        if isinstance(
            raw_url,
            str,
        ):
            cleaned_url = raw_url.strip()

            if cleaned_url:
                source_url = cleaned_url

    # BayyinatMaterialAdapter supports several
    # source shapes. Populate them consistently
    # so public projection cannot regress to
    # title-only output.
    top["text"] = display_text
    top["answer"] = display_text
    top["content"] = display_text
    top["question"] = display_text
    top["title"] = display_text

    if source_url is not None:
        top["source_url"] = source_url

    ordinal = top.get("ordinal")

    if ordinal is not None:
        top["unit_id"] = f"bayyinat-{ordinal}"

    # Same governed source, strongest result only.
    return [top]


def _default_jamhara_factory(
    language: str,
) -> CompetitionMaterialAdapter:
    root = Path.home() / ".cache" / "basira"

    return JamharaTerminologyAdapter(
        config=JamharaResolverConfig(
            raw_cache_dir=(root / "jamhara-full-abfac30-v1"),
            warmer_state_db=(root / "jamhara-warmer-v1.sqlite3"),
            semantic_store_db=(root / "jamhara-semantic-v1.sqlite3"),
            language=language,
            # Public display material must never
            # block the governed answer pipeline.
            #
            # Jamhara public lookup is cache/source-
            # native only. Cache warming is a separate
            # acquisition concern.
            allow_network=False,
        ),
        resolver=(_source_native_jamhara_resolver),
    )


class GeneralMaterialRuntime:
    """
    First-layer general Islamic material runtime.

    Evidence proves.
    Materials explain.

    These lanes MUST NOT manufacture EvidenceNodes or
    grant Quran/Hadith/Fiqh/Aqeedah authority.
    """

    def __init__(
        self,
        *,
        bayyinat_adapter: (CompetitionMaterialAdapter | None) = None,
        jamhara_factory: (MaterialFactory | None) = None,
    ) -> None:
        self.bayyinat_adapter = bayyinat_adapter or BayyinatMaterialAdapter(
            search=(_high_precision_bayyinat_search),
        )

        self.jamhara_factory = jamhara_factory or _default_jamhara_factory

    def retrieve(
        self,
        *,
        question: str,
        language: str | None = None,
        resolution: HybridQueryResolution | None = None,
        limit: int = 5,
    ) -> GeneralMaterialResult:
        if resolution is None:
            resolution = resolve_hybrid_query(
                question=question,
                language=language,
            )

        lane = _select_general_lane(
            question=question,
            resolution=resolution,
        )

        if lane is None:
            return GeneralMaterialResult(
                resolution=resolution,
            )

        if lane is GeneralMaterialLane.SHUBUHAT:
            return self._shubuhat(
                question=question,
                resolution=resolution,
                limit=limit,
            )

        if lane is GeneralMaterialLane.TERMINOLOGY:
            return self._terminology(
                question=question,
                resolution=resolution,
                limit=limit,
            )

        if lane is GeneralMaterialLane.DAWAH:
            return self._dawah(
                question=question,
                resolution=resolution,
                limit=limit,
            )

        # General concepts intentionally fail closed
        # until an explicit governed general-content
        # source family is admitted.
        return GeneralMaterialResult(
            resolution=resolution,
            lane=lane,
            unavailable_reason=("governed_general_runtime_not_implemented"),
        )

    def _dawah(
        self,
        *,
        question: str,
        resolution: HybridQueryResolution,
        limit: int,
    ) -> GeneralMaterialResult:
        """
        Return source navigation context only.

        Dawa Center currently has routing-context
        authority in Basira, not answer-bearing
        religious evidence authority.
        """

        adapter = DawaCenterRoutingMaterialAdapter()

        materials = adapter.retrieve(
            CompetitionRetrievalRequest(
                official_domain=(OfficialDomain.DAWAH_GENERAL_CONTENT),
                query=question,
                limit=limit,
            )
        )

        return GeneralMaterialResult(
            resolution=resolution,
            lane=GeneralMaterialLane.DAWAH,
            official_domain=(OfficialDomain.DAWAH_GENERAL_CONTENT),
            materials=materials,
        )

    def _shubuhat(
        self,
        *,
        question: str,
        resolution: HybridQueryResolution,
        limit: int,
    ) -> GeneralMaterialResult:
        # Current admitted Bayyinat artifact is the
        # governed Arabic conversational lane.
        if resolution.language != "ar":
            return GeneralMaterialResult(
                resolution=resolution,
                lane=(GeneralMaterialLane.SHUBUHAT),
                official_domain=(OfficialDomain.SHUBUHAT_FAQ),
                unavailable_reason=("source_native_shubuhat_language_unavailable"),
            )

        materials = self.bayyinat_adapter.retrieve(
            CompetitionRetrievalRequest(
                official_domain=(OfficialDomain.SHUBUHAT_FAQ),
                query=question,
                limit=limit,
            )
        )

        return GeneralMaterialResult(
            resolution=resolution,
            lane=(GeneralMaterialLane.SHUBUHAT),
            official_domain=(OfficialDomain.SHUBUHAT_FAQ),
            materials=materials,
        )

    def _terminology(
        self,
        *,
        question: str,
        resolution: HybridQueryResolution,
        limit: int,
    ) -> GeneralMaterialResult:
        adapter = self.jamhara_factory(resolution.language)

        materials = adapter.retrieve(
            CompetitionRetrievalRequest(
                official_domain=(OfficialDomain.TRANSLATION_TERMINOLOGY),
                query=question,
                limit=limit,
            )
        )

        return GeneralMaterialResult(
            resolution=resolution,
            lane=(GeneralMaterialLane.TERMINOLOGY),
            official_domain=(OfficialDomain.TRANSLATION_TERMINOLOGY),
            materials=materials,
            unavailable_reason=(
                None if materials else ("source_native_terminology_unavailable")
            ),
        )
