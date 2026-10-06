from __future__ import annotations

from difflib import SequenceMatcher
from enum import StrEnum

from pydantic import BaseModel, Field

from basira.models.quran import QuranVerse
from basira.normalization.quran import normalize_quran_search_text
from basira.sources.quran.repository import QuranRepository


class QuranQuoteStatus(StrEnum):
    EXACT_MATCH = "exact_match"
    NORMALIZED_MATCH = "normalized_match"
    PARTIAL_MATCH = "partial_match"
    ALTERED_TEXT = "altered_text"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


class QuranDifferenceKind(StrEnum):
    ORTHOGRAPHIC = "orthographic"
    SUBSTITUTION = "substitution"
    INSERTION = "insertion"
    DELETION = "deletion"


class QuranDifference(BaseModel):
    """Difference between trusted Quran text and received text."""

    kind: QuranDifferenceKind

    expected: tuple[str, ...] = ()
    received: tuple[str, ...] = ()

    is_substantive: bool


class QuranCandidate(BaseModel):
    """Potential Quran verse corresponding to a user quotation."""

    surah_number: int
    ayah_number: int

    surah_name_ar: str | None = None
    surah_name_en: str | None = None

    canonical_text: str
    source_id: str

    score: float = Field(
        ge=0.0,
        le=1.0,
    )

    @property
    def reference(self) -> str:
        return (
            f"{self.surah_number}:"
            f"{self.ayah_number}"
        )


class QuranQuoteResult(BaseModel):
    """Result returned by QuranQuoteVerifier."""

    status: QuranQuoteStatus

    input_text: str
    normalized_input: str

    candidates: tuple[QuranCandidate, ...] = ()
    differences: tuple[QuranDifference, ...] = ()

    @property
    def has_substantive_difference(self) -> bool:
        return any(
            difference.is_substantive
            for difference in self.differences
        )


