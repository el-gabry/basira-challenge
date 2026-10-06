from __future__ import annotations

import math
import re
from collections import Counter, defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass

from basira.models.scholarly import ScholarlyPassage
from basira.retrieval.arabic_query import (
    normalize_arabic_search_text,
)

_TOKEN_RE = re.compile(
    r"[a-z0-9]+|[\u0621-\u064a]+"
)

_STOPWORDS = frozenset(
    {
        # Arabic query scaffolding / function words
        "ما",
        "ماذا",
        "هل",
        "في",
        "من",
        "عن",
        "على",
        "الى",
        "إلى",
        "هو",
        "هي",
        "هذا",
        "هذه",
        "لماذا",
        "كيف",
        "معنى",
        "معني",
        "شرح",
        "تفسير",
        "يقول",
        "قال",
        "الاسلام",
        "الإسلام",
        # English query scaffolding / function words
        "what",
        "why",
        "how",
        "does",
        "do",
        "is",
        "are",
        "the",
        "a",
        "an",
        "in",
        "of",
        "about",
        "say",
        "says",
        "teach",
        "teaches",
        "meaning",
        "explain",
        "islam",
        "islamic",
    }
)


def _tokens(
    value: str,
) -> tuple[str, ...]:
    normalized = (
        normalize_arabic_search_text(
            value
        )
        .casefold()
    )

    return tuple(
        token
        for token in _TOKEN_RE.findall(
            normalized
        )
        if len(token) > 1
        and token not in _STOPWORDS
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ScholarlyLexicalHit:
    passage: ScholarlyPassage
    score: float


class ScholarlyLexicalIndex:
    """
    Deterministic BM25-style lexical index.

    Long scholarly passages are split into deterministic
    token windows for ranking only. Search results collapse
    matching child windows back to their original parent
    ScholarlyPassage before source balancing.

    Child windows are retrieval artifacts only: they never
    become evidence, never rewrite source text, and never
    replace parent provenance.

    This remains a lexical baseline only. It performs no
    embedding or semantic inference.
    """

    def __init__(
        self,
        passages: Iterable[
            ScholarlyPassage
        ],
        *,
        k1: float = 1.5,
        b: float = 0.75,
        child_chunk_size: int = 192,
        child_chunk_overlap: int = 32,
    ) -> None:
        if k1 <= 0:
            raise ValueError(
                "k1 must be greater than zero."
            )

        if not 0 <= b <= 1:
            raise ValueError(
                "b must be between zero and one."
            )

        if child_chunk_size <= 0:
            raise ValueError(
                "child_chunk_size must be greater than zero."
            )

        if child_chunk_overlap < 0:
            raise ValueError(
                "child_chunk_overlap cannot be negative."
            )

        if (
            child_chunk_overlap
            >= child_chunk_size
        ):
            raise ValueError(
                "child_chunk_overlap must be smaller "
                "than child_chunk_size."
            )

        self.k1 = k1
        self.b = b
        self.child_chunk_size = (
            child_chunk_size
        )
        self.child_chunk_overlap = (
            child_chunk_overlap
        )

        stored_passages: list[
            ScholarlyPassage
        ] = []

        document_parent_indexes: list[
            int
        ] = []

        document_lengths: list[int] = []

        postings: dict[
            str,
            list[
                tuple[int, int]
            ],
        ] = defaultdict(list)

        total_length = 0

        stride = (
            child_chunk_size
            - child_chunk_overlap
        )

        for passage in passages:
            tokens = _tokens(
                passage.text
            )

            if not tokens:
                continue

            parent_index = len(
                stored_passages
            )

            stored_passages.append(
                passage
            )

            start = 0

            while start < len(tokens):
                child_tokens = tokens[
                    start:
                    start + child_chunk_size
                ]

                document_index = len(
                    document_lengths
                )

                document_parent_indexes.append(
                    parent_index
                )

                document_length = len(
                    child_tokens
                )

                document_lengths.append(
                    document_length
                )

                total_length += (
                    document_length
                )

                frequencies = Counter(
                    child_tokens
                )

                for (
                    term,
                    frequency,
                ) in frequencies.items():
                    postings[term].append(
                        (
                            document_index,
                            frequency,
                        )
                    )

                if (
                    start
                    + child_chunk_size
                    >= len(tokens)
                ):
                    break

                start += stride

        self._passages = tuple(
            stored_passages
        )

        self._document_parent_indexes = (
            tuple(
                document_parent_indexes
            )
        )

        self._document_lengths = tuple(
            document_lengths
        )

        self._postings = {
            term: tuple(values)
            for term, values
            in postings.items()
        }

        if self._document_lengths:
            self._average_length = (
                total_length
                / len(
                    self._document_lengths
                )
            )
        else:
            self._average_length = 0.0

    def __len__(
        self,
    ) -> int:
        """
        Return the number of indexed parent passages.

        Child windows are intentionally hidden from the
        public corpus-facing size of the index.
        """

        return len(
            self._passages
        )

    @property
    def child_document_count(
        self,
    ) -> int:
        """
        Return the number of retrieval-only child windows.
        """

        return len(
            self._document_lengths
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> tuple[
        ScholarlyLexicalHit,
        ...,
    ]:
        if limit <= 0:
            return ()

        query_terms = tuple(
            dict.fromkeys(
                _tokens(query)
            )
        )

        if (
            not query_terms
            or not self._document_lengths
        ):
            return ()

        document_count = len(
            self._document_lengths
        )

        scores: dict[
            int,
            float,
        ] = defaultdict(float)

        for term in query_terms:
            term_postings = (
                self._postings.get(
                    term
                )
            )

            if not term_postings:
                continue

            document_frequency = len(
                term_postings
            )

            inverse_document_frequency = (
                math.log(
                    1.0
                    + (
                        document_count
                        - document_frequency
                        + 0.5
                    )
                    / (
                        document_frequency
                        + 0.5
                    )
                )
            )

            for (
                document_index,
                frequency,
            ) in term_postings:
                document_length = (
                    self
                    ._document_lengths[
                        document_index
                    ]
                )

                length_ratio = (
                    document_length
                    / self._average_length
                )

                denominator = (
                    frequency
                    + self.k1
                    * (
                        1.0
                        - self.b
                        + self.b
                        * length_ratio
                    )
                )

                scores[
                    document_index
                ] += (
                    inverse_document_frequency
                    * frequency
                    * (
                        self.k1
                        + 1.0
                    )
                    / denominator
                )

        parent_scores: dict[
            int,
            float,
        ] = {}

        for (
            document_index,
            score,
        ) in scores.items():
            if score <= 0:
                continue

            parent_index = (
                self
                ._document_parent_indexes[
                    document_index
                ]
            )

            current_score = (
                parent_scores.get(
                    parent_index
                )
            )

            if (
                current_score is None
                or score > current_score
            ):
                parent_scores[
                    parent_index
                ] = score

        hits = [
            ScholarlyLexicalHit(
                passage=(
                    self._passages[
                        parent_index
                    ]
                ),
                score=score,
            )
            for parent_index, score
            in parent_scores.items()
        ]

        hits.sort(
            key=lambda hit: (
                -hit.score,
                hit.passage.source_id,
                hit.passage.passage_id,
            )
        )

        return self._source_balanced(
            hits,
            limit=limit,
        )

    @staticmethod
    def _source_balanced(
        hits: list[
            ScholarlyLexicalHit
        ],
        *,
        limit: int,
    ) -> tuple[
        ScholarlyLexicalHit,
        ...,
    ]:
        buckets: dict[
            str,
            deque[
                ScholarlyLexicalHit
            ],
        ] = defaultdict(deque)

        source_order: list[str] = []

        for hit in hits:
            source_id = (
                hit.passage.source_id
            )

            if source_id not in buckets:
                source_order.append(
                    source_id
                )

            buckets[
                source_id
            ].append(
                hit
            )

        selected: list[
            ScholarlyLexicalHit
        ] = []

        while len(selected) < limit:
            progressed = False

            for source_id in source_order:
                bucket = buckets[
                    source_id
                ]

                if not bucket:
                    continue

                selected.append(
                    bucket.popleft()
                )

                progressed = True

                if (
                    len(selected)
                    >= limit
                ):
                    break

            if not progressed:
                break

        return tuple(selected)
