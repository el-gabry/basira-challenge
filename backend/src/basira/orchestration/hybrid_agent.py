from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from basira.retrieval.hybrid_query_resolver import (
    HybridQueryResolution,
    HybridTopic,
    ResponseGovernanceLevel,
    resolve_hybrid_query,
)


class HybridAgentHandoff(StrEnum):
    """
    Execution capability selected by the Hybrid Agent.

    This is NOT religious authority selection.

    The agent may choose which already-governed runtime
    must handle the question. It may never choose:
    - source authority
    - scholar
    - madhhab
    - hadith grade
    - tafsir conclusion
    - legal ruling
    """

    GOVERNED_CORE = "governed_core"
    GENERAL_MATERIAL = "general_material"
    FAIL_CLOSED = "fail_closed"


class HybridPublicationObligation(StrEnum):
    """
    Public-response obligation attached to the handoff.

    Final publication remains controlled by the existing
    Trust Shield / evidence governance pipeline.
    """

    GOVERNED_ANSWER = "governed_answer"

    PRESERVE_DISAGREEMENT = "preserve_disagreement"

    GENERAL_INFORMATION_AND_REFER = "general_information_and_refer"

    DISPLAY_ONLY = "display_only"

    FAIL_CLOSED = "fail_closed"


@dataclass(
    frozen=True,
    slots=True,
)
class ResolvedIdentityHint:
    """
    Candidate identity/reference resolved for convenience.

    This NEVER counts as evidence.

    The specialized governed runtime must verify it
    before it may affect a religious answer.
    """

    kind: str
    value: str

    verification_required: bool = True


@dataclass(
    frozen=True,
    slots=True,
)
class HybridAgentPlan:
    """
    Governed execution plan produced by the Hybrid Agent.

    Important:
    capability identifies an existing Basira capability.
    It is NOT a source ID and grants no religious authority.
    """

    resolution: HybridQueryResolution

    handoff: HybridAgentHandoff

    capability: str | None

    publication_obligation: HybridPublicationObligation

    requires_expert_referral: bool = False

    unavailable_reason: str | None = None

    identity_hints: tuple[
        ResolvedIdentityHint,
        ...,
    ] = ()

    @property
    def language(
        self,
    ) -> str:
        return self.resolution.language

    @property
    def direct_public_answer_allowed(
        self,
    ) -> bool:
        """
        Whether this PLAN permits attempting a normal
        governed answer.

        This property does NOT itself authorize publication.
        The Trust Shield still owns final publication.
        """

        return (
            self.handoff is HybridAgentHandoff.GOVERNED_CORE
            and self.publication_obligation
            in {
                HybridPublicationObligation.GOVERNED_ANSWER,
                (HybridPublicationObligation.PRESERVE_DISAGREEMENT),
            }
        )

    @property
    def material_only(
        self,
    ) -> bool:
        return self.handoff is HybridAgentHandoff.GENERAL_MATERIAL


def _resolved_identity_hints(
    *,
    question: str,
    resolution: HybridQueryResolution,
) -> tuple[
    ResolvedIdentityHint,
    ...,
]:
    """
    Resolve convenience candidates only.

    Examples:
    - "Ayat al-Kursi" -> candidate Quran 2:255
    - Hadith number -> candidate Hadith identifier

    Specialized governed systems perform verification.
    """

    normalized = " ".join(question.casefold().split())

    hints: list[ResolvedIdentityHint] = []

    if any(
        marker in normalized
        for marker in (
            "آية الكرسي",
            "اية الكرسي",
            "ayat al-kursi",
            "ayat al kursi",
            "ayat ul kursi",
        )
    ):
        hints.append(
            ResolvedIdentityHint(
                kind=("quran_reference_candidate"),
                value="2:255",
            )
        )

    if resolution.topic is HybridTopic.HADITH and resolution.identifier_candidate:
        hints.append(
            ResolvedIdentityHint(
                kind=("hadith_identifier_candidate"),
                value=(resolution.identifier_candidate),
            )
        )

    return tuple(hints)


_CORE_CAPABILITIES = {
    HybridTopic.QURAN: "quran",
    HybridTopic.HADITH: "hadith",
    HybridTopic.TAFSIR: "tafsir",
    HybridTopic.FIQH: "general_fiqh",
}


_MATERIAL_CAPABILITIES = {
    HybridTopic.SHUBUHAT: "shubuhat_faq",
    HybridTopic.DAWAH: "dawah_general_content",
    HybridTopic.TERMINOLOGY: ("translation_terminology"),
    HybridTopic.GENERAL: "general_islamic",
}


_PHASE_2_TOPICS = frozenset(
    {
        HybridTopic.AQEEDAH,
        HybridTopic.HISTORY,
    }
)


