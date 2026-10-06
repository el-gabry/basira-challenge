from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)


class ScholarlyPassageNotFoundError(
    KeyError
):
    """
    Raised when a scholarly passage id is not
    available in the repository.
    """


class ScholarlyRepository:
    """
    Local repository of attributable scholarly
    passages.

    Quran-linked scholarly passages are indexed by
    canonical Quran reference so anchor-first
    retrieval does not require semantic search.
    """

    def __init__(
        self,
        passages: Iterable[
            ScholarlyPassage
        ],
    ) -> None:
        self._passages = tuple(
            passages
        )

        self._by_id: dict[
            str,
            ScholarlyPassage,
        ] = {}

        self._by_reference: dict[
            tuple[int, int],
            list[
                ScholarlyPassage
            ],
        ] = defaultdict(
            list
        )

        self._by_domain: dict[
            ScholarlyDomain,
            list[
                ScholarlyPassage
            ],
        ] = defaultdict(
            list
        )

        self._by_source: dict[
            str,
            list[
                ScholarlyPassage
            ],
        ] = defaultdict(
            list
        )

        for passage in (
            self._passages
        ):
            if (
                passage.passage_id
                in self._by_id
            ):
                raise ValueError(
                    "Duplicate scholarly "
                    "passage id: "
                    f"{passage.passage_id}"
                )

            self._by_id[
                passage.passage_id
            ] = passage

            self._by_domain[
                passage.domain
            ].append(
                passage
            )

            self._by_source[
                passage.source_id
            ].append(
                passage
            )

            self._index_quran_span(
                passage
            )

    def __len__(
        self,
    ) -> int:
        return len(
            self._passages
        )

    def get(
        self,
        passage_id: str,
    ) -> ScholarlyPassage | None:
        return self._by_id.get(
            passage_id
        )

    def require(
        self,
        passage_id: str,
    ) -> ScholarlyPassage:
        passage = self.get(
            passage_id
        )

        if passage is None:
            raise (
                ScholarlyPassageNotFoundError(
                    "Scholarly passage "
                    "not found: "
                    f"{passage_id}"
                )
            )

        return passage

    def find_by_quran_reference(
        self,
        surah_number: int,
        ayah_number: int,
        *,
        domain: (
            ScholarlyDomain
            | None
        ) = None,
    ) -> tuple[
        ScholarlyPassage,
        ...,
    ]:
        passages = (
            self._by_reference.get(
                (
                    surah_number,
                    ayah_number,
                ),
                [],
            )
        )

        if domain is None:
            return tuple(
                passages
            )

        return tuple(
            passage
            for passage in passages
            if passage.domain
            == domain
        )

    def find_by_domain(
        self,
        domain: ScholarlyDomain,
    ) -> tuple[
        ScholarlyPassage,
        ...,
    ]:
        return tuple(
            self._by_domain.get(
                domain,
                [],
            )
        )

    def find_by_source(
        self,
        source_id: str,
    ) -> tuple[
        ScholarlyPassage,
        ...,
    ]:
        return tuple(
            self._by_source.get(
                source_id,
                [],
            )
        )

    def all(
        self,
    ) -> tuple[
        ScholarlyPassage,
        ...,
    ]:
        return self._passages

    def _index_quran_span(
        self,
        passage: ScholarlyPassage,
    ) -> None:
        if (
            passage.surah_number
            is None
            or passage.ayah_start
            is None
        ):
            return

        end = (
            passage.ayah_end
            if passage.ayah_end
            is not None
            else passage.ayah_start
        )

        for ayah_number in range(
            passage.ayah_start,
            end + 1,
        ):
            self._by_reference[
                (
                    passage
                    .surah_number,
                    ayah_number,
                )
            ].append(
                passage
            )
