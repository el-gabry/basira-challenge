from __future__ import annotations

from enum import StrEnum
from functools import cache

from pydantic import BaseModel

from basira.verification.quran_orthography import (
    QuranOrthographyAssessment,
    QuranOrthographyComparator,
    QuranOrthographyRelation,
    QuranSourceProfile,
)
from basira.verification.quran_orthography_rules import (
    QuranOrthographyRuleId,
)


class QuranOrthographySequenceRelation(StrEnum):
    EXACT_MATCH = "exact_match"

    ORTHOGRAPHICALLY_EQUIVALENT = (
        "orthographically_equivalent"
    )

    UNRESOLVED = "unresolved"


class QuranOrthographySegment(BaseModel):
    """
    One aligned portion of the two Quran
    representations.

    Token offsets are zero-based and end-exclusive.
    """

    left_token_start: int
    left_token_end: int

    right_token_start: int
    right_token_end: int

    assessment: QuranOrthographyAssessment

    @property
    def left_text(self) -> str:
        return self.assessment.left_text

    @property
    def right_text(self) -> str:
        return self.assessment.right_text

    @property
    def relation(
        self,
    ) -> QuranOrthographyRelation:
        return self.assessment.relation

    @property
    def rule_id(
        self,
    ) -> QuranOrthographyRuleId | None:
        return self.assessment.rule_id

    @property
    def is_resolved(self) -> bool:
        return (
            self.assessment.relation
            != QuranOrthographyRelation.UNRESOLVED
        )


class QuranOrthographySequenceAssessment(
    BaseModel
):
    """
    Segment-level result for a complete Quran
    quotation or verse.

    Important:
    If even one segment remains unresolved,
    the whole comparison remains unresolved.
    """

    left_text: str
    right_text: str

    relation: QuranOrthographySequenceRelation

    segments: tuple[
        QuranOrthographySegment,
        ...,
    ]

    is_textual_error: bool | None

    @property
    def unresolved_segments(
        self,
    ) -> tuple[
        QuranOrthographySegment,
        ...,
    ]:
        return tuple(
            segment
            for segment in self.segments
            if not segment.is_resolved
        )

    @property
    def unresolved_count(self) -> int:
        return len(
            self.unresolved_segments
        )

    @property
    def all_resolved(self) -> bool:
        return (
            self.unresolved_count
            == 0
        )

    @property
    def rule_ids(
        self,
    ) -> tuple[
        QuranOrthographyRuleId,
        ...,
    ]:
        result: list[
            QuranOrthographyRuleId
        ] = []

        for segment in self.segments:
            rule_id = segment.rule_id

            if rule_id is None:
                continue

            if rule_id in result:
                continue

            result.append(
                rule_id
            )

        return tuple(
            result
        )

    @property
    def evidence_ids(
        self,
    ) -> tuple[str, ...]:
        result: list[str] = []

        for segment in self.segments:
            for evidence_id in (
                segment
                .assessment
                .rule_evidence_ids
            ):
                if evidence_id in result:
                    continue

                result.append(
                    evidence_id
                )

        return tuple(
            result
        )

    @property
    def evidence_urls(
        self,
    ) -> tuple[str, ...]:
        result: list[str] = []

        for segment in self.segments:
            for url in (
                segment
                .assessment
                .rule_evidence_urls
            ):
                if url in result:
                    continue

                result.append(
                    url
                )

        return tuple(
            result
        )


