from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from basira.competition.bayyinat import (
    search_bayyinat,
)
from basira.competition.bayyinat_admission import (
    SOURCE_ID as BAYYINAT_SOURCE_ID,
)
from basira.competition.bayyinat_admission import (
    load_bayyinat_runtime_state,
)
from basira.competition.dorar_hadith_adapter import (
    DorarHadithEvidenceAdapter,
)
from basira.competition.dorar_tafsir_adapter import (
    DorarTafsirEvidenceAdapter,
)
from basira.competition.dorar_tafsir_admission import DorarTafsirRuntimeGate
from basira.competition.dorar_tafsir_retrieval import DorarTafsirRetriever
from basira.competition.dorar_transport import DorarHttpTransport
from basira.competition.jamhara_admission import (
    load_jamhara_runtime_state,
)
from basira.competition.jamhara_resolver import (
    SemanticStore,
    resolve_term,
)
from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.competition.quranpedia_adapter import QuranpediaEvidenceAdapter
from basira.competition.retrieval_bridge import (
    CompetitionEvidenceAdapter,
    CompetitionMaterialAdapter,
    CompetitionMaterialRole,
    CompetitionRetrievalRequest,
    CompetitionSourceMaterial,
)
from basira.evidence.fiqh_structural_adapter import (
    FiqhStructuralEvidenceAdapter,
)
from basira.evidence.fiqh_units import (
    FiqhStructuralUnitBuilder,
)
from basira.evidence.models import (
    ContextRequirement,
    EvidenceDomain,
    EvidenceNode,
)
from basira.reasoning.routing import (
    ReligiousReasoningRouter,
)
from basira.retrieval.arabic_query import (
    build_arabic_query,
)
from basira.retrieval.fiqh_evidence_projector import (
    FiqhEvidenceProjector,
)
from basira.retrieval.fiqh_policy_compiler import (
    FiqhRetrievalPolicyEnvelope,
    bind_fiqh_policy,
)
from basira.retrieval.query_understanding import (
    BasiraIntent,
    BasiraQueryUnderstanding,
)
from basira.retrieval.shamela_scout import (
    ShamelaHybridEvidenceScout,
    ShamelaPlanningAdvisor,
    ShamelaScoutPlanner,
    ShamelaScoutStopReason,
    ShamelaSearchBackend,
)


def _enum_value(
    value: object,
) -> str:
    enum_value = getattr(
        value,
        "value",
        value,
    )

    return str(enum_value)


def _clean_text(
    value: object,
) -> str | None:
    if not isinstance(
        value,
        str,
    ):
        return None

    value = " ".join(value.split())

    return value or None


def _source_strings(
    value: object,
) -> tuple[str, ...]:
    """
    Extract only text already present in the source
    object. Never manufacture semantic content.
    """

    if isinstance(
        value,
        str,
    ):
        cleaned = _clean_text(value)

        return (cleaned,) if cleaned else ()

    if isinstance(
        value,
        Mapping,
    ):
        values: list[str] = []

        for nested in value.values():
            values.extend(_source_strings(nested))

        return tuple(values)

    if isinstance(
        value,
        (list, tuple),
    ):
        values = []

        for nested in value:
            values.extend(_source_strings(nested))

        return tuple(values)

    return ()


_METADATA_KEYS = frozenset(
    {
        "id",
        "unit_id",
        "word_id",
        "source_id",
        "source_url",
        "canonical_url",
        "url",
        "hash",
        "sha256",
        "score",
        "rank",
        "language",
        "resolved_language",
    }
)


_PREFERRED_TEXT_KEYS = (
    "title",
    "question",
    "objection",
    "answer",
    "reply",
    "response",
    "terminological_meaning",
    "meaning",
    "definition",
    "summary",
    "content",
    "body",
    "text",
)


