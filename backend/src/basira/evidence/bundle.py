from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.evidence.models import (
    EvidenceDomain,
    EvidenceNeed,
    EvidenceNode,
)
from basira.evidence.requirements import (
    evidence_domain_for_need,
)
from basira.retrieval.unified_retriever import (
    UnifiedRetrievalResult,
)


class EvidenceConflictType(StrEnum):
    HADITH_GRADE = "hadith_grade"

    FIQH_POSITION = "fiqh_position"


@dataclass(
    frozen=True,
    slots=True,
)
class EvidenceConflict:
    conflict_type: EvidenceConflictType

    group_id: str

    evidence_ids: tuple[
        str,
        ...,
    ]


class EvidenceRequirementState(StrEnum):
    """
    Resolution state for one required evidence need.
    """

    SATISFIED = "satisfied"

    NO_ATTESTED_ENTRY = "no_attested_entry"

    MISSING_EVIDENCE = "missing_evidence"

    UNAVAILABLE_DOMAIN = "unavailable_domain"


@dataclass(
    frozen=True,
    slots=True,
)
class EvidenceRequirementAssessment:
    need: EvidenceNeed

    state: EvidenceRequirementState

    evidence_ids: tuple[
        str,
        ...,
    ] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class EvidenceBundle:
    """
    Evidence retrieved for one query together with
    explicit assessments of every required evidence
    need.

    evidence_complete:
        Every required need has positive evidence.

    resolution_complete:
        Every required need has been resolved safely.

        NO_ATTESTED_ENTRY counts as resolved, but it
        does not count as positive evidence.
    """

    evidence: tuple[
        EvidenceNode,
        ...,
    ]

    required_assessments: tuple[
        EvidenceRequirementAssessment,
        ...,
    ]

    conflicts: tuple[
        EvidenceConflict,
        ...,
    ] = ()

    @property
    def required_count(
        self,
    ) -> int:
        return len(self.required_assessments)

    @property
    def satisfied_count(
        self,
    ) -> int:
        return sum(
            assessment.state == EvidenceRequirementState.SATISFIED
            for assessment in self.required_assessments
        )

    @property
    def resolved_count(
        self,
    ) -> int:
        resolved_states = {
            EvidenceRequirementState.SATISFIED,
            EvidenceRequirementState.NO_ATTESTED_ENTRY,
        }

        return sum(
            assessment.state in resolved_states
            for assessment in self.required_assessments
        )

    @property
    def evidence_coverage(
        self,
    ) -> float:
        if self.required_count == 0:
            return 1.0

        return self.satisfied_count / self.required_count

    @property
    def resolution_coverage(
        self,
    ) -> float:
        if self.required_count == 0:
            return 1.0

        return self.resolved_count / self.required_count

    @property
    def evidence_complete(
        self,
    ) -> bool:
        return self.satisfied_count == self.required_count

    @property
    def resolution_complete(
        self,
    ) -> bool:
        return self.resolved_count == self.required_count

    def assessment_for(
        self,
        need: EvidenceNeed,
    ) -> EvidenceRequirementAssessment | None:
        for assessment in self.required_assessments:
            if assessment.need == need:
                return assessment

        return None


