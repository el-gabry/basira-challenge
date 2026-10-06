from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from basira.evidence.bundle import (
    EvidenceBundleBuilder,
    EvidenceRequirementState,
)
from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.models.source_manifest import (
    IntegrityStatus,
    SourceManifest,
    SourceStatus,
)
from basira.retrieval.governed_scholarly_retriever import (
    GovernedScholarlyRetriever,
)
from basira.retrieval.unified_retriever import (
    BasiraUnifiedRetriever,
)
from basira.sources.registry import (
    TrustedSourceRegistry,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)

SOURCE_ID = "surahapp-ayat-nozool"


@dataclass(frozen=True)
class _Entity:
    entity_type: str
    value: str


@dataclass(frozen=True)
class _Understanding:
    entities: tuple[_Entity, ...]


@dataclass(frozen=True)
class _Target:
    domain: EvidenceDomain


@dataclass(frozen=True)
class _Requirement:
    required: frozenset[EvidenceNeed]


@dataclass(frozen=True)
class _Plan:
    understanding: _Understanding
    targets: tuple[_Target, ...]
    context_requirement: _Requirement


class _EmptyRetriever:
    def retrieve(
        self,
        *,
        understanding: Any,
        target: Any,
        limit: int = 10,
    ) -> tuple[EvidenceNode, ...]:
        del understanding, target, limit
        return ()


def _plan() -> Any:
    return cast(
        Any,
        _Plan(
            understanding=_Understanding(
                entities=(
                    _Entity(
                        entity_type="surah_number",
                        value="2",
                    ),
                    _Entity(
                        entity_type="ayah_number",
                        value="255",
                    ),
                )
            ),
            targets=(_Target(domain=(EvidenceDomain.REVELATION_CONTEXT)),),
            context_requirement=_Requirement(
                required=frozenset(
                    {
                        EvidenceNeed.REVELATION_CONTEXT,
                    }
                )
            ),
        ),
    )


def _runtime(
    *,
    approved: bool,
) -> FailClosedSourceRuntime:
    manifest = SourceManifest(
        source_id=SOURCE_ID,
        source_name="Test revelation context",
        domain="tafsir",
        role="secondary_reference",
        status=(SourceStatus.APPROVED if approved else SourceStatus.PENDING),
        integrity_status=(
            IntegrityStatus.VERIFIED if approved else IntegrityStatus.NOT_CHECKED
        ),
    )

    return FailClosedSourceRuntime(TrustedSourceRegistry([manifest]))


def _assessment(
    *,
    approved: bool,
):
    retriever = GovernedScholarlyRetriever(
        delegate=_EmptyRetriever(),
        runtime=_runtime(approved=approved),
        source_ids=(SOURCE_ID,),
    )

    result = BasiraUnifiedRetriever(
        {
            EvidenceDomain.REVELATION_CONTEXT: retriever,
        }
    ).retrieve(_plan())

    bundle = EvidenceBundleBuilder().build(result)

    return bundle.assessment_for(EvidenceNeed.REVELATION_CONTEXT)


def test_authorized_sparse_source_is_no_attested_entry() -> None:
    assessment = _assessment(approved=True)

    assert assessment is not None

    assert assessment.state is EvidenceRequirementState.NO_ATTESTED_ENTRY


def test_denied_sparse_source_is_unavailable_domain() -> None:
    assessment = _assessment(approved=False)

    assert assessment is not None

    assert assessment.state is EvidenceRequirementState.UNAVAILABLE_DOMAIN
