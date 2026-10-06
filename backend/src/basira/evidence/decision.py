from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.evidence.bundle import (
    EvidenceBundle,
    EvidenceConflictType,
    EvidenceRequirementState,
)
from basira.evidence.models import (
    EvidenceNeed,
)
from basira.evidence.sufficiency import (
    RetrievalSufficiencyAssessment,
    RetrievalSufficiencyState,
)
from basira.retrieval.query_understanding import (
    BasiraQueryUnderstanding,
    RiskTag,
)


class EvidenceDecisionAction(StrEnum):
    ANSWER = "answer"

    ANSWER_WITH_LIMITATION = "answer_with_limitation"

    RETRIEVE_MORE = "retrieve_more"

    ABSTAIN = "abstain"

    ESCALATE_TO_EXPERT = "escalate_to_expert"


class EvidenceDecisionReason(StrEnum):
    COMPLETE_EVIDENCE = "complete_evidence"

    RESOLVED_ABSENCE = "resolved_absence"

    MISSING_REQUIRED_EVIDENCE = "missing_required_evidence"

    UNAVAILABLE_REQUIRED_DOMAIN = "unavailable_required_domain"

    HIGH_RISK_QUERY = "high_risk_query"

    EVIDENCE_CONFLICT = "evidence_conflict"

    INVALID_REQUIRED_EVIDENCE_LINK = "invalid_required_evidence_link"


@dataclass(
    frozen=True,
    slots=True,
)
class EvidenceDecision:
    action: EvidenceDecisionAction

    reasons: tuple[
        EvidenceDecisionReason,
        ...,
    ]

    unresolved_needs: tuple[
        EvidenceNeed,
        ...,
    ] = ()

    risk_tags: tuple[
        RiskTag,
        ...,
    ] = ()

    @property
    def requires_expert(
        self,
    ) -> bool:
        return self.action == EvidenceDecisionAction.ESCALATE_TO_EXPERT


_HIGH_RISK_TAGS = frozenset(
    {
        RiskTag.ARMED_CONFLICT,
        RiskTag.TAKFIR,
        RiskTag.HUDUD,
        RiskTag.CRIMINAL_PUNISHMENT,
        RiskTag.SECTARIAN_CONFLICT,
        RiskTag.SELF_HARM,
        RiskTag.HARM_TO_OTHERS,
    }
)


