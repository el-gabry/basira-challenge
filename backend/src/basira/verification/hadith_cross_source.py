from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from basira.models.hadith import (
    HadithGradeCategory,
    HadithRecord,
)


class HadithCoverageRelation(StrEnum):
    SHARED = "shared"
    PRIMARY_ONLY = "primary_only"
    SECONDARY_ONLY = "secondary_only"


class HadithTextRelation(StrEnum):
    EXACT = "exact"
    DIACRITIC_VARIANT = "diacritic_variant"
    TEXT_VARIANT = "text_variant"
    NOT_COMPARABLE = "not_comparable"


class HadithGradeRelation(StrEnum):
    MATCH = "match"
    CONFLICT = "conflict"
    INSUFFICIENT = "insufficient"


@dataclass(
    frozen=True,
    slots=True,
)
class HadithCrossSourceVerification:
    reference_key: str

    primary_source_id: str
    secondary_source_id: str

    coverage_relation: HadithCoverageRelation

    text_relation: HadithTextRelation

    grade_relation: HadithGradeRelation

    review_required: bool


def _is_arabic_combining_mark(
    character: str,
) -> bool:
    return (
        unicodedata.category(character) == "Mn"
        and "ARABIC" in unicodedata.name(
            character,
            "",
        )
    )


def _without_arabic_diacritics(
    value: str,
) -> str:
    return "".join(
        character
        for character in value
        if not _is_arabic_combining_mark(
            character
        )
    )


def _reference_key(
    record: HadithRecord,
) -> str:
    reference = (
        record.primary_reference
    )

    return (
        f"{reference.collection_id}:"
        f"{reference.hadith_number}"
    )


def _text_relation(
    primary: HadithRecord,
    secondary: HadithRecord,
) -> HadithTextRelation:
    primary_text = (
        primary.text_variants[0]
        .arabic_text
    )

    secondary_text = (
        secondary.text_variants[0]
        .arabic_text
    )

    if primary_text == secondary_text:
        return HadithTextRelation.EXACT

    if (
        _without_arabic_diacritics(
            primary_text
        )
        == _without_arabic_diacritics(
            secondary_text
        )
    ):
        return (
            HadithTextRelation
            .DIACRITIC_VARIANT
        )

    return HadithTextRelation.TEXT_VARIANT


def _grade_texts(
    record: HadithRecord,
) -> frozenset[str]:
    return frozenset(
        assessment.grade_text.strip()
        for assessment
        in record.grade_assessments
        if assessment.grade_text.strip()
    )


def _known_grade_categories(
    record: HadithRecord,
) -> frozenset[
    HadithGradeCategory
]:
    return frozenset(
        assessment.category
        for assessment
        in record.grade_assessments
        if assessment.category
        not in {
            HadithGradeCategory.UNKNOWN,
        }
    )


def _grade_relation(
    primary: HadithRecord,
    secondary: HadithRecord,
) -> HadithGradeRelation:
    if (
        not primary.grade_assessments
        or not secondary.grade_assessments
    ):
        return (
            HadithGradeRelation
            .INSUFFICIENT
        )

    primary_texts = _grade_texts(
        primary
    )

    secondary_texts = _grade_texts(
        secondary
    )

    # Exact attributed wording is the strongest
    # straightforward agreement signal.
    if (
        primary_texts
        and primary_texts
        == secondary_texts
    ):
        return HadithGradeRelation.MATCH

    primary_categories = (
        _known_grade_categories(
            primary
        )
    )

    secondary_categories = (
        _known_grade_categories(
            secondary
        )
    )

    if (
        primary_categories
        and secondary_categories
    ):
        if (
            primary_categories
            == secondary_categories
        ):
            return (
                HadithGradeRelation.MATCH
            )

        return (
            HadithGradeRelation.CONFLICT
        )

    # Unknown or complex scholarly wording should
    # not be promoted into a false contradiction.
    return HadithGradeRelation.INSUFFICIENT


class HadithCrossSourceVerifier:
    """
    Compare two independently-provenanced Hadith
    observations without collapsing their provenance.

    The verifier does not decide religious truth.
    It reports agreement, variants, conflicts, and
    incomplete cross-source coverage.
    """

    def __init__(
        self,
        *,
        primary_source_id: str,
        secondary_source_id: str,
    ) -> None:
        self.primary_source_id = (
            primary_source_id
        )

        self.secondary_source_id = (
            secondary_source_id
        )

    def verify(
        self,
        *,
        primary: HadithRecord | None,
        secondary: HadithRecord | None,
    ) -> HadithCrossSourceVerification:
        if (
            primary is None
            and secondary is None
        ):
            raise ValueError(
                "At least one Hadith record "
                "must be supplied."
            )

        if primary is None:
            assert secondary is not None

            return (
                HadithCrossSourceVerification(
                    reference_key=(
                        _reference_key(
                            secondary
                        )
                    ),
                    primary_source_id=(
                        self.primary_source_id
                    ),
                    secondary_source_id=(
                        self.secondary_source_id
                    ),
                    coverage_relation=(
                        HadithCoverageRelation
                        .SECONDARY_ONLY
                    ),
                    text_relation=(
                        HadithTextRelation
                        .NOT_COMPARABLE
                    ),
                    grade_relation=(
                        HadithGradeRelation
                        .INSUFFICIENT
                    ),
                    review_required=True,
                )
            )

        if secondary is None:
            return (
                HadithCrossSourceVerification(
                    reference_key=(
                        _reference_key(
                            primary
                        )
                    ),
                    primary_source_id=(
                        self.primary_source_id
                    ),
                    secondary_source_id=(
                        self.secondary_source_id
                    ),
                    coverage_relation=(
                        HadithCoverageRelation
                        .PRIMARY_ONLY
                    ),
                    text_relation=(
                        HadithTextRelation
                        .NOT_COMPARABLE
                    ),
                    grade_relation=(
                        HadithGradeRelation
                        .INSUFFICIENT
                    ),
                    review_required=True,
                )
            )

        primary_key = _reference_key(
            primary
        )

        secondary_key = _reference_key(
            secondary
        )

        if primary_key != secondary_key:
            raise ValueError(
                "Cannot compare different Hadith "
                "references: "
                f"{primary_key!r} != "
                f"{secondary_key!r}."
            )

        text_relation = _text_relation(
            primary,
            secondary,
        )

        grade_relation = _grade_relation(
            primary,
            secondary,
        )

        review_required = (
            text_relation
            is HadithTextRelation.TEXT_VARIANT
            or grade_relation
            in {
                HadithGradeRelation.CONFLICT,
                HadithGradeRelation.INSUFFICIENT,
            }
        )

        return HadithCrossSourceVerification(
            reference_key=primary_key,
            primary_source_id=(
                self.primary_source_id
            ),
            secondary_source_id=(
                self.secondary_source_id
            ),
            coverage_relation=(
                HadithCoverageRelation.SHARED
            ),
            text_relation=text_relation,
            grade_relation=grade_relation,
            review_required=review_required,
        )