class EvidenceBundleBuilder:
    """
    Compare retrieved evidence with the evidence
    requirements declared before retrieval.
    """

    def build(
        self,
        result: UnifiedRetrievalResult,
    ) -> EvidenceBundle:
        assessments = tuple(
            self._assess_need(
                result=result,
                need=need,
            )
            for need in sorted(
                result.plan.context_requirement.required,
                key=lambda value: value.value,
            )
        )

        return EvidenceBundle(
            evidence=result.evidence,
            required_assessments=(assessments),
            conflicts=(self._detect_conflicts(result)),
        )

    def _assess_need(
        self,
        *,
        result: UnifiedRetrievalResult,
        need: EvidenceNeed,
    ) -> EvidenceRequirementAssessment:
        if need is EvidenceNeed.SOURCE_PROVENANCE:
            return self._assess_provenance(result)

        if need is EvidenceNeed.HADITH_TEXT:
            return self._assess_hadith_claim(
                result=result,
                need=need,
                claim_type=("hadith_text"),
            )

        if need is EvidenceNeed.HADITH_GRADE:
            return self._assess_hadith_claim(
                result=result,
                need=need,
                claim_type=("hadith_grade"),
            )

        if need is EvidenceNeed.FIQH_EVIDENCE:
            return self._assess_fiqh_claim_types(
                result=result,
                need=need,
                claim_types=(
                    "fiqh_position",
                    "fiqh_ruling",
                ),
            )

        if need is EvidenceNeed.FIQH_MADHHAB_SCOPE:
            return self._assess_fiqh_madhhab_scope(
                result=result,
                need=need,
            )

        if need is EvidenceNeed.FIQH_CONDITIONS:
            return self._assess_fiqh_claim_types(
                result=result,
                need=need,
                claim_types=(
                    "fiqh_condition",
                ),
            )

        if need is EvidenceNeed.FIQH_EXCEPTIONS:
            return self._assess_fiqh_claim_types(
                result=result,
                need=need,
                claim_types=(
                    "fiqh_exception",
                ),
            )

        if need is EvidenceNeed.FIQH_DISAGREEMENT:
            return self._assess_fiqh_disagreement(
                result=result,
                need=need,
            )

        if need is EvidenceNeed.FIQH_CONSTRAINTS:
            return self._assess_legacy_fiqh_constraints(
                result=result,
                need=need,
            )

        domain = evidence_domain_for_need(need)

        if domain is None:
            return EvidenceRequirementAssessment(
                need=need,
                state=(EvidenceRequirementState.MISSING_EVIDENCE),
            )

        if domain in result.unavailable_domains:
            return EvidenceRequirementAssessment(
                need=need,
                state=(EvidenceRequirementState.UNAVAILABLE_DOMAIN),
            )

        domain_evidence = tuple(
            node for node in result.evidence if node.domain == domain
        )

        if domain_evidence:
            return EvidenceRequirementAssessment(
                need=need,
                state=(EvidenceRequirementState.SATISFIED),
                evidence_ids=tuple(node.evidence_id for node in domain_evidence),
            )

        if (
            need is EvidenceNeed.REVELATION_CONTEXT
            and self._has_exact_quran_anchor(result)
            and self._domain_was_targeted(
                result=result,
                domain=domain,
            )
        ):
            return EvidenceRequirementAssessment(
                need=need,
                state=(EvidenceRequirementState.NO_ATTESTED_ENTRY),
            )

        return EvidenceRequirementAssessment(
            need=need,
            state=(EvidenceRequirementState.MISSING_EVIDENCE),
        )

    @staticmethod
    def _detect_conflicts(
        result: UnifiedRetrievalResult,
    ) -> tuple[
        EvidenceConflict,
        ...,
    ]:
        groups: dict[
            str,
            list[EvidenceNode],
        ] = {}

        for node in result.evidence:
            if (
                node.domain is not EvidenceDomain.HADITH
                or node.claim_type != "hadith_grade"
                or node.conflict_group is None
            ):
                continue

            groups.setdefault(
                node.conflict_group,
                [],
            ).append(node)

        conflicts: list[EvidenceConflict] = []

        for group_id, nodes in groups.items():
            categories = {
                node.topic
                for node in nodes
                if node.topic
                not in {
                    None,
                    "unknown",
                }
            }

            explicit_conflict = any(node.conflict_type is not None for node in nodes)

            distinct_grade_texts = {
                node.text.strip() for node in nodes if node.text.strip()
            }

            if len(categories) < 2 and not (
                explicit_conflict and len(distinct_grade_texts) >= 2
            ):
                continue

            conflicts.append(
                EvidenceConflict(
                    conflict_type=(EvidenceConflictType.HADITH_GRADE),
                    group_id=group_id,
                    evidence_ids=tuple(node.evidence_id for node in nodes),
                )
            )

        conflicts.extend(
            EvidenceBundleBuilder
            ._detect_fiqh_conflicts(
                result
            )
        )

        return tuple(conflicts)

    @staticmethod
    def _detect_fiqh_conflicts(
        result: UnifiedRetrievalResult,
    ) -> tuple[
        EvidenceConflict,
        ...,
    ]:
        """
        Preserve jurisprudential disagreement.

        We do NOT infer disagreement merely because two
        madhhabs are present.

        Automatic conflict detection requires:
        - same explicit issue/topic;
        - explicit fiqh_ruling nodes;
        - at least two distinct ruling texts;
        - at least two distinct madhhab attributions.

        An explicit source-derived fiqh_disagreement node
        is also sufficient to preserve a conflict.
        """

        fiqh_nodes = tuple(
            node
            for node in result.evidence
            if (
                node.domain
                is EvidenceDomain.FIQH
            )
        )

        topics = {
            node.topic
            for node in fiqh_nodes
            if node.topic
        }

        conflicts: list[
            EvidenceConflict
        ] = []

        for topic in sorted(topics):
            topic_nodes = tuple(
                node
                for node in fiqh_nodes
                if node.topic == topic
            )

            explicit = tuple(
                node
                for node in topic_nodes
                if (
                    node.claim_type
                    == "fiqh_disagreement"
                )
            )

            rulings = tuple(
                node
                for node in topic_nodes
                if (
                    node.claim_type
                    == "fiqh_ruling"
                    and node.text.strip()
                    and node.authority_scope
                    not in {
                        None,
                        "",
                        "unspecified",
                    }
                )
            )

            distinct_rulings = {
                node.text.strip()
                for node in rulings
            }

            distinct_authorities = {
                node.authority_scope
                for node in rulings
            }

            automatic_conflict = (
                len(distinct_rulings) >= 2
                and len(distinct_authorities) >= 2
            )

            if (
                not explicit
                and not automatic_conflict
            ):
                continue

            evidence_ids = tuple(
                dict.fromkeys(
                    node.evidence_id
                    for node in (
                        *rulings,
                        *explicit,
                    )
                )
            )

            conflicts.append(
                EvidenceConflict(
                    conflict_type=(
                        EvidenceConflictType
                        .FIQH_POSITION
                    ),
                    group_id=(
                        f"fiqh:{topic}"
                    ),
                    evidence_ids=evidence_ids,
                )
            )

        return tuple(
            conflicts
        )

    @staticmethod
    def _assess_fiqh_claim_types(
        *,
        result: UnifiedRetrievalResult,
        need: EvidenceNeed,
        claim_types: tuple[
            str,
            ...,
        ],
    ) -> EvidenceRequirementAssessment:
        if (
            EvidenceDomain.FIQH
            in result.unavailable_domains
        ):
            return EvidenceRequirementAssessment(
                need=need,
                state=(
                    EvidenceRequirementState
                    .UNAVAILABLE_DOMAIN
                ),
            )

        matching = tuple(
            node
            for node in result.evidence
            if (
                node.domain
                is EvidenceDomain.FIQH
                and node.claim_type
                in claim_types
            )
        )

        if matching:
            return EvidenceRequirementAssessment(
                need=need,
                state=(
                    EvidenceRequirementState
                    .SATISFIED
                ),
                evidence_ids=tuple(
                    node.evidence_id
                    for node in matching
                ),
            )

        return EvidenceRequirementAssessment(
            need=need,
            state=(
                EvidenceRequirementState
                .MISSING_EVIDENCE
            ),
        )

    @staticmethod
    def _assess_fiqh_madhhab_scope(
        *,
        result: UnifiedRetrievalResult,
        need: EvidenceNeed,
    ) -> EvidenceRequirementAssessment:
        if (
            EvidenceDomain.FIQH
            in result.unavailable_domains
        ):
            return EvidenceRequirementAssessment(
                need=need,
                state=(
                    EvidenceRequirementState
                    .UNAVAILABLE_DOMAIN
                ),
            )

        matching = tuple(
            node
            for node in result.evidence
            if (
                node.domain
                is EvidenceDomain.FIQH
                and node.claim_type
                in {
                    "fiqh_position",
                    "fiqh_ruling",
                }
                and node.authority_scope
                not in {
                    None,
                    "",
                    "unspecified",
                }
            )
        )

        if matching:
            return EvidenceRequirementAssessment(
                need=need,
                state=(
                    EvidenceRequirementState
                    .SATISFIED
                ),
                evidence_ids=tuple(
                    node.evidence_id
                    for node in matching
                ),
            )

        return EvidenceRequirementAssessment(
            need=need,
            state=(
                EvidenceRequirementState
                .MISSING_EVIDENCE
            ),
        )

    @staticmethod
    def _assess_fiqh_disagreement(
        *,
        result: UnifiedRetrievalResult,
        need: EvidenceNeed,
    ) -> EvidenceRequirementAssessment:
        if (
            EvidenceDomain.FIQH
            in result.unavailable_domains
        ):
            return EvidenceRequirementAssessment(
                need=need,
                state=(
                    EvidenceRequirementState
                    .UNAVAILABLE_DOMAIN
                ),
            )

        explicit = tuple(
            node
            for node in result.evidence
            if (
                node.domain
                is EvidenceDomain.FIQH
                and node.claim_type
                == "fiqh_disagreement"
            )
        )

        if explicit:
            return EvidenceRequirementAssessment(
                need=need,
                state=(
                    EvidenceRequirementState
                    .SATISFIED
                ),
                evidence_ids=tuple(
                    node.evidence_id
                    for node in explicit
                ),
            )

        conflicts = (
            EvidenceBundleBuilder
            ._detect_fiqh_conflicts(
                result
            )
        )

        matching_ids = tuple(
            evidence_id
            for conflict in conflicts
            for evidence_id
            in conflict.evidence_ids
        )

        if matching_ids:
            return EvidenceRequirementAssessment(
                need=need,
                state=(
                    EvidenceRequirementState
                    .SATISFIED
                ),
                evidence_ids=tuple(
                    dict.fromkeys(
                        matching_ids
                    )
                ),
            )

        return EvidenceRequirementAssessment(
            need=need,
            state=(
                EvidenceRequirementState
                .MISSING_EVIDENCE
            ),
        )

    @staticmethod
    def _assess_legacy_fiqh_constraints(
        *,
        result: UnifiedRetrievalResult,
        need: EvidenceNeed,
    ) -> EvidenceRequirementAssessment:
        """
        Backwards-compatible aggregate check.

        New routes additionally carry precise needs, so
        satisfying this legacy requirement can no longer
        substitute for madhhab scope, conditions,
        exceptions, or disagreement individually.
        """

        if (
            EvidenceDomain.FIQH
            in result.unavailable_domains
        ):
            return EvidenceRequirementAssessment(
                need=need,
                state=(
                    EvidenceRequirementState
                    .UNAVAILABLE_DOMAIN
                ),
            )

        matching = tuple(
            node
            for node in result.evidence
            if (
                node.domain
                is EvidenceDomain.FIQH
                and (
                    node.claim_type
                    in {
                        "fiqh_condition",
                        "fiqh_exception",
                        "fiqh_disagreement",
                    }
                    or (
                        node.claim_type
                        in {
                            "fiqh_position",
                            "fiqh_ruling",
                        }
                        and node.authority_scope
                        not in {
                            None,
                            "",
                            "unspecified",
                        }
                    )
                )
            )
        )

        if matching:
            return EvidenceRequirementAssessment(
                need=need,
                state=(
                    EvidenceRequirementState
                    .SATISFIED
                ),
                evidence_ids=tuple(
                    node.evidence_id
                    for node in matching
                ),
            )

        return EvidenceRequirementAssessment(
            need=need,
            state=(
                EvidenceRequirementState
                .MISSING_EVIDENCE
            ),
        )

    @staticmethod
    def _assess_hadith_claim(
        *,
        result: UnifiedRetrievalResult,
        need: EvidenceNeed,
        claim_type: str,
    ) -> EvidenceRequirementAssessment:
        if EvidenceDomain.HADITH in result.unavailable_domains:
            return EvidenceRequirementAssessment(
                need=need,
                state=(EvidenceRequirementState.UNAVAILABLE_DOMAIN),
            )

        matching = tuple(
            node
            for node in result.evidence
            if (node.domain is EvidenceDomain.HADITH and node.claim_type == claim_type)
        )

        if matching:
            return EvidenceRequirementAssessment(
                need=need,
                state=(EvidenceRequirementState.SATISFIED),
                evidence_ids=tuple(node.evidence_id for node in matching),
            )

        return EvidenceRequirementAssessment(
            need=need,
            state=(EvidenceRequirementState.MISSING_EVIDENCE),
        )

    @staticmethod
    def _assess_provenance(
        result: UnifiedRetrievalResult,
    ) -> EvidenceRequirementAssessment:
        if result.evidence and all(node.source_id for node in result.evidence):
            state = EvidenceRequirementState.SATISFIED

            ids = tuple(node.evidence_id for node in result.evidence)
        else:
            state = EvidenceRequirementState.MISSING_EVIDENCE

            ids = ()

        return EvidenceRequirementAssessment(
            need=(EvidenceNeed.SOURCE_PROVENANCE),
            state=state,
            evidence_ids=ids,
        )

    @staticmethod
    def _domain_was_targeted(
        *,
        result: UnifiedRetrievalResult,
        domain: EvidenceDomain,
    ) -> bool:
        return any(target.domain == domain for target in result.plan.targets)

    @staticmethod
    def _has_exact_quran_anchor(
        result: UnifiedRetrievalResult,
    ) -> bool:
        if any(
            target.domain is EvidenceDomain.QURAN and bool(target.references)
            for target in result.plan.targets
        ):
            return True

        entity_types = {
            entity.entity_type for entity in result.plan.understanding.entities
        }

        return "surah_number" in entity_types and "ayah_number" in entity_types
