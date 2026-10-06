from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceRequirementState,
)
from basira.evidence.models import (
    EvidenceNeed,
)


class RetrievalSufficiencyState(StrEnum):
    """
    Structural retrieval sufficiency.

    This deliberately does NOT mean semantic claim
    support or entailment.
    """

    SUFFICIENT = "sufficient"

    RESOLVED_ABSENCE = "resolved_absence"

    NEEDS_MORE_RETRIEVAL = "needs_more_retrieval"

    UNAVAILABLE = "unavailable"

    INVALID_EVIDENCE_LINK = "invalid_evidence_link"


@dataclass(
    frozen=True,
    slots=True,
)
class RetrievalSufficiencyAssessment:
    """
    Deterministic gate result between retrieval/evidence
    bundling and the action decision layer.

    The gate answers only:

    "Did retrieval structurally resolve the declared
    required evidence needs?"

    It does NOT answer:

    "Does this evidence semantically support a claim?"
    """

    state: RetrievalSufficiencyState

    blocking_needs: tuple[
        EvidenceNeed,
        ...,
    ] = ()

    resolved_absence_needs: tuple[
        EvidenceNeed,
        ...,
    ] = ()

    invalid_link_needs: tuple[
        EvidenceNeed,
        ...,
    ] = ()

    @property
    def allows_positive_evidence_path(
        self,
    ) -> bool:
        return self.state is RetrievalSufficiencyState.SUFFICIENT

    @property
    def requires_more_retrieval(
        self,
    ) -> bool:
        return self.state is RetrievalSufficiencyState.NEEDS_MORE_RETRIEVAL

    @property
    def is_unavailable(
        self,
    ) -> bool:
        return self.state is RetrievalSufficiencyState.UNAVAILABLE


class RetrievalSufficiencyGate:
    """
    Fail-closed structural retrieval sufficiency gate.

    It consumes the already-built EvidenceBundle.

    It deliberately does not:
    - judge semantic relevance;
    - infer claim support;
    - score religious correctness;
    - invent evidence;
    - inspect benchmark gold references.

    Semantic claim verification belongs to a later
    claim/evidence verification layer.
    """

    def assess(
        self,
        bundle: EvidenceBundle,
    ) -> RetrievalSufficiencyAssessment:
        evidence_ids = {node.evidence_id for node in bundle.evidence}

        invalid_needs: list[EvidenceNeed] = []

        unavailable_needs: list[EvidenceNeed] = []

        missing_needs: list[EvidenceNeed] = []

        absence_needs: list[EvidenceNeed] = []

        for assessment in bundle.required_assessments:
            if assessment.state is EvidenceRequirementState.SATISFIED:
                # SATISFIED must resolve to actual evidence
                # nodes in this exact bundle. A stale,
                # fabricated, or orphan evidence ID fails
                # closed before an answer decision.
                if not assessment.evidence_ids or any(
                    evidence_id not in evidence_ids
                    for evidence_id in assessment.evidence_ids
                ):
                    invalid_needs.append(assessment.need)

                continue

            if assessment.state is EvidenceRequirementState.UNAVAILABLE_DOMAIN:
                unavailable_needs.append(assessment.need)
                continue

            if assessment.state is EvidenceRequirementState.MISSING_EVIDENCE:
                missing_needs.append(assessment.need)
                continue

            if assessment.state is EvidenceRequirementState.NO_ATTESTED_ENTRY:
                absence_needs.append(assessment.need)
                continue

            # Defensive fail-closed fallback for any
            # future state that is not explicitly mapped.
            missing_needs.append(assessment.need)

        if invalid_needs:
            return RetrievalSufficiencyAssessment(
                state=(RetrievalSufficiencyState.INVALID_EVIDENCE_LINK),
                blocking_needs=tuple(invalid_needs),
                invalid_link_needs=tuple(invalid_needs),
                resolved_absence_needs=tuple(absence_needs),
            )

        if unavailable_needs:
            return RetrievalSufficiencyAssessment(
                state=(RetrievalSufficiencyState.UNAVAILABLE),
                blocking_needs=tuple(unavailable_needs),
                resolved_absence_needs=tuple(absence_needs),
            )

        if missing_needs:
            return RetrievalSufficiencyAssessment(
                state=(RetrievalSufficiencyState.NEEDS_MORE_RETRIEVAL),
                blocking_needs=tuple(missing_needs),
                resolved_absence_needs=tuple(absence_needs),
            )

        if absence_needs:
            return RetrievalSufficiencyAssessment(
                state=(RetrievalSufficiencyState.RESOLVED_ABSENCE),
                resolved_absence_needs=tuple(absence_needs),
            )

        return RetrievalSufficiencyAssessment(
            state=(RetrievalSufficiencyState.SUFFICIENT),
        )