def _mapping_text(
    value: Mapping[str, object],
) -> str | None:
    pieces: list[str] = []
    seen: set[str] = set()

    def add(
        raw: object,
    ) -> None:
        for text in _source_strings(raw):
            if text in seen:
                continue

            seen.add(text)
            pieces.append(text)

    for key in _PREFERRED_TEXT_KEYS:
        if key in value:
            add(value[key])

    if not pieces:
        for key, raw in value.items():
            if key in _METADATA_KEYS:
                continue

            add(raw)

    if not pieces:
        return None

    return "\n\n".join(pieces)


def _source_url(
    value: Mapping[str, object],
) -> str | None:
    for key in (
        "source_url",
        "canonical_url",
        "url",
    ):
        cleaned = _clean_text(value.get(key))

        if cleaned:
            return cleaned

    return None


def _stable_material_id(
    prefix: str,
    value: Mapping[str, object],
) -> str:
    for key in (
        "unit_id",
        "word_id",
        "id",
        "reference",
        "source_locator",
    ):
        raw = value.get(key)

        if raw is not None:
            cleaned = " ".join(str(raw).split())

            if cleaned:
                return f"{prefix}:{cleaned}"

    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )

    digest = sha256(canonical.encode("utf-8")).hexdigest()[:20]

    return f"{prefix}:{digest}"


class BayyinatMaterialAdapter:
    """
    Bayyinat is conversational material only.

    It may structure or frame a shubhah response, but
    this adapter can never emit primary EvidenceNodes.
    """

    def __init__(
        self,
        *,
        search: Callable[
            [str, int],
            list[dict],
        ] = search_bayyinat,
        runtime_loader: Callable[
            [],
            Any,
        ] = load_bayyinat_runtime_state,
    ) -> None:
        self._search = search
        self._runtime_loader = runtime_loader

    @staticmethod
    def runtime_ready(
        state: object,
    ) -> bool:
        return (
            _enum_value(
                getattr(
                    state,
                    "eligibility",
                    "",
                )
            )
            == "eligible"
            and bool(
                getattr(
                    state,
                    "exact_artifact_governed",
                    False,
                )
            )
            and bool(
                getattr(
                    state,
                    "source_identity_verified",
                    False,
                )
            )
        )

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        CompetitionSourceMaterial,
        ...,
    ]:
        state = self._runtime_loader()

        if not self.runtime_ready(state):
            return ()

        hits = self._search(
            request.query,
            request.limit,
        )

        materials = []

        for hit in hits:
            text = _mapping_text(hit)

            if not text:
                continue

            materials.append(
                CompetitionSourceMaterial(
                    material_id=(
                        _stable_material_id(
                            "bayyinat",
                            hit,
                        )
                    ),
                    source_id=(BAYYINAT_SOURCE_ID),
                    role=(CompetitionMaterialRole.CONVERSATIONAL),
                    text=text,
                    source_url=(_source_url(hit)),
                )
            )

        return tuple(materials)


@dataclass(
    frozen=True,
    slots=True,
)
class JamharaResolverConfig:
    raw_cache_dir: Path
    warmer_state_db: Path
    semantic_store_db: Path

    language: str = "ar"

    # Offline by default.
    # Production composition must opt into network.
    allow_network: bool = False