class QuranOrthographySegmentComparator:
    """
    Align two Quran representations at segment level.

    Why this exists
    ---------------
    A single phrase may contain multiple independent
    orthographic rules.

    Example:

        Uthmani:
            يَـٰبَنِىٓ إِسْرَٰٓءِيلَ

        Imla'i:
            يا بني إسرائيل

    This includes at least two independent differences:

        يَـٰبَنِىٓ
            ↔ يا بني

        إِسْرَٰٓءِيلَ
            ↔ إسرائيل

    Treating the whole phrase as one rule would be
    unsafe.

    Safety rule
    -----------
    Every part of the text must be accounted for.

    If even one aligned segment cannot be explained
    by a known deterministic representation rule,
    the complete result remains UNRESOLVED.
    """

    def __init__(
        self,
        comparator: (
            QuranOrthographyComparator
            | None
        ) = None,
    ) -> None:
        self._comparator = (
            comparator
            or QuranOrthographyComparator()
        )

    def compare(
        self,
        *,
        left_text: str,
        right_text: str,
        left_profile: QuranSourceProfile,
        right_profile: QuranSourceProfile,
        surah_number: int | None = None,
        ayah_number: int | None = None,
    ) -> QuranOrthographySequenceAssessment:
        # First check a whole-text structural rule.
        #
        # Basmala layout is inherently structural,
        # so token-level alignment is not a better
        # representation for it.

        whole_assessment = (
            self._comparator.compare(
                left_text=left_text,
                right_text=right_text,
                left_profile=left_profile,
                right_profile=right_profile,
                surah_number=surah_number,
                ayah_number=ayah_number,
            )
        )

        if (
            whole_assessment.relation
            == QuranOrthographyRelation
            .BASMALA_LAYOUT_VARIANT
        ):
            segment = QuranOrthographySegment(
                left_token_start=0,
                left_token_end=len(
                    left_text.split()
                ),
                right_token_start=0,
                right_token_end=len(
                    right_text.split()
                ),
                assessment=whole_assessment,
            )

            return (
                QuranOrthographySequenceAssessment(
                    left_text=left_text,
                    right_text=right_text,
                    relation=(
                        QuranOrthographySequenceRelation
                        .ORTHOGRAPHICALLY_EQUIVALENT
                    ),
                    segments=(
                        segment,
                    ),
                    is_textual_error=False,
                )
            )

        left_tokens = (
            left_text.split()
        )

        right_tokens = (
            right_text.split()
        )

        segments = self._align(
            left_tokens=left_tokens,
            right_tokens=right_tokens,
            left_profile=left_profile,
            right_profile=right_profile,
            surah_number=surah_number,
            ayah_number=ayah_number,
        )

        return self._build_result(
            left_text=left_text,
            right_text=right_text,
            segments=segments,
        )

    def _align(
        self,
        *,
        left_tokens: list[str],
        right_tokens: list[str],
        left_profile: QuranSourceProfile,
        right_profile: QuranSourceProfile,
        surah_number: int | None,
        ayah_number: int | None,
    ) -> tuple[
        QuranOrthographySegment,
        ...,
    ]:
        left_count = len(
            left_tokens
        )

        right_count = len(
            right_tokens
        )

        @cache
        def solve(
            left_index: int,
            right_index: int,
        ) -> tuple[
            tuple[int, int, int, int],
            tuple[
                QuranOrthographySegment,
                ...,
            ],
        ]:
            if (
                left_index
                == left_count
                and right_index
                == right_count
            ):
                return (
                    (
                        0,
                        0,
                        0,
                        0,
                    ),
                    (),
                )

            candidates: list[
                tuple[
                    tuple[
                        int,
                        int,
                        int,
                        int,
                    ],
                    tuple[
                        QuranOrthographySegment,
                        ...,
                    ],
                ]
            ] = []

            # -------------------------------------
            # Normal alignment possibilities
            #
            # 1 ↔ 1
            # 1 ↔ 2
            # 2 ↔ 1
            #
            # We deliberately do not allow arbitrary
            # large spans.
            # -------------------------------------

            span_pairs = (
                (1, 1),
                (1, 2),
                (2, 1),
            )

            for (
                left_span,
                right_span,
            ) in span_pairs:
                new_left = (
                    left_index
                    + left_span
                )

                new_right = (
                    right_index
                    + right_span
                )

                if (
                    new_left
                    > left_count
                    or new_right
                    > right_count
                ):
                    continue

                left_piece = " ".join(
                    left_tokens[
                        left_index:
                        new_left
                    ]
                )

                right_piece = " ".join(
                    right_tokens[
                        right_index:
                        new_right
                    ]
                )

                assessment = (
                    self._comparator.compare(
                        left_text=left_piece,
                        right_text=right_piece,
                        left_profile=left_profile,
                        right_profile=right_profile,
                        surah_number=(
                            surah_number
                        ),
                        ayah_number=(
                            ayah_number
                        ),
                    )
                )

                # A merged span is permitted only
                # when the orthography engine can
                # actually explain it.
                #
                # This prevents two unrelated words
                # from being swallowed into one large
                # unresolved segment.
                if (
                    (
                        left_span > 1
                        or right_span > 1
                    )
                    and assessment.relation
                    == QuranOrthographyRelation
                    .UNRESOLVED
                ):
                    continue

                tail = solve(
                    new_left,
                    new_right,
                )

                segment = (
                    QuranOrthographySegment(
                        left_token_start=(
                            left_index
                        ),
                        left_token_end=(
                            new_left
                        ),
                        right_token_start=(
                            right_index
                        ),
                        right_token_end=(
                            new_right
                        ),
                        assessment=assessment,
                    )
                )

                local_cost = (
                    self._segment_cost(
                        segment=segment,
                        left_span=left_span,
                        right_span=right_span,
                    )
                )

                total_cost = (
                    local_cost[0]
                    + tail[0][0],
                    local_cost[1]
                    + tail[0][1],
                    local_cost[2]
                    + tail[0][2],
                    local_cost[3]
                    + tail[0][3],
                )

                candidates.append(
                    (
                        total_cost,
                        (
                            segment,
                            *tail[1],
                        ),
                    )
                )

            # -------------------------------------
            # If one side has remaining tokens and
            # no normal alignment is available,
            # preserve them as unresolved.
            #
            # Never silently discard source text.
            # -------------------------------------

            if (
                left_index
                < left_count
                and right_index
                == right_count
            ):
                left_piece = (
                    left_tokens[
                        left_index
                    ]
                )

                assessment = (
                    self._unmatched_assessment(
                        left_text=left_piece,
                        right_text="",
                        left_profile=left_profile,
                        right_profile=right_profile,
                    )
                )

                segment = (
                    QuranOrthographySegment(
                        left_token_start=(
                            left_index
                        ),
                        left_token_end=(
                            left_index + 1
                        ),
                        right_token_start=(
                            right_index
                        ),
                        right_token_end=(
                            right_index
                        ),
                        assessment=assessment,
                    )
                )

                tail = solve(
                    left_index + 1,
                    right_index,
                )

                candidates.append(
                    (
                        (
                            1
                            + tail[0][0],
                            tail[0][1],
                            1
                            + tail[0][2],
                            1
                            + tail[0][3],
                        ),
                        (
                            segment,
                            *tail[1],
                        ),
                    )
                )

            if (
                right_index
                < right_count
                and left_index
                == left_count
            ):
                right_piece = (
                    right_tokens[
                        right_index
                    ]
                )

                assessment = (
                    self._unmatched_assessment(
                        left_text="",
                        right_text=right_piece,
                        left_profile=left_profile,
                        right_profile=right_profile,
                    )
                )

                segment = (
                    QuranOrthographySegment(
                        left_token_start=(
                            left_index
                        ),
                        left_token_end=(
                            left_index
                        ),
                        right_token_start=(
                            right_index
                        ),
                        right_token_end=(
                            right_index + 1
                        ),
                        assessment=assessment,
                    )
                )

                tail = solve(
                    left_index,
                    right_index + 1,
                )

                candidates.append(
                    (
                        (
                            1
                            + tail[0][0],
                            tail[0][1],
                            1
                            + tail[0][2],
                            1
                            + tail[0][3],
                        ),
                        (
                            segment,
                            *tail[1],
                        ),
                    )
                )

            if not candidates:
                # Defensive fallback.
                #
                # In normal operation 1↔1 or one of
                # the unmatched branches above should
                # always produce a path.

                return (
                    (
                        10_000,
                        10_000,
                        10_000,
                        10_000,
                    ),
                    (),
                )

            return min(
                candidates,
                key=lambda candidate: (
                    candidate[0]
                ),
            )

        _, segments = solve(
            0,
            0,
        )

        return segments

    @staticmethod
    def _segment_cost(
        *,
        segment: QuranOrthographySegment,
        left_span: int,
        right_span: int,
    ) -> tuple[
        int,
        int,
        int,
        int,
    ]:
        """
        Cost ordering:

        1. Avoid unresolved segments.
        2. Avoid unnecessary token merging.
        3. Prefer exact matches.
        4. Prefer fewer total segments when all
           higher-priority criteria are equal.

        This makes a documented 1↔2 rasm rule beat
        an incorrect chain of unresolved 1↔1 matches.
        """

        unresolved = int(
            segment.relation
            == QuranOrthographyRelation
            .UNRESOLVED
        )

        merged_tokens = (
            max(
                left_span,
                right_span,
            )
            - 1
        )

        non_exact = int(
            segment.relation
            != QuranOrthographyRelation
            .EXACT_MATCH
        )

        return (
            unresolved,
            merged_tokens,
            non_exact,
            1,
        )

    def _unmatched_assessment(
        self,
        *,
        left_text: str,
        right_text: str,
        left_profile: QuranSourceProfile,
        right_profile: QuranSourceProfile,
    ) -> QuranOrthographyAssessment:
        """
        Create a conservative unresolved assessment
        when one source contains an unmatched token.

        We still use the existing comparator so that
        normalization remains centralized.
        """

        assessment = (
            self._comparator.compare(
                left_text=left_text,
                right_text=right_text,
                left_profile=left_profile,
                right_profile=right_profile,
            )
        )

        if (
            assessment.relation
            == QuranOrthographyRelation
            .UNRESOLVED
        ):
            return assessment

        # Empty-side comparisons should never be
        # promoted to an accepted representation
        # difference.
        return QuranOrthographyAssessment(
            relation=(
                QuranOrthographyRelation
                .UNRESOLVED
            ),
            left_text=left_text,
            right_text=right_text,
            normalized_left=(
                assessment.normalized_left
            ),
            normalized_right=(
                assessment.normalized_right
            ),
            left_script=(
                left_profile.script
            ),
            right_script=(
                right_profile.script
            ),
            is_textual_error=None,
            explanation_ar=(
                "يوجد جزء من النص في أحد "
                "المصدرين بلا مقابل مباشر "
                "في المصدر الآخر. يحتاج هذا "
                "الجزء إلى مراجعة ولا يجوز "
                "اعتباره اختلاف رسم تلقائياً."
            ),
            evidence_source_ids=(
                left_profile.source_id,
                right_profile.source_id,
            ),
        )

    @staticmethod
    def _build_result(
        *,
        left_text: str,
        right_text: str,
        segments: tuple[
            QuranOrthographySegment,
            ...,
        ],
    ) -> QuranOrthographySequenceAssessment:
        if not segments:
            return (
                QuranOrthographySequenceAssessment(
                    left_text=left_text,
                    right_text=right_text,
                    relation=(
                        QuranOrthographySequenceRelation
                        .UNRESOLVED
                    ),
                    segments=(),
                    is_textual_error=None,
                )
            )

        if any(
            not segment.is_resolved
            for segment in segments
        ):
            return (
                QuranOrthographySequenceAssessment(
                    left_text=left_text,
                    right_text=right_text,
                    relation=(
                        QuranOrthographySequenceRelation
                        .UNRESOLVED
                    ),
                    segments=segments,
                    is_textual_error=None,
                )
            )

        if all(
            segment.relation
            == QuranOrthographyRelation
            .EXACT_MATCH
            for segment in segments
        ):
            return (
                QuranOrthographySequenceAssessment(
                    left_text=left_text,
                    right_text=right_text,
                    relation=(
                        QuranOrthographySequenceRelation
                        .EXACT_MATCH
                    ),
                    segments=segments,
                    is_textual_error=False,
                )
            )

        return (
            QuranOrthographySequenceAssessment(
                left_text=left_text,
                right_text=right_text,
                relation=(
                    QuranOrthographySequenceRelation
                    .ORTHOGRAPHICALLY_EQUIVALENT
                ),
                segments=segments,
                is_textual_error=False,
            )
        )