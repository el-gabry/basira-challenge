from __future__ import annotations

from basira.evidence.models import (
    EvidenceDomain,
)
from basira.evidence.requirements import (
    evidence_domains_for_needs,
)
from basira.orchestration.contracts import (
    ClaimTask,
)
from basira.orchestration.evidence_acceptance import (
    AnchorStrength,
    EvidenceAnchor,
    RetrievalShape,
    TaskEvidenceAcceptanceContract,
)
from basira.orchestration.quran_anchor_resolution import (
    AnchorResolutionDisposition,
    QuranAnchorResolution,
)
from basira.reasoning.contracts import (
    ReasoningMode,
)
from basira.reasoning.routing import (
    evidence_domains_for_discipline,
    evidence_domains_for_frame,
)

_QURAN_STRUCTURAL_DOMAINS = frozenset(
    {
        EvidenceDomain.QURAN,
        EvidenceDomain.TAFSIR,
        EvidenceDomain.REVELATION_CONTEXT,
    }
)


class EvidenceContractCompilationError(RuntimeError):
    pass


class UnresolvedEvidenceIdentityError(EvidenceContractCompilationError):
    pass


def _required_domains(
    task: ClaimTask,
    *,
    allowed_domains: frozenset[EvidenceDomain],
) -> frozenset[EvidenceDomain]:
    """
    Required domains are NOT simply every secondary
    discipline.

    They come from:
    1. the claim's primary discipline;
    2. concrete required EvidenceNeed values.

    Secondary disciplines remain allowed and become
    required only when the evidence contract actually
    requires them.
    """

    primary = frozenset(evidence_domains_for_discipline(task.frame.primary_discipline))

    need_domains = evidence_domains_for_needs(task.context_requirement.required)

    required = primary | need_domains

    unexpected = required - allowed_domains

    if unexpected:
        raise (
            EvidenceContractCompilationError(
                "Claim evidence requirements "
                "request domains outside the "
                "reasoning frame: "
                + ", ".join(sorted(domain.value for domain in unexpected))
            )
        )

    if not required:
        raise (
            EvidenceContractCompilationError(
                "Claim produced no required evidence domains."
            )
        )

    return required


def _quran_anchors(
    *,
    resolution: (QuranAnchorResolution | None),
    allowed_domains: frozenset[EvidenceDomain],
) -> tuple[
    EvidenceAnchor,
    ...,
]:
    relevant_domains = allowed_domains & _QURAN_STRUCTURAL_DOMAINS

    if not relevant_domains:
        # A Quran identity in the overall question must
        # not accidentally constrain an independent
        # Fiqh/Hadith/etc claim.
        return ()

    if resolution is None:
        return ()

    if resolution.disposition in {
        AnchorResolutionDisposition.ASK_USER,
        AnchorResolutionDisposition.BOUNDED_BRANCH,
    }:
        raise (
            UnresolvedEvidenceIdentityError(
                "Quran identity is unresolved "
                "for a Quran-linked claim: "
                f"{resolution.reason}"
            )
        )

    if resolution.disposition is AnchorResolutionDisposition.NO_ANCHOR:
        return ()

    if resolution.disposition is not AnchorResolutionDisposition.RESOLVED:
        raise (
            EvidenceContractCompilationError(
                "Unsupported Quran anchor "
                "resolution state: "
                f"{resolution.disposition.value}"
            )
        )

    anchors = []

    for verified in resolution.anchors:
        anchors.append(
            EvidenceAnchor(
                reference=(verified.reference),
                domains=(relevant_domains),
                kind=verified.kind,
                origin=verified.origin,
                strength=(AnchorStrength.HARD),
            )
        )

    return tuple(anchors)


def _retrieval_shape(
    task: ClaimTask,
    *,
    anchors: tuple[
        EvidenceAnchor,
        ...,
    ],
    allowed_domains: frozenset[EvidenceDomain],
) -> RetrievalShape:
    if anchors:
        if task.frame.reasoning_mode in {
            ReasoningMode.DIRECT_GROUNDING,
            ReasoningMode.CONCEPTUAL_GROUNDING,
        }:
            return RetrievalShape.EXACT_ANCHOR

        return RetrievalShape.HYBRID

    if (
        task.frame.reasoning_mode
        is ReasoningMode.DIRECT_GROUNDING
        and (
            allowed_domains
            & _QURAN_STRUCTURAL_DOMAINS
        )
    ):
        raise (
            UnresolvedEvidenceIdentityError(
                "Direct Quran grounding requires "
                "a verified canonical anchor."
            )
        )

    # Conceptual grounding discovers canonical evidence
    # without pretending that discovered evidence was
    # already a HARD task anchor.
    return RetrievalShape.CONCEPTUAL


class TaskEvidenceContractCompiler:
    """
    Compile a semantic ClaimTask + independently
    verified identity context into the structural
    evidence acceptance contract.

    This compiler does not:
    - create or modify ClaimTask;
    - perform retrieval;
    - grant source authority;
    - decide semantic support;
    - decide answerability.
    """

    def compile(
        self,
        *,
        task: ClaimTask,
        quran_resolution: (QuranAnchorResolution | None) = None,
    ) -> TaskEvidenceAcceptanceContract:
        allowed = frozenset(evidence_domains_for_frame(task.frame))

        if not allowed:
            raise (
                EvidenceContractCompilationError(
                    "Reasoning frame produced no allowed evidence domains."
                )
            )

        required = _required_domains(
            task,
            allowed_domains=allowed,
        )

        anchors = _quran_anchors(
            resolution=quran_resolution,
            allowed_domains=allowed,
        )

        shape = _retrieval_shape(
            task,
            anchors=anchors,
            allowed_domains=allowed,
        )

        return TaskEvidenceAcceptanceContract(
            task_id=task.task_id,
            retrieval_shape=shape,
            allowed_domains=allowed,
            required_domains=required,
            anchors=anchors,
            require_provenance=True,
        )
