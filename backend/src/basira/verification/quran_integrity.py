from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, Field

from basira.models.quran import QuranVerse
from basira.sources.quran.repository import QuranRepository
from basira.verification.quran_orthography import (
    QuranScriptType,
    QuranSourceProfile,
)
from basira.verification.quran_orthography_segments import (
    QuranOrthographySegmentComparator,
    QuranOrthographySequenceAssessment,
    QuranOrthographySequenceRelation,
)

EXPECTED_QURAN_REFERENCE_COUNT = 6236


class QuranIntegrityStatus(StrEnum):
    """
    Cross-source Quran integrity result for one
    Quran reference.

    EXACT_MATCH
        Both canonical Uthmani source strings are
        exactly identical.

    ORTHOGRAPHICALLY_EQUIVALENT
        Source strings differ, but every difference
        is deterministically accounted for by the
        Quran orthography layer.

    UNRESOLVED_MISMATCH
        At least one difference cannot currently be
        explained by the registered deterministic
        rules.

        This does NOT independently mean that either
        Quran source is wrong.

    REFERENCE_MISSING
        The reference exists in one corpus but not
        the other.
    """

    EXACT_MATCH = "exact_match"

    ORTHOGRAPHICALLY_EQUIVALENT = (
        "orthographically_equivalent"
    )

    UNRESOLVED_MISMATCH = (
        "unresolved_mismatch"
    )

    REFERENCE_MISSING = (
        "reference_missing"
    )


class QuranIntegrityComparison(BaseModel):
    """
    Integrity result for one Quran reference.
    """

    surah_number: int = Field(
        ge=1,
        le=114,
    )

    ayah_number: int = Field(
        ge=1,
    )

    source_a_id: str = Field(
        min_length=1,
    )

    source_b_id: str = Field(
        min_length=1,
    )

    text_a: str | None = None
    text_b: str | None = None

    status: QuranIntegrityStatus

    orthography: (
        QuranOrthographySequenceAssessment
        | None
    ) = None

    @property
    def reference(self) -> str:
        return (
            f"{self.surah_number}:"
            f"{self.ayah_number}"
        )

    @property
    def requires_review(self) -> bool:
        return self.status in {
            QuranIntegrityStatus
            .UNRESOLVED_MISMATCH,
            QuranIntegrityStatus
            .REFERENCE_MISSING,
        }

    @property
    def orthographically_accounted_for(
        self,
    ) -> bool:
        return self.status in {
            QuranIntegrityStatus.EXACT_MATCH,
            QuranIntegrityStatus
            .ORTHOGRAPHICALLY_EQUIVALENT,
        }

    @property
    def unresolved_segment_count(
        self,
    ) -> int:
        if self.orthography is None:
            return 0

        return (
            self.orthography
            .unresolved_count
        )


