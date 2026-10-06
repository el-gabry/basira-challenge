from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReligiousDiscipline(StrEnum):
    """
    Knowledge discipline.

    A discipline says WHERE relevant knowledge belongs.
    It does not say HOW a user's claim should be judged.
    """

    QURAN = "quran"
    HADITH = "hadith"
    TAFSIR = "tafsir"
    ASBAB_AL_NUZUL = "asbab_al_nuzul"

    AQIDAH = "aqidah"

    FIQH = "fiqh"
    USUL_AL_FIQH = "usul_al_fiqh"
    CONTEMPORARY_FIQH = "contemporary_fiqh"

    SIRAH = "sirah"
    MAWARITH = "mawarith"

    CROSS_DISCIPLINARY = "cross_disciplinary"


class ReasoningMode(StrEnum):
    """
    What reasoning shape the question requires.

    Important:
    a "shubha" is represented as CONTESTED_CLAIM,
    not as a religious discipline. The same reasoning
    mode may operate over Quran, Hadith, Aqidah, Fiqh,
    Sirah, or several disciplines together.
    """

    DIRECT_GROUNDING = "direct_grounding"

    # Evidence discovery for a known authority/domain
    # when the user did not identify one exact source
    # location before retrieval.
    CONCEPTUAL_GROUNDING = "conceptual_grounding"

    INTERPRETATION = "interpretation"

    AUTHENTICITY = "authenticity"

    COMPARATIVE = "comparative"

    LEGAL_RULING = "legal_ruling"

    CONTEMPORARY_APPLICATION = "contemporary_application"

    CONTESTED_CLAIM = "contested_claim"

    DETERMINISTIC_CALCULATION = "deterministic_calculation"


class EvidenceObligation(StrEnum):
    """
    Evidence or context that the reasoning layer says
    must be available before a safe answer is possible.

    These are reasoning-layer obligations. They do not
    replace the existing Basira EvidenceNeed model.
    A later adapter will map obligations into retrieval
    requirements.
    """

    EXACT_CANONICAL_TEXT = "exact_canonical_text"

    SOURCE_ATTRIBUTION = "source_attribution"

    HADITH_TEXT = "hadith_text"

    HADITH_GRADING = "hadith_grading"

    TAFSIR_CONTEXT = "tafsir_context"

    REVELATION_CONTEXT = "revelation_context"

    CLASSICAL_FIQH_POSITION = "classical_fiqh_position"

    MADHHAB_SCOPE = "madhhab_scope"

    USUL_PRINCIPLE = "usul_principle"

    LEGAL_RATIONALE = "legal_rationale"

    CONDITIONS = "conditions"

    EXCEPTIONS = "exceptions"

    CONTEMPORARY_GUIDANCE = "contemporary_guidance"

    CONTEMPORARY_FACTS = "contemporary_facts"

    TEMPORAL_CONTEXT = "temporal_context"

    JURISDICTION_CONTEXT = "jurisdiction_context"

    INSTITUTION_ATTRIBUTION = "institution_attribution"

    DOCUMENTED_DISAGREEMENT = "documented_disagreement"


class AnswerConstraint(StrEnum):
    """
    Behaviour that composition must preserve.

    These are constraints, not truth judgments.
    """

    PRESERVE_DISAGREEMENT = "preserve_disagreement"

    DO_NOT_CLAIM_CONSENSUS = "do_not_claim_consensus_without_evidence"

    DO_NOT_COLLAPSE_MADHHABS = "do_not_collapse_madhhabs"

    ATTRIBUTE_OPINIONS = "attribute_opinions"

    PRESERVE_CONDITIONS = "preserve_conditions"

    PRESERVE_EXCEPTIONS = "preserve_exceptions"

    DO_NOT_ACCEPT_PREMISE_AS_FACT = "do_not_accept_premise_as_fact"

    REQUIRE_CONTEXT_BEFORE_CONCLUSION = "require_context_before_conclusion"

    REQUIRE_EXPERT_REVIEW = "require_expert_review"