def _fail_closed(
    resolution: HybridQueryResolution,
    *,
    reason: str,
) -> HybridAgentPlan:
    return HybridAgentPlan(
        resolution=resolution,
        handoff=(HybridAgentHandoff.FAIL_CLOSED),
        capability=None,
        publication_obligation=(HybridPublicationObligation.FAIL_CLOSED),
        unavailable_reason=reason,
    )


def govern_hybrid_resolution(
    resolution: HybridQueryResolution,
) -> HybridAgentPlan:
    """
    Convert resolver output into a governed runtime handoff.

    Resolver:
        What kind of problem is this?

    Hybrid Agent:
        Which existing governed capability may handle it?

    Policy / runtime:
        Which religious sources may actually be trusted?

    Trust Shield:
        What may finally be published?
    """

    # -------------------------------------------------
    # Global invariant:
    # no silent cross-language authority substitution.
    # -------------------------------------------------

    if resolution.allow_cross_language_fallback is not False:
        return _fail_closed(
            resolution,
            reason=("cross_language_fallback_not_permitted"),
        )

    # -------------------------------------------------
    # Frozen Phase 2 domains.
    # -------------------------------------------------

    if resolution.topic in _PHASE_2_TOPICS:
        return _fail_closed(
            resolution,
            reason=("phase_2_capability_not_admitted"),
        )

    # -------------------------------------------------
    # Display-only General lanes.
    #
    # Evidence proves.
    # Materials explain.
    # -------------------------------------------------

    if resolution.topic in _MATERIAL_CAPABILITIES:
        expected = _MATERIAL_CAPABILITIES[resolution.topic]

        if resolution.capability != expected:
            return _fail_closed(
                resolution,
                reason=("resolver_capability_mismatch"),
            )

        return HybridAgentPlan(
            resolution=resolution,
            handoff=(HybridAgentHandoff.GENERAL_MATERIAL),
            capability=expected,
            publication_obligation=(HybridPublicationObligation.DISPLAY_ONLY),
        )

    # -------------------------------------------------
    # Existing governed evidence lanes.
    # -------------------------------------------------

    expected = _CORE_CAPABILITIES.get(resolution.topic)

    if expected is None:
        return _fail_closed(
            resolution,
            reason=("no_governed_capability"),
        )

    if resolution.capability != expected:
        return _fail_closed(
            resolution,
            reason=("resolver_capability_mismatch"),
        )

    # -------------------------------------------------
    # Personalized Fiqh:
    #
    # general governed information may be used,
    # but the Hybrid Agent may NOT authorize a
    # personalized fatwa.
    # -------------------------------------------------

    if resolution.topic is HybridTopic.FIQH and (
        resolution.personalized
        or (resolution.response_level is ResponseGovernanceLevel.D)
    ):
        return HybridAgentPlan(
            resolution=resolution,
            handoff=(HybridAgentHandoff.GOVERNED_CORE),
            capability=expected,
            publication_obligation=(
                HybridPublicationObligation.GENERAL_INFORMATION_AND_REFER
            ),
            requires_expert_referral=True,
        )

    # -------------------------------------------------
    # General Fiqh:
    # preserve source-authored disagreement;
    # never auto-tarjih.
    # -------------------------------------------------

    if resolution.topic is HybridTopic.FIQH:
        return HybridAgentPlan(
            resolution=resolution,
            handoff=(HybridAgentHandoff.GOVERNED_CORE),
            capability=expected,
            publication_obligation=(HybridPublicationObligation.PRESERVE_DISAGREEMENT),
        )

    # -------------------------------------------------
    # Quran / Hadith / Tafsir:
    #
    # Handoff only.
    # Existing governed runtime retains authority.
    # -------------------------------------------------

    return HybridAgentPlan(
        resolution=resolution,
        handoff=(HybridAgentHandoff.GOVERNED_CORE),
        capability=expected,
        publication_obligation=(HybridPublicationObligation.GOVERNED_ANSWER),
    )


class HybridResolverAgent:
    """
    Basira's thin Hybrid Agent.

    The agent decides what must be resolved and which
    governed capability should receive the question.

    It deliberately has no source registry and no
    authority-selection API.
    """

    def plan(
        self,
        *,
        question: str,
        language: str | None = None,
    ) -> HybridAgentPlan:
        resolution = resolve_hybrid_query(
            question=question,
            language=language,
        )

        hints = _resolved_identity_hints(
            question=question,
            resolution=resolution,
        )

        # A known identity candidate may refine routing
        # from GENERAL into an EXISTING governed core.
        #
        # The hint remains verification-required and
        # never becomes religious evidence by itself.
        if resolution.topic is HybridTopic.GENERAL and any(
            hint.kind == "quran_reference_candidate" for hint in hints
        ):
            resolution = replace(
                resolution,
                topic=HybridTopic.QURAN,
                capability="quran",
                reasons=(
                    *resolution.reasons,
                    "quran_identity_candidate_resolved",
                    "specialized_runtime_must_verify",
                ),
            )

        plan = govern_hybrid_resolution(resolution)

        return replace(
            plan,
            identity_hints=hints,
        )