class QuranIntegrityReport(BaseModel):
    """
    Cross-source Quran corpus integrity report.

    Important distinction
    ---------------------
    This report verifies cross-source corpus
    agreement.

    It does NOT grant runtime approval to either
    source.

    Runtime approval belongs to Basira's source
    governance layer and SourceManifest state.
    """

    source_a_id: str = Field(
        min_length=1,
    )

    source_b_id: str = Field(
        min_length=1,
    )

    expected_reference_count: int = Field(
        default=EXPECTED_QURAN_REFERENCE_COUNT,
        ge=1,
    )

    comparisons: tuple[
        QuranIntegrityComparison,
        ...,
    ]

    @property
    def total_references(self) -> int:
        return len(
            self.comparisons
        )

    @property
    def exact_matches(self) -> int:
        return self._count(
            QuranIntegrityStatus.EXACT_MATCH
        )

    @property
    def orthographic_variants(self) -> int:
        return self._count(
            QuranIntegrityStatus
            .ORTHOGRAPHICALLY_EQUIVALENT
        )

    @property
    def orthographically_accounted_for(
        self,
    ) -> int:
        return (
            self.exact_matches
            + self.orthographic_variants
        )

    @property
    def unresolved_mismatches(self) -> int:
        return self._count(
            QuranIntegrityStatus
            .UNRESOLVED_MISMATCH
        )

    @property
    def missing_references(self) -> int:
        return self._count(
            QuranIntegrityStatus
            .REFERENCE_MISSING
        )

    @property
    def unresolved_segments(self) -> int:
        return sum(
            comparison
            .unresolved_segment_count
            for comparison
            in self.comparisons
        )

    @property
    def coverage_complete(self) -> bool:
        """
        Check expected corpus-size coverage.

        This catches the important case where BOTH
        sources omit the same reference.

        If both omit the same verse, a union of their
        references cannot reveal the missing reference,
        but expected_reference_count still can.
        """

        return (
            self.total_references
            == self.expected_reference_count
        )

    @property
    def review_required(self) -> bool:
        if not self.coverage_complete:
            return True

        return any(
            comparison.requires_review
            for comparison
            in self.comparisons
        )

    @property
    def corpus_text_agrees(self) -> bool:
        """
        True only when:

        - expected reference coverage is complete
        - no reference is missing from one source
        - no unresolved cross-source difference
          remains
        - every expected reference is either exact
          or orthographically accounted for

        This remains separate from runtime source
        approval.
        """

        return (
            self.coverage_complete
            and not self.review_required
            and (
                self.orthographically_accounted_for
                == self.expected_reference_count
            )
        )

    @property
    def cross_source_verified(self) -> bool:
        """
        Semantic alias for higher-level services.

        Meaning:

            The compared corpora agree after
            deterministic Quran orthography
            accounting.

        It does NOT mean:

            source_manifest.is_runtime_approved
        """

        return self.corpus_text_agrees

    def _count(
        self,
        status: QuranIntegrityStatus,
    ) -> int:
        return sum(
            comparison.status == status
            for comparison
            in self.comparisons
        )