@dataclass(
    frozen=True,
    slots=True,
)
class ReligiousReasoningFrame:
    """
    Query-level reasoning contract.

    This frame records:
    - the primary knowledge discipline;
    - optional supporting disciplines;
    - the reasoning mode;
    - evidence/context obligations;
    - answer constraints.

    It does not perform retrieval and does not make
    semantic or religious truth judgments.
    """

    frame_id: str

    question: str

    primary_discipline: ReligiousDiscipline

    reasoning_mode: ReasoningMode

    secondary_disciplines: tuple[
        ReligiousDiscipline,
        ...,
    ] = ()

    obligations: tuple[
        EvidenceObligation,
        ...,
    ] = ()

    constraints: tuple[
        AnswerConstraint,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not self.frame_id.strip():
            raise ValueError("frame_id must not be blank")

        if not self.question.strip():
            raise ValueError("question must not be blank")

        if self.primary_discipline in self.secondary_disciplines:
            raise ValueError("primary discipline must not also be secondary")

        if len(set(self.secondary_disciplines)) != len(self.secondary_disciplines):
            raise ValueError("secondary disciplines must be unique")

        if len(set(self.obligations)) != len(self.obligations):
            raise ValueError("evidence obligations must be unique")

        if len(set(self.constraints)) != len(self.constraints):
            raise ValueError("answer constraints must be unique")


@dataclass(
    frozen=True,
    slots=True,
)
class ClassicalFiqhIssue:
    """
    Structural representation of a classical fiqh
    question.

    No field identifies a winning madhhab or ruling.
    """

    issue_id: str

    issue_text: str

    requested_madhhabs: tuple[
        str,
        ...,
    ] = ()

    compare_positions: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not self.issue_id.strip():
            raise ValueError("issue_id must not be blank")

        if not self.issue_text.strip():
            raise ValueError("issue_text must not be blank")


@dataclass(
    frozen=True,
    slots=True,
)
class ContemporaryFiqhContext:
    """
    Facts that may affect applicability of a modern
    ruling.

    These facts are kept separate from the ruling
    itself.
    """

    issue_id: str

    facts: tuple[
        str,
        ...,
    ]

    as_of_date: str | None = None

    jurisdiction: str | None = None

    institution: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not self.issue_id.strip():
            raise ValueError("issue_id must not be blank")

        if not self.facts:
            raise ValueError("contemporary fiqh context requires explicit facts")

        if any(not fact.strip() for fact in self.facts):
            raise ValueError("facts must not contain blank values")


@dataclass(
    frozen=True,
    slots=True,
)
class ContestedClaim:
    """
    A claim under examination.

    This is how Basira represents a shubha-like
    question without treating "shubha" as a separate
    source discipline.

    The presence of a contested claim never implies
    that the claim is false.
    """

    claim_id: str

    text: str

    attribution: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not self.claim_id.strip():
            raise ValueError("claim_id must not be blank")

        if not self.text.strip():
            raise ValueError("claim text must not be blank")


def classical_fiqh_comparison_frame(
    *,
    frame_id: str,
    question: str,
) -> ReligiousReasoningFrame:
    return ReligiousReasoningFrame(
        frame_id=frame_id,
        question=question,
        primary_discipline=(ReligiousDiscipline.FIQH),
        secondary_disciplines=(ReligiousDiscipline.USUL_AL_FIQH,),
        reasoning_mode=(ReasoningMode.COMPARATIVE),
        obligations=(
            EvidenceObligation.CLASSICAL_FIQH_POSITION,
            EvidenceObligation.MADHHAB_SCOPE,
            EvidenceObligation.CONDITIONS,
            EvidenceObligation.EXCEPTIONS,
            EvidenceObligation.DOCUMENTED_DISAGREEMENT,
        ),
        constraints=(
            AnswerConstraint.PRESERVE_DISAGREEMENT,
            AnswerConstraint.DO_NOT_CLAIM_CONSENSUS,
            AnswerConstraint.DO_NOT_COLLAPSE_MADHHABS,
            AnswerConstraint.PRESERVE_CONDITIONS,
            AnswerConstraint.PRESERVE_EXCEPTIONS,
        ),
    )


def contemporary_fiqh_frame(
    *,
    frame_id: str,
    question: str,
) -> ReligiousReasoningFrame:
    return ReligiousReasoningFrame(
        frame_id=frame_id,
        question=question,
        primary_discipline=(ReligiousDiscipline.CONTEMPORARY_FIQH),
        secondary_disciplines=(
            ReligiousDiscipline.FIQH,
            ReligiousDiscipline.USUL_AL_FIQH,
        ),
        reasoning_mode=(ReasoningMode.CONTEMPORARY_APPLICATION),
        obligations=(
            EvidenceObligation.CONTEMPORARY_GUIDANCE,
            EvidenceObligation.CONTEMPORARY_FACTS,
            EvidenceObligation.CLASSICAL_FIQH_POSITION,
            EvidenceObligation.USUL_PRINCIPLE,
            EvidenceObligation.CONDITIONS,
            EvidenceObligation.EXCEPTIONS,
            EvidenceObligation.TEMPORAL_CONTEXT,
            EvidenceObligation.JURISDICTION_CONTEXT,
            EvidenceObligation.INSTITUTION_ATTRIBUTION,
        ),
        constraints=(
            AnswerConstraint.ATTRIBUTE_OPINIONS,
            AnswerConstraint.PRESERVE_DISAGREEMENT,
            AnswerConstraint.PRESERVE_CONDITIONS,
            AnswerConstraint.PRESERVE_EXCEPTIONS,
        ),
    )


def contested_claim_frame(
    *,
    frame_id: str,
    question: str,
    primary_discipline: ReligiousDiscipline,
    secondary_disciplines: tuple[
        ReligiousDiscipline,
        ...,
    ] = (),
) -> ReligiousReasoningFrame:
    return ReligiousReasoningFrame(
        frame_id=frame_id,
        question=question,
        primary_discipline=(primary_discipline),
        secondary_disciplines=(secondary_disciplines),
        reasoning_mode=(ReasoningMode.CONTESTED_CLAIM),
        obligations=(EvidenceObligation.SOURCE_ATTRIBUTION,),
        constraints=(
            AnswerConstraint.DO_NOT_ACCEPT_PREMISE_AS_FACT,
            AnswerConstraint.REQUIRE_CONTEXT_BEFORE_CONCLUSION,
        ),
    )