class QuranQuoteVerifier:
    """
    Verify Quran quotations against a local Quran repository.

    Similarity is used only to identify candidate verses.
    Source authority is handled separately by Basira's
    trusted-source layer.
    """

    MIN_ALTERATION_TOKENS = 5
    ALTERATION_THRESHOLD = 0.82
    AMBIGUITY_MARGIN = 0.015

    def __init__(
        self,
        repository: QuranRepository,
    ) -> None:
        self._repository = repository

    def verify(
        self,
        text: str,
    ) -> QuranQuoteResult:
        normalized = normalize_quran_search_text(
            text
        )

        if not normalized:
            return self._result(
                status=QuranQuoteStatus.NOT_FOUND,
                input_text=text,
                normalized_input=normalized,
            )

        verses = self._repository.all()

        # 1. Exact source search-text match.
        raw_matches = tuple(
            verse
            for verse in verses
            if text.strip()
            == verse.text_search.strip()
        )

        if len(raw_matches) == 1:
            return self._result(
                status=QuranQuoteStatus.EXACT_MATCH,
                input_text=text,
                normalized_input=normalized,
                verses=raw_matches,
            )

        # 2. Whole-verse match after harmless normalization.
        normalized_compact = self._compact(
            normalized
        )

        normalized_matches = tuple(
            verse
            for verse in verses
            if self._compact(
                verse.text_search
            )
            == normalized_compact
        )

        if len(normalized_matches) == 1:
            verse = normalized_matches[0]

            differences = self._differences(
                expected=verse.text_search,
                received=text,
            )

            return self._result(
                status=QuranQuoteStatus.NORMALIZED_MATCH,
                input_text=text,
                normalized_input=normalized,
                verses=normalized_matches,
                differences=differences,
            )

        if len(normalized_matches) > 1:
            return self._result(
                status=QuranQuoteStatus.AMBIGUOUS,
                input_text=text,
                normalized_input=normalized,
                verses=normalized_matches,
            )

        # 3. Valid partial quotation.
        partial_matches = tuple(
            verse
            for verse in verses
            if normalized_compact
            in self._compact(
                verse.text_search
            )
        )

        if len(partial_matches) == 1:
            return self._result(
                status=QuranQuoteStatus.PARTIAL_MATCH,
                input_text=text,
                normalized_input=normalized,
                verses=partial_matches,
            )

        if len(partial_matches) > 1:
            return self._result(
                status=QuranQuoteStatus.AMBIGUOUS,
                input_text=text,
                normalized_input=normalized,
                verses=partial_matches,
            )

        # Short unmatched input is not sufficient evidence
        # to classify a quotation as altered.
        if (
            len(normalized.split())
            < self.MIN_ALTERATION_TOKENS
        ):
            return self._result(
                status=QuranQuoteStatus.NOT_FOUND,
                input_text=text,
                normalized_input=normalized,
            )

        # 4. Candidate discovery for possible alteration.
        scored = sorted(
            (
                (
                    self._similarity(
                        normalized,
                        verse.text_search,
                    ),
                    verse,
                )
                for verse in verses
            ),
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_verse = scored[0]

        if (
            best_score
            < self.ALTERATION_THRESHOLD
        ):
            return self._result(
                status=QuranQuoteStatus.NOT_FOUND,
                input_text=text,
                normalized_input=normalized,
            )

        close_candidates = tuple(
            verse
            for score, verse in scored
            if (
                best_score - score
                <= self.AMBIGUITY_MARGIN
                and score
                >= self.ALTERATION_THRESHOLD
            )
        )

        if len(close_candidates) > 1:
            scores = {
                verse.reference: score
                for score, verse in scored
                if verse in close_candidates
            }

            return self._result(
                status=QuranQuoteStatus.AMBIGUOUS,
                input_text=text,
                normalized_input=normalized,
                verses=close_candidates,
                scores=scores,
            )

        differences = self._differences(
            expected=best_verse.text_search,
            received=text,
        )

        return self._result(
            status=QuranQuoteStatus.ALTERED_TEXT,
            input_text=text,
            normalized_input=normalized,
            verses=(best_verse,),
            differences=differences,
            scores={
                best_verse.reference: best_score,
            },
        )

    def _result(
        self,
        status: QuranQuoteStatus,
        input_text: str,
        normalized_input: str,
        verses: tuple[QuranVerse, ...] = (),
        differences: tuple[
            QuranDifference,
            ...,
        ] = (),
        scores: dict[str, float] | None = None,
    ) -> QuranQuoteResult:
        scores = scores or {}

        candidates = tuple(
            QuranCandidate(
                surah_number=verse.surah_number,
                ayah_number=verse.ayah_number,
                surah_name_ar=verse.surah_name_ar,
                surah_name_en=verse.surah_name_en,
                canonical_text=verse.text_search,
                source_id=verse.source_id,
                score=scores.get(
                    verse.reference,
                    1.0,
                ),
            )
            for verse in verses
        )

        return QuranQuoteResult(
            status=status,
            input_text=input_text,
            normalized_input=normalized_input,
            candidates=candidates,
            differences=differences,
        )

    @staticmethod
    def _compact(
        text: str,
    ) -> str:
        """
        Compact text for retrieval.

        This removes harmless spacing, tashkeel and supported
        orthographic representation differences.
        """

        return normalize_quran_search_text(
            text
        ).replace(" ", "")

    def _similarity(
        self,
        left: str,
        right: str,
    ) -> float:
        """Character-level similarity for candidate discovery."""

        return SequenceMatcher(
            None,
            self._compact(left),
            self._compact(right),
        ).ratio()

    @staticmethod
    def _classify_difference(
        operation: str,
        expected: tuple[str, ...],
        received: tuple[str, ...],
    ) -> QuranDifference:
        """
        Classify a difference as orthographic or substantive.

        If concatenating both sides produces the same normalized
        text, the difference is considered orthographic only.

        Example:
            ("ياايها",)
            ("يا", "ايها")

        Both become:
            ياايها
        """

        expected_compact = "".join(
            expected
        )

        received_compact = "".join(
            received
        )

        if (
            expected_compact
            == received_compact
        ):
            return QuranDifference(
                kind=(
                    QuranDifferenceKind.ORTHOGRAPHIC
                ),
                expected=expected,
                received=received,
                is_substantive=False,
            )

        if operation == "insert":
            kind = (
                QuranDifferenceKind.INSERTION
            )

        elif operation == "delete":
            kind = (
                QuranDifferenceKind.DELETION
            )

        else:
            kind = (
                QuranDifferenceKind.SUBSTITUTION
            )

        return QuranDifference(
            kind=kind,
            expected=expected,
            received=received,
            is_substantive=True,
        )

    @staticmethod
    def _differences(
        expected: str,
        received: str,
    ) -> tuple[QuranDifference, ...]:
        """
        Return word-level differences while distinguishing
        harmless orthographic variation from textual alteration.
        """

        expected_tokens = (
            normalize_quran_search_text(
                expected
            ).split()
        )

        received_tokens = (
            normalize_quran_search_text(
                received
            ).split()
        )

        matcher = SequenceMatcher(
            None,
            expected_tokens,
            received_tokens,
        )

        differences: list[
            QuranDifference
        ] = []

        for (
            operation,
            expected_start,
            expected_end,
            received_start,
            received_end,
        ) in matcher.get_opcodes():
            if operation == "equal":
                continue

            expected_part = tuple(
                expected_tokens[
                    expected_start:expected_end
                ]
            )

            received_part = tuple(
                received_tokens[
                    received_start:received_end
                ]
            )

            differences.append(
                QuranQuoteVerifier
                ._classify_difference(
                    operation=operation,
                    expected=expected_part,
                    received=received_part,
                )
            )

        return tuple(differences)