from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from basira.competition.official_coverage import (
    OfficialDomain,
)
from basira.evidence.models import (
    EvidenceNode,
)
from basira.retrieval.fiqh_policy_compiler import (
    FiqhRetrievalPolicyEnvelope,
)


class CompetitionRetrievalError(RuntimeError):
    pass


class CompetitionPolicyRequired(CompetitionRetrievalError):
    pass


class CompetitionSourceUnavailable(CompetitionRetrievalError):
    """
    Governed source could not be reached or
    safely interpreted.

    This is explicitly different from a valid
    retrieval returning zero results.
    """

    pass


class CompetitionAuthorityBoundaryError(CompetitionRetrievalError):
    pass


class CompetitionMaterialRole(StrEnum):
    """
    Non-primary source material.

    These lanes must never be silently promoted
    into answer-bearing EvidenceNodes.
    """

    CONVERSATIONAL = "conversational"

    TERMINOLOGY = "terminology"

    ROUTING_CONTEXT = "routing_context"


@dataclass(
    frozen=True,
    slots=True,
)
class CompetitionSourceMaterial:
    material_id: str

    source_id: str

    role: CompetitionMaterialRole

    text: str

    source_url: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class CompetitionRetrievalRequest:
    """
    Request emitted by the competition control plane.

    This deliberately carries an OfficialDomain rather
    than asking the legacy BasiraRetrievalPlanner to
    choose a domain.

    Retrieval implementations may reuse proven search
    engines, but they cannot widen source authority.
    """

    official_domain: OfficialDomain

    query: str

    limit: int = 10

    references: tuple[str, ...] = ()

    fiqh_policy: FiqhRetrievalPolicyEnvelope | None = None

    def __post_init__(
        self,
    ) -> None:
        if not self.query.strip():
            raise ValueError("Competition retrieval query must be nonblank.")

        if self.limit <= 0:
            raise ValueError("Competition retrieval limit must be positive.")


@dataclass(
    frozen=True,
    slots=True,
)
class CompetitionRetrievalResult:
    """
    Retrieval result before Agent/API integration.

    `evidence` is reserved for answer-bearing governed
    EvidenceNodes.

    `materials` contains policy-limited contextual
    material such as Bayyinat conversational framing
    or Jamhara terminology.

    Keeping these lanes separate prevents authority
    laundering.
    """

    official_domain: OfficialDomain

    evidence: tuple[
        EvidenceNode,
        ...,
    ] = ()

    materials: tuple[
        CompetitionSourceMaterial,
        ...,
    ] = ()

    unavailable: bool = False

    unavailable_reason: str | None = None


class CompetitionEvidenceAdapter(Protocol):
    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        EvidenceNode,
        ...,
    ]: ...


class CompetitionMaterialAdapter(Protocol):
    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[
        CompetitionSourceMaterial,
        ...,
    ]: ...


_MATERIAL_ONLY_DOMAINS = frozenset(
    {
        OfficialDomain.SHUBUHAT_FAQ,
        (OfficialDomain.TRANSLATION_TERMINOLOGY),
        OfficialDomain.DAWAH_GENERAL_CONTENT,
    }
)


class CompetitionRetrievalBridge:
    """
    Execution bridge between the competition control
    plane and proven retrieval engines.

    Important:
    - no BasiraRetrievalPlanner;
    - no Agent authority;
    - no source-family selection;
    - no answerability decision;
    - no fallback widening.

    Upstream competition policy decides the domain and
    source authority. This bridge only executes an
    already-authorized retrieval lane.
    """

    def __init__(
        self,
        *,
        evidence_adapters: (
            Mapping[
                OfficialDomain,
                CompetitionEvidenceAdapter,
            ]
            | None
        ) = None,
        material_adapters: (
            Mapping[
                OfficialDomain,
                CompetitionMaterialAdapter,
            ]
            | None
        ) = None,
    ) -> None:
        self._evidence_adapters = dict(evidence_adapters or {})

        self._material_adapters = dict(material_adapters or {})

        invalid = set(self._evidence_adapters) & set(_MATERIAL_ONLY_DOMAINS)

        if invalid:
            names = ", ".join(sorted(domain.value for domain in invalid))

            raise (
                CompetitionAuthorityBoundaryError(
                    "Material-only competition "
                    "domain(s) cannot be registered "
                    "as primary evidence adapters: " + names
                )
            )

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> CompetitionRetrievalResult:
        domain = request.official_domain

        if domain is OfficialDomain.GENERAL_FIQH and request.fiqh_policy is None:
            raise CompetitionPolicyRequired(
                "Fiqh retrieval requires an immutable policy envelope."
            )

        if domain in _MATERIAL_ONLY_DOMAINS:
            adapter = self._material_adapters.get(domain)

            if adapter is None:
                return CompetitionRetrievalResult(
                    official_domain=domain,
                    unavailable=True,
                    unavailable_reason=("material_adapter_unavailable"),
                )

            try:
                materials = adapter.retrieve(request)
            except CompetitionSourceUnavailable as exc:
                return CompetitionRetrievalResult(
                    official_domain=domain,
                    unavailable=True,
                    unavailable_reason=(f"source_unavailable:{exc}"),
                )

            return CompetitionRetrievalResult(
                official_domain=domain,
                materials=materials,
            )

        adapter = self._evidence_adapters.get(domain)

        if adapter is None:
            return CompetitionRetrievalResult(
                official_domain=domain,
                unavailable=True,
                unavailable_reason=("evidence_adapter_unavailable"),
            )

        try:
            evidence = adapter.retrieve(request)
        except CompetitionSourceUnavailable as exc:
            return CompetitionRetrievalResult(
                official_domain=domain,
                unavailable=True,
                unavailable_reason=(f"source_unavailable:{exc}"),
            )

        return CompetitionRetrievalResult(
            official_domain=domain,
            evidence=evidence,
        )