class EvidenceDecisionPolicy:
    """
    Decide what Basira may do after evidence
    retrieval and completeness assessment.

    The policy is deterministic and fail-closed.

    High-risk cases are escalated even if retrieved
    evidence appears complete. Basira may prepare an
    evidence packet for a qualified reviewer, but it
    must not silently convert that packet into an
    autonomous high-risk ruling.
    """

    def decide(
        self,
        *,
        understanding: BasiraQueryUnderstanding,
        bundle: EvidenceBundle,
        sufficiency: (RetrievalSufficiencyAssessment | None) = None,
    ) -> EvidenceDecision:
        specific_risks = tuple(
            sorted(
                (tag for tag in understanding.risk_tags if tag in _HIGH_RISK_TAGS),
                key=lambda tag: tag.value,
            )
        )

        if specific_risks:
            return EvidenceDecision(
                action=(EvidenceDecisionAction.ESCALATE_TO_EXPERT),
                reasons=(EvidenceDecisionReason.HIGH_RISK_QUERY,),
                unresolved_needs=(self._unresolved_needs(bundle)),
                risk_tags=specific_risks,
            )

        fiqh_conflicts = tuple(
            conflict
            for conflict in bundle.conflicts
            if (
                conflict.conflict_type
                is EvidenceConflictType.FIQH_POSITION
            )
        )

        blocking_conflicts = tuple(
            conflict
            for conflict in bundle.conflicts
            if (
                conflict.conflict_type
                is not EvidenceConflictType.FIQH_POSITION
            )
        )

        # Ordinary evidence conflicts remain blocking.
        #
        # Documented Fiqh disagreement is different:
        # it is expected jurisprudential pluralism that
        # must remain attributed and visible. It may not
        # be collapsed into automated tarjih, but it also
        # must not become automatic expert escalation.
        if blocking_conflicts:
            return EvidenceDecision(
                action=(EvidenceDecisionAction.ESCALATE_TO_EXPERT),
                reasons=(EvidenceDecisionReason.EVIDENCE_CONFLICT,),
                unresolved_needs=(self._unresolved_needs(bundle)),
            )

        if sufficiency is not None:
            decision = self._decision_from_sufficiency(
                sufficiency
            )

            return self._apply_fiqh_conflict_limitation(
                decision=decision,
                has_fiqh_conflict=bool(
                    fiqh_conflicts
                ),
            )

        unavailable = self._needs_with_state(
            bundle,
            EvidenceRequirementState.UNAVAILABLE_DOMAIN,
        )

        if unavailable:
            return EvidenceDecision(
                action=(EvidenceDecisionAction.ABSTAIN),
                reasons=(EvidenceDecisionReason.UNAVAILABLE_REQUIRED_DOMAIN,),
                unresolved_needs=(unavailable),
            )

        missing = self._needs_with_state(
            bundle,
            EvidenceRequirementState.MISSING_EVIDENCE,
        )

        if missing:
            return EvidenceDecision(
                action=(EvidenceDecisionAction.RETRIEVE_MORE),
                reasons=(EvidenceDecisionReason.MISSING_REQUIRED_EVIDENCE,),
                unresolved_needs=(missing),
            )

        resolved_absence = self._needs_with_state(
            bundle,
            EvidenceRequirementState.NO_ATTESTED_ENTRY,
        )

        if resolved_absence:
            decision = EvidenceDecision(
                action=(EvidenceDecisionAction.ANSWER_WITH_LIMITATION),
                reasons=(EvidenceDecisionReason.RESOLVED_ABSENCE,),
                unresolved_needs=(resolved_absence),
            )

            return self._apply_fiqh_conflict_limitation(
                decision=decision,
                has_fiqh_conflict=bool(
                    fiqh_conflicts
                ),
            )

        decision = EvidenceDecision(
            action=(EvidenceDecisionAction.ANSWER),
            reasons=(EvidenceDecisionReason.COMPLETE_EVIDENCE,),
        )

        return self._apply_fiqh_conflict_limitation(
            decision=decision,
            has_fiqh_conflict=bool(
                fiqh_conflicts
            ),
        )

    @staticmethod
    def _decision_from_sufficiency(
        sufficiency: RetrievalSufficiencyAssessment,
    ) -> EvidenceDecision:
        if sufficiency.state is RetrievalSufficiencyState.INVALID_EVIDENCE_LINK:
            return EvidenceDecision(
                action=(EvidenceDecisionAction.ABSTAIN),
                reasons=(EvidenceDecisionReason.INVALID_REQUIRED_EVIDENCE_LINK,),
                unresolved_needs=(sufficiency.blocking_needs),
            )

        if sufficiency.state is RetrievalSufficiencyState.UNAVAILABLE:
            return EvidenceDecision(
                action=(EvidenceDecisionAction.ABSTAIN),
                reasons=(EvidenceDecisionReason.UNAVAILABLE_REQUIRED_DOMAIN,),
                unresolved_needs=(sufficiency.blocking_needs),
            )

        if sufficiency.state is RetrievalSufficiencyState.NEEDS_MORE_RETRIEVAL:
            return EvidenceDecision(
                action=(EvidenceDecisionAction.RETRIEVE_MORE),
                reasons=(EvidenceDecisionReason.MISSING_REQUIRED_EVIDENCE,),
                unresolved_needs=(sufficiency.blocking_needs),
            )

        if sufficiency.state is RetrievalSufficiencyState.RESOLVED_ABSENCE:
            return EvidenceDecision(
                action=(EvidenceDecisionAction.ANSWER_WITH_LIMITATION),
                reasons=(EvidenceDecisionReason.RESOLVED_ABSENCE,),
                unresolved_needs=(sufficiency.resolved_absence_needs),
            )

        if sufficiency.state is RetrievalSufficiencyState.SUFFICIENT:
            return EvidenceDecision(
                action=(EvidenceDecisionAction.ANSWER),
                reasons=(EvidenceDecisionReason.COMPLETE_EVIDENCE,),
            )

        raise ValueError(
            f"Unsupported retrieval sufficiency state: {sufficiency.state!r}"
        )

    @staticmethod
    def _apply_fiqh_conflict_limitation(
        *,
        decision: EvidenceDecision,
        has_fiqh_conflict: bool,
    ) -> EvidenceDecision:
        """
        Preserve documented Fiqh disagreement at the
        publication-decision boundary.

        This helper cannot upgrade a blocking decision.

        RETRIEVE_MORE, ABSTAIN, and expert escalation
        therefore remain unchanged. Only an otherwise
        answerable path becomes ANSWER_WITH_LIMITATION.
        """

        if not has_fiqh_conflict:
            return decision

        if decision.action not in {
            EvidenceDecisionAction.ANSWER,
            EvidenceDecisionAction.ANSWER_WITH_LIMITATION,
        }:
            return decision

        reasons = tuple(
            dict.fromkeys(
                (
                    *decision.reasons,
                    EvidenceDecisionReason
                    .EVIDENCE_CONFLICT,
                )
            )
        )

        return EvidenceDecision(
            action=(
                EvidenceDecisionAction
                .ANSWER_WITH_LIMITATION
            ),
            reasons=reasons,
            unresolved_needs=(
                decision.unresolved_needs
            ),
            risk_tags=decision.risk_tags,
        )

    @staticmethod
    def _needs_with_state(
        bundle: EvidenceBundle,
        state: EvidenceRequirementState,
    ) -> tuple[
        EvidenceNeed,
        ...,
    ]:
        return tuple(
            assessment.need
            for assessment in bundle.required_assessments
            if assessment.state == state
        )

    @staticmethod
    def _unresolved_needs(
        bundle: EvidenceBundle,
    ) -> tuple[
        EvidenceNeed,
        ...,
    ]:
        return tuple(
            assessment.need
            for assessment in bundle.required_assessments
            if assessment.state != EvidenceRequirementState.SATISFIED
        )
