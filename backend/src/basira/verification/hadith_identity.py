from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basira.models.hadith import (
    HadithRecord,
)


class HadithIdentityScope(StrEnum):
    """
    How broadly an identity may be used.

    SHARED_EXTERNAL_REFERENCE:
        A stable upstream identifier independently
        observed across more than one Basira source.

    SOURCE_LOCAL:
        The reference is valid inside its source but
        Basira has not yet established that the same
        number in another source is equivalent.
    """

    SHARED_EXTERNAL_REFERENCE = (
        "shared_external_reference"
    )

    SOURCE_LOCAL = "source_local"


@dataclass(
    frozen=True,
    slots=True,
)
class HadithCanonicalIdentity:
    key: str

    scope: HadithIdentityScope

    collection_id: str

    hadith_number: str

    source_id: str | None = None


_COLLECTION_ALIASES = {
    "hadeethenc": "hadeethenc",
    "hadeeth-enc": "hadeethenc",
    "hadeeth_enc": "hadeethenc",
    "bukhari": "bukhari",
    "al-bukhari": "bukhari",
    "muslim": "muslim",
    "abudawud": "abudawud",
    "abu-dawud": "abudawud",
    "abu_dawud": "abudawud",
    "tirmidhi": "tirmidhi",
    "al-tirmidhi": "tirmidhi",
    "nasai": "nasai",
    "al-nasai": "nasai",
    "ibnmajah": "ibnmajah",
    "ibn-majah": "ibnmajah",
    "malik": "malik",
    "ahmad": "ahmad",
    "darimi": "darimi",
    "nawawi": "nawawi",
    "qudsi": "qudsi",
    "dehlawi": "dehlawi",
}


def normalize_collection_id(
    value: str,
) -> str:
    normalized = (
        value
        .strip()
        .casefold()
        .replace(" ", "-")
    )

    if not normalized:
        raise ValueError(
            "collection_id must not be blank."
        )

    return _COLLECTION_ALIASES.get(
        normalized,
        normalized,
    )


def normalize_hadith_number(
    value: str,
) -> str:
    normalized = value.strip()

    if not normalized:
        raise ValueError(
            "hadith_number must not be blank."
        )

    return normalized


class HadithIdentityResolver:
    """
    Resolve conservative Basira Hadith identities.

    Only explicitly trusted shared-reference
    namespaces may collapse records across sources.

    Everything else remains source-local until a
    separate numbering/provenance mapping has been
    reviewed.
    """

    def __init__(
        self,
        *,
        shared_reference_collections: (
            frozenset[str] | None
        ) = None,
    ) -> None:
        if shared_reference_collections is None:
            shared_reference_collections = (
                frozenset(
                    {
                        "hadeethenc",
                    }
                )
            )

        self.shared_reference_collections = (
            frozenset(
                normalize_collection_id(
                    value
                )
                for value
                in shared_reference_collections
            )
        )

    def resolve(
        self,
        record: HadithRecord,
    ) -> HadithCanonicalIdentity:
        reference = (
            record.primary_reference
        )

        collection_id = (
            normalize_collection_id(
                reference.collection_id
            )
        )

        hadith_number = (
            normalize_hadith_number(
                reference.hadith_number
            )
        )

        if (
            collection_id
            in self.shared_reference_collections
        ):
            return HadithCanonicalIdentity(
                key=(
                    f"{collection_id}:"
                    f"{hadith_number}"
                ),
                scope=(
                    HadithIdentityScope
                    .SHARED_EXTERNAL_REFERENCE
                ),
                collection_id=collection_id,
                hadith_number=hadith_number,
                source_id=None,
            )

        source_id = (
            reference.source_id.strip()
        )

        if not source_id:
            raise ValueError(
                "source_id must not be blank."
            )

        return HadithCanonicalIdentity(
            key=(
                f"{source_id}:"
                f"{collection_id}:"
                f"{hadith_number}"
            ),
            scope=(
                HadithIdentityScope
                .SOURCE_LOCAL
            ),
            collection_id=collection_id,
            hadith_number=hadith_number,
            source_id=source_id,
        )

    def same_identity(
        self,
        left: HadithRecord,
        right: HadithRecord,
    ) -> bool:
        return (
            self.resolve(left).key
            == self.resolve(right).key
        )