class QuranCrossSourceIntegrityVerifier:
    """
    Compare two independently ingested Quran
    repositories.

    Pipeline
    --------
    1. Validate repository contents.
    2. Ensure each repository belongs to exactly
       one source.
    3. Index verses by (surah, ayah).
    4. Compare common references through the
       segment-level Quran orthography engine.
    5. Surface missing references.
    6. Preserve unresolved differences for review.
    7. Validate expected corpus coverage.

    Safety principles
    -----------------
    - no majority voting
    - no preferred-source winner
    - no silent correction
    - no automatic claim that an unresolved
      difference is a Quran textual error
    - runtime source approval remains separate
    """

    def __init__(
        self,
        *,
        orthography_comparator: (
            QuranOrthographySegmentComparator
            | None
        ) = None,
        expected_reference_count: int = (
            EXPECTED_QURAN_REFERENCE_COUNT
        ),
    ) -> None:
        if expected_reference_count < 1:
            raise ValueError(
                "Expected Quran reference count "
                "must be at least 1."
            )

        self._orthography = (
            orthography_comparator
            or QuranOrthographySegmentComparator()
        )

        self._expected_reference_count = (
            expected_reference_count
        )

    def compare(
        self,
        source_a: QuranRepository,
        source_b: QuranRepository,
    ) -> QuranIntegrityReport:
        verses_a = self._index(
            source_a
        )

        verses_b = self._index(
            source_b
        )

        source_a_id = self._source_id(
            verses_a.values()
        )

        source_b_id = self._source_id(
            verses_b.values()
        )

        source_a_profile = (
            self._profile(
                source_id=source_a_id,
            )
        )

        source_b_profile = (
            self._profile(
                source_id=source_b_id,
            )
        )

        references = sorted(
            set(verses_a)
            | set(verses_b)
        )

        comparisons = tuple(
            self._compare_reference(
                reference=reference,
                verse_a=verses_a.get(
                    reference
                ),
                verse_b=verses_b.get(
                    reference
                ),
                source_a_profile=(
                    source_a_profile
                ),
                source_b_profile=(
                    source_b_profile
                ),
            )
            for reference in references
        )

        return QuranIntegrityReport(
            source_a_id=source_a_id,
            source_b_id=source_b_id,
            expected_reference_count=(
                self._expected_reference_count
            ),
            comparisons=comparisons,
        )

    @staticmethod
    def _index(
        repository: QuranRepository,
    ) -> dict[
        tuple[int, int],
        QuranVerse,
    ]:
        verses = tuple(
            repository.all()
        )

        if not verses:
            raise ValueError(
                "Cannot compare an empty "
                "Quran corpus."
            )

        result: dict[
            tuple[int, int],
            QuranVerse,
        ] = {}

        for verse in verses:
            reference = (
                verse.surah_number,
                verse.ayah_number,
            )

            if reference in result:
                raise ValueError(
                    "Duplicate Quran reference "
                    "found during cross-source "
                    "integrity verification: "
                    f"{reference[0]}:"
                    f"{reference[1]}"
                )

            result[
                reference
            ] = verse

        return result

    @staticmethod
    def _source_id(
        verses: Iterable[
            QuranVerse
        ],
    ) -> str:
        source_ids = {
            verse.source_id
            for verse in verses
        }

        if not source_ids:
            raise ValueError(
                "Cannot determine Quran source "
                "identity from an empty corpus."
            )

        if len(source_ids) != 1:
            raise ValueError(
                "A Quran repository used for "
                "cross-source integrity "
                "comparison must contain "
                "exactly one source."
            )

        return next(
            iter(
                source_ids
            )
        )

    @staticmethod
    def _profile(
        *,
        source_id: str,
    ) -> QuranSourceProfile:
        """
        Corpus integrity compares the canonical
        Uthmani representation stored in:

            QuranVerse.text_uthmani

        Therefore both source profiles are explicitly
        UTHMANI here.

        Uthmani ↔ Imla'i verification belongs to the
        separate representation/user-input workflow.
        """

        return QuranSourceProfile(
            source_id=source_id,
            source_name=source_id,
            script=QuranScriptType.UTHMANI,
            narration="hafs",
        )

    def _compare_reference(
        self,
        *,
        reference: tuple[
            int,
            int,
        ],
        verse_a: QuranVerse | None,
        verse_b: QuranVerse | None,
        source_a_profile: QuranSourceProfile,
        source_b_profile: QuranSourceProfile,
    ) -> QuranIntegrityComparison:
        surah_number, ayah_number = (
            reference
        )

        # =================================================
        # Missing from one source
        # =================================================

        if (
            verse_a is None
            or verse_b is None
        ):
            return QuranIntegrityComparison(
                surah_number=surah_number,
                ayah_number=ayah_number,
                source_a_id=(
                    source_a_profile.source_id
                ),
                source_b_id=(
                    source_b_profile.source_id
                ),
                text_a=(
                    verse_a.text_uthmani
                    if verse_a is not None
                    else None
                ),
                text_b=(
                    verse_b.text_uthmani
                    if verse_b is not None
                    else None
                ),
                status=(
                    QuranIntegrityStatus
                    .REFERENCE_MISSING
                ),
                orthography=None,
            )

        # =================================================
        # Segment-level Uthmani comparison
        # =================================================

        orthography = (
            self._orthography.compare(
                left_text=(
                    verse_a.text_uthmani
                ),
                right_text=(
                    verse_b.text_uthmani
                ),
                left_profile=(
                    source_a_profile
                ),
                right_profile=(
                    source_b_profile
                ),
                surah_number=(
                    surah_number
                ),
                ayah_number=(
                    ayah_number
                ),
            )
        )

        status = (
            self._status_from_orthography(
                orthography
            )
        )

        return QuranIntegrityComparison(
            surah_number=surah_number,
            ayah_number=ayah_number,
            source_a_id=(
                source_a_profile.source_id
            ),
            source_b_id=(
                source_b_profile.source_id
            ),
            text_a=(
                verse_a.text_uthmani
            ),
            text_b=(
                verse_b.text_uthmani
            ),
            status=status,
            orthography=orthography,
        )

    @staticmethod
    def _status_from_orthography(
        orthography: (
            QuranOrthographySequenceAssessment
        ),
    ) -> QuranIntegrityStatus:
        if (
            orthography.relation
            == QuranOrthographySequenceRelation
            .EXACT_MATCH
        ):
            return (
                QuranIntegrityStatus
                .EXACT_MATCH
            )

        if (
            orthography.relation
            == QuranOrthographySequenceRelation
            .ORTHOGRAPHICALLY_EQUIVALENT
        ):
            return (
                QuranIntegrityStatus
                .ORTHOGRAPHICALLY_EQUIVALENT
            )

        return (
            QuranIntegrityStatus
            .UNRESOLVED_MISMATCH
        )