class JamharaTerminologyAdapter:
    """
    Jamhara authority is terminology-only.

    It can never emit religious primary EvidenceNodes.
    """

    def __init__(
        self,
        *,
        config: JamharaResolverConfig,
        resolver: Callable[..., dict[str, object] | None] = (resolve_term),
        runtime_loader: Callable[
            [],
            Any,
        ] = load_jamhara_runtime_state,
        store_factory: Callable[
            [Path],
            Any,
        ] = SemanticStore,
    ) -> None:
        self._config = config
        self._resolver = resolver
        self._runtime_loader = runtime_loader
        self._store_factory = store_factory

    @staticmethod
    def runtime_ready(
        state: object,
    ) -> bool:
        return (
            bool(
                getattr(
                    state,
                    "eligible",
                    False,
                )
            )
            and bool(
                getattr(
                    state,
                    "source_identity_verified",
                    False,
                )
            )
            and bool(
                getattr(
                    state,
                    "implementation_governed",
                    False,
                )
            )
            and bool(
                getattr(
                    state,
                    "terminology_only",
                    False,
                )
            )
            and not bool(
                getattr(
                    state,
                    "cross_domain_primary_evidence",
                    True,
                )
            )
        )

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        CompetitionSourceMaterial,
        ...,
    ]:
        state = self._runtime_loader()

        if not self.runtime_ready(state):
            return ()

        store = self._store_factory(self._config.semantic_store_db)

        try:
            unit = self._resolver(
                query=request.query,
                language=(self._config.language),
                raw_cache_dir=(self._config.raw_cache_dir),
                warmer_state_db=(self._config.warmer_state_db),
                store=store,
                allow_network=(self._config.allow_network),
            )
        finally:
            close = getattr(
                store,
                "close",
                None,
            )

            if close is not None:
                close()

        if unit is None:
            return ()

        text = _mapping_text(unit)

        if not text:
            return ()

        return (
            CompetitionSourceMaterial(
                material_id=(
                    _stable_material_id(
                        "jamhara",
                        unit,
                    )
                ),
                source_id=str(state.source_id),
                role=(CompetitionMaterialRole.TERMINOLOGY),
                text=text,
                source_url=(_source_url(unit)),
            ),
        )


class PolicyBoundShamelaPlanner(ShamelaScoutPlanner):
    """
    Reuse the proven Hybrid Scout planner underneath
    the NEW competition Fiqh authority envelope.

    Query strategy may adapt.
    Source/work authority may not.
    """

    def __init__(
        self,
        envelope: FiqhRetrievalPolicyEnvelope,
    ) -> None:
        self._envelope = envelope

    def build(
        self,
        route,
    ):
        baseline = super().build(route)

        return bind_fiqh_policy(
            baseline,
            self._envelope,
        )


class FiqhHybridEvidenceAdapter:
    """
    Competition Fiqh lane backed by the bounded
    Hybrid Scout.

    The request MUST already contain the immutable
    Fiqh policy envelope compiled by governance.
    """

    def __init__(
        self,
        *,
        backend: ShamelaSearchBackend,
        advisor: (ShamelaPlanningAdvisor | None) = None,
    ) -> None:
        self._backend = backend
        self._advisor = advisor

    @property
    def is_available(
        self,
    ) -> bool:
        return bool(self._backend.is_available)

    @staticmethod
    def _route(
        text: str,
    ):
        understanding = BasiraQueryUnderstanding(
            query=build_arabic_query(text),
            primary_intent=(BasiraIntent.FIQH_QUESTION),
            risk_tags=frozenset(),
            entities=(),
            context_requirement=(ContextRequirement()),
            confidence=1.0,
        )

        return ReligiousReasoningRouter().route(understanding)

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]:
        policy = request.fiqh_policy

        if policy is None:
            raise ValueError("Fiqh adapter requires FiqhRetrievalPolicyEnvelope.")

        if not self.is_available:
            return ()

        if not policy.allowed_work_ids:
            # No governed primary book is authorized.
            return ()

        planner = PolicyBoundShamelaPlanner(policy)

        scout = ShamelaHybridEvidenceScout(
            backend=self._backend,
            planner=planner,
            advisor=self._advisor,
        )

        result = scout.scout(
            self._route(request.query),
            limit_per_task=(request.limit),
        )

        if result.stop_reason is ShamelaScoutStopReason.SOURCE_UNAVAILABLE:
            return ()

        allowed = frozenset(
            policy.allowed_work_ids
        )

        # The Hybrid Agent may search broadly through
        # bounded reformulations, but answer-bearing
        # evidence is narrowed to exact source slices.
        query_hints = tuple(
            dict.fromkeys(
                (
                    request.query,
                    *result.executed_query_hints,
                )
            )
        )

        projector = FiqhEvidenceProjector()
        unit_builder = FiqhStructuralUnitBuilder()
        structural_adapter = (
            FiqhStructuralEvidenceAdapter()
        )

        projected_nodes = []

        for hit in result.hits:
            # Authority boundary BEFORE projection.
            # A highly relevant unauthorized book must
            # never enter the answer-bearing lane.
            if (
                hit.passage.work_id
                not in allowed
            ):
                continue

            projected_passage = (
                projector.project_passage(
                    hit.passage,
                    query_hints=query_hints,
                )
            )

            # Fail narrow. Never fall back to the whole
            # page merely because projection failed.
            if projected_passage is None:
                continue

            unit = (
                unit_builder
                .from_projected_passage(
                    projected_passage
                )
            )

            structural_nodes = (
                structural_adapter
                .from_unit(
                    unit
                )
            )

            for node in structural_nodes:
                # Final defensive authority/domain
                # boundary applies to EVERY structural
                # child node, not only its parent.
                if (
                    node.domain
                    is not EvidenceDomain.FIQH
                    or node.work_id
                    not in allowed
                ):
                    continue

                projected_nodes.append(
                    node
                )

        return tuple(
            projected_nodes
        )

