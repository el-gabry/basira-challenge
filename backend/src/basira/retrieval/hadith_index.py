from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from basira.models.hadith import (
    HadithRecord,
)
from basira.models.source_usage import (
    RuntimeUse,
)
from basira.retrieval.arabic_query import (
    ArabicQuery,
    build_arabic_query,
    normalize_arabic_search_text,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)
from basira.verification.hadith_identity import (
    HadithCanonicalIdentity,
    HadithIdentityResolver,
    normalize_collection_id,
)


class HadithMatchType(StrEnum):
    EXACT_REFERENCE = "exact_reference"
    EXACT_ARABIC = "exact_arabic"
    NORMALIZED_ARABIC = "normalized_arabic"
    PHRASE = "phrase"


@dataclass(
    frozen=True,
    slots=True,
)
class HadithEvidenceBundle:
    identity: HadithCanonicalIdentity

    records: tuple[
        HadithRecord,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class HadithRetrievalHit:
    match_type: HadithMatchType

    bundle: HadithEvidenceBundle


class HadithLocalIndex:
    """
    Deterministic local Hadith retrieval.

    Indexing and runtime authorization are separate:
    records can exist locally while fail-closed runtime
    policy prevents them from being returned.
    """

    def __init__(
        self,
        *,
        runtime: FailClosedSourceRuntime,
        identity_resolver: (
            HadithIdentityResolver | None
        ) = None,
    ) -> None:
        self.runtime = runtime

        self.identity_resolver = (
            identity_resolver
            or HadithIdentityResolver()
        )

        self._records_by_identity: dict[
            str,
            list[HadithRecord],
        ] = defaultdict(list)

        self._reference_index: dict[
            tuple[str, str],
            set[str],
        ] = defaultdict(set)

        self._exact_arabic_index: dict[
            str,
            set[str],
        ] = defaultdict(set)

        self._normalized_arabic_index: dict[
            str,
            set[str],
        ] = defaultdict(set)

        self._normalized_texts: dict[
            str,
            set[str],
        ] = defaultdict(set)

    def add(
        self,
        record: HadithRecord,
    ) -> None:
        identity = (
            self.identity_resolver.resolve(
                record
            )
        )

        identity_key = (
            identity.key
        )

        self._records_by_identity[
            identity_key
        ].append(record)

        reference = (
            record.primary_reference
        )

        reference_key = (
            normalize_collection_id(
                reference.collection_id
            ),
            reference.hadith_number.strip(),
        )

        self._reference_index[
            reference_key
        ].add(
            identity_key
        )

        for variant in (
            record.text_variants
        ):
            source_text = (
                variant.arabic_text
            )

            self._exact_arabic_index[
                source_text
            ].add(
                identity_key
            )

            normalized = (
                normalize_arabic_search_text(
                    source_text
                )
            )

            if not normalized:
                continue

            self._normalized_arabic_index[
                normalized
            ].add(
                identity_key
            )

            self._normalized_texts[
                identity_key
            ].add(
                normalized
            )

    def add_many(
        self,
        records: Iterable[
            HadithRecord
        ],
    ) -> None:
        for record in records:
            self.add(record)

    def _authorized_records(
        self,
        identity_key: str,
    ) -> tuple[
        HadithRecord,
        ...,
    ]:
        authorized = []

        for record in (
            self._records_by_identity[
                identity_key
            ]
        ):
            source_id = (
                record
                .primary_reference
                .source_id
            )

            if self.runtime.allows(
                source_id=source_id,
                runtime_use=(
                    RuntimeUse
                    .RETRIEVE_PASSAGES
                ),
            ):
                authorized.append(
                    record
                )

        return tuple(
            authorized
        )

    def _bundle(
        self,
        identity_key: str,
    ) -> HadithEvidenceBundle | None:
        records = (
            self._authorized_records(
                identity_key
            )
        )

        if not records:
            return None

        identity = (
            self.identity_resolver.resolve(
                records[0]
            )
        )

        return HadithEvidenceBundle(
            identity=identity,
            records=records,
        )

    def _build_hits(
        self,
        *,
        identity_keys: Iterable[str],
        match_type: HadithMatchType,
        limit: int,
    ) -> tuple[
        HadithRetrievalHit,
        ...,
    ]:
        if limit <= 0:
            return ()

        result = []

        for identity_key in sorted(
            set(identity_keys)
        ):
            bundle = self._bundle(
                identity_key
            )

            if bundle is None:
                continue

            result.append(
                HadithRetrievalHit(
                    match_type=(
                        match_type
                    ),
                    bundle=bundle,
                )
            )

            if len(result) >= limit:
                break

        return tuple(
            result
        )

    def search_reference(
        self,
        *,
        collection_id: str,
        hadith_number: str,
        limit: int = 10,
    ) -> tuple[
        HadithRetrievalHit,
        ...,
    ]:
        key = (
            normalize_collection_id(
                collection_id
            ),
            hadith_number.strip(),
        )

        return self._build_hits(
            identity_keys=(
                self._reference_index
                .get(
                    key,
                    set(),
                )
            ),
            match_type=(
                HadithMatchType
                .EXACT_REFERENCE
            ),
            limit=limit,
        )

    def search_query(
        self,
        query: ArabicQuery,
        *,
        limit: int = 10,
    ) -> tuple[
        HadithRetrievalHit,
        ...,
    ]:
        exact = (
            self._exact_arabic_index
            .get(
                query.original_text,
                set(),
            )
        )

        if exact:
            return self._build_hits(
                identity_keys=exact,
                match_type=(
                    HadithMatchType
                    .EXACT_ARABIC
                ),
                limit=limit,
            )

        normalized_exact = (
            self._normalized_arabic_index
            .get(
                query.search_text,
                set(),
            )
        )

        if normalized_exact:
            return self._build_hits(
                identity_keys=(
                    normalized_exact
                ),
                match_type=(
                    HadithMatchType
                    .NORMALIZED_ARABIC
                ),
                limit=limit,
            )

        phrase_matches: list[
            str
        ] = []

        for (
            identity_key,
            texts,
        ) in (
            self._normalized_texts
            .items()
        ):
            if any(
                query.search_text
                in text
                for text in texts
            ):
                phrase_matches.append(
                    identity_key
                )

        return self._build_hits(
            identity_keys=(
                phrase_matches
            ),
            match_type=(
                HadithMatchType.PHRASE
            ),
            limit=limit,
        )

    def search_text(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> tuple[
        HadithRetrievalHit,
        ...,
    ]:
        if not query.strip():
            return ()

        return self.search_query(
            build_arabic_query(
                query
            ),
            limit=limit,
        )
