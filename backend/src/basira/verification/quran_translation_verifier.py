from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from basira.competition.quranpedia_translation_adapter import (
    QuranpediaTranslationEvidenceAdapter,
)
from basira.verification.quran_verifier import (
    QuranCandidate,
    QuranDifference,
    QuranDifferenceKind,
    QuranQuoteResult,
    QuranQuoteStatus,
)


def normalize_english_quran_translation(
    value: str,
) -> str:
    """
    Deterministic comparison normalization only.

    It does not translate, paraphrase, infer Quran text,
    or create religious evidence.
    """

    text = unicodedata.normalize(
        "NFKC",
        value,
    ).casefold()

    text = text.replace(
        "’",
        "'",
    )

    text = re.sub(
        r"[^a-z0-9']+",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


class QuranTranslationQuoteVerifier:
    """
    Verify an English Quran-meaning quotation only against
    Basira's already-admitted governed English translation.

    The source remains Quranpedia / Sahih International.
    Memory contributes ZERO religious evidence.
    """

    MIN_ALTERATION_TOKENS = 5

    # Deliberately conservative.
    ALTERATION_THRESHOLD = 0.76
    MIN_INPUT_COVERAGE = 0.70
    AMBIGUITY_MARGIN = 0.02

    def __init__(
        self,
        adapter: QuranpediaTranslationEvidenceAdapter,
    ) -> None:
        self._adapter = adapter

    def verify(
        self,
        text: str,
    ) -> QuranQuoteResult:
        normalized = (
            normalize_english_quran_translation(
                text
            )
        )

        if not normalized:
            return self._empty(
                text=text,
                normalized=normalized,
            )

        records = self._adapter.records()

        normalized_records = tuple(
            (
                surah,
                ayah,
                source_text,
                normalize_english_quran_translation(
                    source_text
                ),
            )
            for (
                surah,
                ayah,
                source_text,
            ) in records
        )

        # Exact after harmless presentation normalization.
        exact = tuple(
            record
            for record in normalized_records
            if record[3] == normalized
        )

        if len(exact) == 1:
            return self._result(
                status=(
                    QuranQuoteStatus.NORMALIZED_MATCH
                ),
                input_text=text,
                normalized_input=normalized,
                records=exact,
            )

        if len(exact) > 1:
            return self._result(
                status=(
                    QuranQuoteStatus.AMBIGUOUS
                ),
                input_text=text,
                normalized_input=normalized,
                records=exact,
            )

        # Valid partial quotation.
        partial = tuple(
            record
            for record in normalized_records
            if (
                normalized in record[3]
                or record[3] in normalized
            )
        )

        if len(partial) == 1:
            return self._result(
                status=(
                    QuranQuoteStatus.PARTIAL_MATCH
                ),
                input_text=text,
                normalized_input=normalized,
                records=partial,
            )

        if len(partial) > 1:
            return self._result(
                status=(
                    QuranQuoteStatus.AMBIGUOUS
                ),
                input_text=text,
                normalized_input=normalized,
                records=partial,
            )

        input_tokens = tuple(
            normalized.split()
        )

        if (
            len(input_tokens)
            < self.MIN_ALTERATION_TOKENS
        ):
            return self._empty(
                text=text,
                normalized=normalized,
            )

        input_token_set = set(
            input_tokens
        )

        scored: list[
            tuple[
                float,
                float,
                int,
                int,
                str,
                str,
            ]
        ] = []

        for (
            surah,
            ayah,
            source_text,
            source_normalized,
        ) in normalized_records:
            source_tokens = set(
                source_normalized.split()
            )

            if not source_tokens:
                continue

            input_coverage = (
                len(
                    input_token_set
                    & source_tokens
                )
                / len(
                    input_token_set
                )
            )

            if (
                input_coverage
                < self.MIN_INPUT_COVERAGE
            ):
                continue

            sequence_score = (
                SequenceMatcher(
                    None,
                    normalized,
                    source_normalized,
                ).ratio()
            )

            # Both signals must agree:
            # character order + input lexical coverage.
            score = (
                0.65
                * sequence_score
                + 0.35
                * input_coverage
            )

            scored.append(
                (
                    score,
                    input_coverage,
                    surah,
                    ayah,
                    source_text,
                    source_normalized,
                )
            )

        if not scored:
            return self._empty(
                text=text,
                normalized=normalized,
            )

        scored.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                item[2],
                item[3],
            )
        )

        best_score = scored[0][0]

        if (
            best_score
            < self.ALTERATION_THRESHOLD
        ):
            return self._empty(
                text=text,
                normalized=normalized,
            )

        close = tuple(
            item
            for item in scored
            if (
                best_score - item[0]
                <= self.AMBIGUITY_MARGIN
                and item[0]
                >= self.ALTERATION_THRESHOLD
            )
        )

        if len(close) > 1:
            records_for_result = tuple(
                (
                    item[2],
                    item[3],
                    item[4],
                    item[5],
                )
                for item in close
            )

            scores = {
                (
                    item[2],
                    item[3],
                ): item[0]
                for item in close
            }

            return self._result(
                status=(
                    QuranQuoteStatus.AMBIGUOUS
                ),
                input_text=text,
                normalized_input=normalized,
                records=records_for_result,
                scores=scores,
            )

        best = close[0]

        record = (
            best[2],
            best[3],
            best[4],
            best[5],
        )

        differences = (
            self._differences(
                expected=best[5],
                received=normalized,
            )
        )

        return self._result(
            status=(
                QuranQuoteStatus.ALTERED_TEXT
            ),
            input_text=text,
            normalized_input=normalized,
            records=(record,),
            differences=differences,
            scores={
                (
                    best[2],
                    best[3],
                ): best[0],
            },
        )

    def _empty(
        self,
        *,
        text: str,
        normalized: str,
    ) -> QuranQuoteResult:
        return QuranQuoteResult(
            status=QuranQuoteStatus.NOT_FOUND,
            input_text=text,
            normalized_input=normalized,
        )

    def _result(
        self,
        *,
        status: QuranQuoteStatus,
        input_text: str,
        normalized_input: str,
        records: tuple[
            tuple[
                int,
                int,
                str,
                str,
            ],
            ...,
        ],
        differences: tuple[
            QuranDifference,
            ...,
        ] = (),
        scores: dict[
            tuple[int, int],
            float,
        ]
        | None = None,
    ) -> QuranQuoteResult:
        scores = scores or {}

        candidates: list[
            QuranCandidate
        ] = []

        for (
            surah,
            ayah,
            _source_text,
            _normalized_source,
        ) in records:
            node = self._adapter.get(
                surah=surah,
                ayah=ayah,
            )

            if node is None:
                continue

            candidates.append(
                QuranCandidate(
                    surah_number=surah,
                    ayah_number=ayah,
                    canonical_text=(
                        node.text
                    ),
                    source_id=(
                        node.source_id
                    ),
                    score=scores.get(
                        (
                            surah,
                            ayah,
                        ),
                        1.0,
                    ),
                )
            )

        if not candidates:
            return self._empty(
                text=input_text,
                normalized=normalized_input,
            )

        return QuranQuoteResult(
            status=status,
            input_text=input_text,
            normalized_input=(
                normalized_input
            ),
            candidates=tuple(
                candidates
            ),
            differences=differences,
        )

    @staticmethod
    def _differences(
        *,
        expected: str,
        received: str,
    ) -> tuple[
        QuranDifference,
        ...,
    ]:
        expected_tokens = tuple(
            expected.split()
        )

        received_tokens = tuple(
            received.split()
        )

        matcher = SequenceMatcher(
            None,
            expected_tokens,
            received_tokens,
        )

        result: list[
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

            expected_part = (
                expected_tokens[
                    expected_start:
                    expected_end
                ]
            )

            received_part = (
                received_tokens[
                    received_start:
                    received_end
                ]
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

            # BASIRA_PARTIAL_QUOTE_BOUNDARY_CONTEXT
            #
            # A quotation may legitimately begin or end in the
            # middle of the governed Quran meaning.
            #
            # Missing canonical words OUTSIDE the submitted
            # fragment are context, not wording errors.
            #
            # Internal omissions remain substantive differences.
            boundary_context_omission = (
                operation == "delete"
                and not received_part
                and bool(received_tokens)
                and len(expected_part) < len(expected_tokens)
                and (
                    expected_part
                    == expected_tokens[
                        : len(expected_part)
                    ]
                    or expected_part
                    == expected_tokens[
                        -len(expected_part) :
                    ]
                )
            )

            if boundary_context_omission:
                continue

            result.append(
                QuranDifference(
                    kind=kind,
                    expected=(
                        expected_part
                    ),
                    received=(
                        received_part
                    ),
                    is_substantive=True,
                )
            )

        return tuple(
            result
        )