@dataclass(
    frozen=True,
    slots=True,
)
class CompetitionAdapterSet:
    evidence: Mapping[
        OfficialDomain,
        CompetitionEvidenceAdapter,
    ]

    materials: Mapping[
        OfficialDomain,
        CompetitionMaterialAdapter,
    ]


def build_ready_competition_adapters(
    *,
    quran: (QuranpediaEvidenceAdapter | None) = None,
    hadith: (DorarHadithEvidenceAdapter | None) = None,
    tafsir: (DorarTafsirEvidenceAdapter | None) = None,
    fiqh_backend: (ShamelaSearchBackend | None) = None,
    fiqh_advisor: (ShamelaPlanningAdvisor | None) = None,
    jamhara: (JamharaResolverConfig | None) = None,
) -> CompetitionAdapterSet:
    """
    Register ONLY lanes with a real retrieval runtime.

    Register only lanes with real governed runtime.

    Dorar Hadith can be injected once composed from:
    governed transport -> parser -> Hadith policy.

    Dorar Tafsir/Fiqh/History/Aqeedah remain
    unregistered until their retrieval transports are
    implemented.
    """

    evidence: dict[
        OfficialDomain,
        CompetitionEvidenceAdapter,
    ] = {}

    if quran is not None:
        evidence[OfficialDomain.QURAN] = quran
    if hadith is not None:
        evidence[OfficialDomain.HADITH] = hadith
    if tafsir is not None:
        evidence[OfficialDomain.TAFSIR] = tafsir

    materials: dict[
        OfficialDomain,
        CompetitionMaterialAdapter,
    ] = {}

    bayyinat = BayyinatMaterialAdapter()

    if bayyinat.runtime_ready(load_bayyinat_runtime_state()):
        materials[OfficialDomain.SHUBUHAT_FAQ] = bayyinat

    if jamhara is not None:
        terminology = JamharaTerminologyAdapter(config=jamhara)

        if terminology.runtime_ready(load_jamhara_runtime_state()):
            materials[OfficialDomain.TRANSLATION_TERMINOLOGY] = terminology

    if fiqh_backend is not None and fiqh_backend.is_available:
        evidence[OfficialDomain.GENERAL_FIQH] = FiqhHybridEvidenceAdapter(
            backend=fiqh_backend,
            advisor=fiqh_advisor,
        )

    return CompetitionAdapterSet(
        evidence=evidence,
        materials=materials,
    )


def build_live_dorar_tafsir_adapter(
    *,
    repo_root: Path | str = ".",
    transport: DorarHttpTransport | None = None,
) -> DorarTafsirEvidenceAdapter:
    """
    Compose the already-governed Dorar Tafsir runtime.

    Authority remains inside:
        passport
        -> artifact verification
        -> DorarTafsirRuntimeGate
        -> OfficialTafsirPolicy

    This builder adds no fallback and grants no new
    evidentiary authority.
    """

    root = Path(repo_root).resolve()

    gate = DorarTafsirRuntimeGate.from_repo(root)

    active_transport = transport if transport is not None else DorarHttpTransport()

    retriever = DorarTafsirRetriever(
        transport=active_transport,
        gate=gate,
    )

    return DorarTafsirEvidenceAdapter(
        retriever=retriever,
    )
