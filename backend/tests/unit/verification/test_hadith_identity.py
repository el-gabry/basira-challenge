from __future__ import annotations

from basira.models.hadith import (
    HadithRecord,
    HadithReference,
    HadithTextVariant,
)
from basira.verification.hadith_identity import (
    HadithIdentityResolver,
    HadithIdentityScope,
    normalize_collection_id,
)


def record(
    *,
    source_id: str,
    collection_id: str,
    hadith_number: str,
) -> HadithRecord:
    return HadithRecord(
        record_id=(
            f"{source_id}:"
            f"{collection_id}:"
            f"{hadith_number}"
        ),
        primary_reference=(
            HadithReference(
                source_id=source_id,
                collection_id=collection_id,
                hadith_number=hadith_number,
            )
        ),
        text_variants=(
            HadithTextVariant(
                source_id=source_id,
                arabic_text="نص الحديث",
            ),
        ),
    )


def test_hadeethenc_is_shared_external_identity() -> None:
    resolver = HadithIdentityResolver()

    official = record(
        source_id="hadeethenc-official",
        collection_id="hadeethenc",
        hadith_number="1751",
    )

    quranlab = record(
        source_id="quranlab-hadith",
        collection_id="hadeethenc",
        hadith_number="1751",
    )

    official_identity = (
        resolver.resolve(
            official
        )
    )

    quranlab_identity = (
        resolver.resolve(
            quranlab
        )
    )

    assert (
        official_identity.key
        == "hadeethenc:1751"
    )

    assert (
        official_identity
        == quranlab_identity
    )

    assert (
        official_identity.scope
        is HadithIdentityScope
        .SHARED_EXTERNAL_REFERENCE
    )

    assert resolver.same_identity(
        official,
        quranlab,
    )


def test_non_verified_collection_remains_source_local() -> None:
    resolver = HadithIdentityResolver()

    quranlab = record(
        source_id="quranlab-hadith",
        collection_id="bukhari",
        hadith_number="1",
    )

    future_source = record(
        source_id="future-source",
        collection_id="bukhari",
        hadith_number="1",
    )

    first = resolver.resolve(
        quranlab
    )

    second = resolver.resolve(
        future_source
    )

    assert (
        first.scope
        is HadithIdentityScope.SOURCE_LOCAL
    )

    assert (
        first.key
        == "quranlab-hadith:bukhari:1"
    )

    assert (
        second.key
        == "future-source:bukhari:1"
    )

    assert not resolver.same_identity(
        quranlab,
        future_source,
    )


def test_same_source_reference_is_stable() -> None:
    resolver = HadithIdentityResolver()

    left = record(
        source_id="quranlab-hadith",
        collection_id="bukhari",
        hadith_number="25",
    )

    right = record(
        source_id="quranlab-hadith",
        collection_id="bukhari",
        hadith_number="25",
    )

    assert resolver.same_identity(
        left,
        right,
    )


def test_collection_aliases_are_normalized() -> None:
    assert (
        normalize_collection_id(
            "Abu Dawud"
        )
        == "abudawud"
    )

    assert (
        normalize_collection_id(
            "abu_dawud"
        )
        == "abudawud"
    )

    assert (
        normalize_collection_id(
            "Al-Bukhari"
        )
        == "bukhari"
    )


def test_custom_shared_namespace_must_be_explicit() -> None:
    resolver = HadithIdentityResolver(
        shared_reference_collections=(
            frozenset(
                {
                    "hadeethenc",
                    "bukhari",
                }
            )
        )
    )

    first = record(
        source_id="source-a",
        collection_id="bukhari",
        hadith_number="42",
    )

    second = record(
        source_id="source-b",
        collection_id="bukhari",
        hadith_number="42",
    )

    identity = resolver.resolve(
        first
    )

    assert (
        identity.scope
        is HadithIdentityScope
        .SHARED_EXTERNAL_REFERENCE
    )

    assert identity.key == "bukhari:42"

    assert resolver.same_identity(
        first,
        second,
    )
