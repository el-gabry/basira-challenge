from __future__ import annotations

from basira.models.hadith import (
    HadithRecord,
    HadithReference,
    HadithTextVariant,
)
from basira.models.source_manifest import (
    IntegrityStatus,
    SourceDomain,
    SourceManifest,
    SourceRole,
    SourceStatus,
)
from basira.retrieval.arabic_query import (
    build_arabic_query,
)
from basira.retrieval.hadith_index import (
    HadithLocalIndex,
    HadithMatchType,
)
from basira.sources.registry import (
    TrustedSourceRegistry,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)


def record(
    *,
    source_id: str,
    number: str,
    text: str,
) -> HadithRecord:
    return HadithRecord(
        record_id=(
            f"{source_id}:{number}"
        ),
        primary_reference=(
            HadithReference(
                source_id=source_id,
                collection_id="hadeethenc",
                hadith_number=number,
            )
        ),
        text_variants=(
            HadithTextVariant(
                source_id=source_id,
                arabic_text=text,
            ),
        ),
    )


def manifest(
    source_id: str,
    *,
    approved: bool = True,
) -> SourceManifest:
    return SourceManifest(
        source_id=source_id,
        source_name=source_id,
        domain=SourceDomain.HADITH,
        role=(
            SourceRole
            .AUTHORITATIVE_REFERENCE
        ),
        status=(
            SourceStatus.APPROVED
            if approved
            else SourceStatus.PENDING
        ),
        integrity_status=(
            IntegrityStatus.VERIFIED
        ),
    )


def runtime(
    *items: SourceManifest,
) -> FailClosedSourceRuntime:
    return FailClosedSourceRuntime(
        TrustedSourceRegistry(
            items
        )
    )


def index() -> HadithLocalIndex:
    return HadithLocalIndex(
        runtime=runtime(
            manifest(
                "hadeethenc-official"
            )
        )
    )


def test_exact_reference() -> None:
    hadith_index = index()

    hadith_index.add(
        record(
            source_id=(
                "hadeethenc-official"
            ),
            number="1751",
            text="نص الحديث",
        )
    )

    hits = (
        hadith_index.search_reference(
            collection_id="hadeethenc",
            hadith_number="1751",
        )
    )

    assert len(hits) == 1

    assert (
        hits[0].match_type
        is HadithMatchType.EXACT_REFERENCE
    )


def test_exact_source_text() -> None:
    hadith_index = index()

    text = (
        "إِنَّمَا الأَعْمَالُ "
        "بِالنِّيَّاتِ"
    )

    hadith_index.add(
        record(
            source_id=(
                "hadeethenc-official"
            ),
            number="1",
            text=text,
        )
    )

    hits = hadith_index.search_text(
        text
    )

    assert (
        hits[0].match_type
        is HadithMatchType.EXACT_ARABIC
    )


def test_normalized_text() -> None:
    hadith_index = index()

    hadith_index.add(
        record(
            source_id=(
                "hadeethenc-official"
            ),
            number="1",
            text=(
                "إِنَّمَا الأَعْمَالُ "
                "بِالنِّيَّاتِ"
            ),
        )
    )

    hits = hadith_index.search_text(
        "انما الاعمال بالنيات"
    )

    assert (
        hits[0].match_type
        is HadithMatchType.NORMALIZED_ARABIC
    )


def test_phrase_search() -> None:
    hadith_index = index()

    hadith_index.add(
        record(
            source_id=(
                "hadeethenc-official"
            ),
            number="1",
            text=(
                "إنما الأعمال بالنيات "
                "وإنما لكل امرئ ما نوى"
            ),
        )
    )

    hits = hadith_index.search_text(
        "لكل امرئ ما نوى"
    )

    assert (
        hits[0].match_type
        is HadithMatchType.PHRASE
    )


def test_query_object_is_supported() -> None:
    hadith_index = index()

    hadith_index.add(
        record(
            source_id=(
                "hadeethenc-official"
            ),
            number="1",
            text=(
                "إنما الأعمال بالنيات"
            ),
        )
    )

    query = build_arabic_query(
        "إنما الأعمال بالنيات"
    )

    hits = (
        hadith_index.search_query(
            query
        )
    )

    assert len(hits) == 1


def test_shared_identity_bundles_sources() -> None:
    hadith_index = HadithLocalIndex(
        runtime=runtime(
            manifest(
                "hadeethenc-official"
            ),
            manifest(
                "quranlab-hadith"
            ),
        )
    )

    hadith_index.add_many(
        [
            record(
                source_id=(
                    "hadeethenc-official"
                ),
                number="1751",
                text="نص الحديث",
            ),
            record(
                source_id=(
                    "quranlab-hadith"
                ),
                number="1751",
                text="نص الحديث",
            ),
        ]
    )

    hits = (
        hadith_index.search_reference(
            collection_id="hadeethenc",
            hadith_number="1751",
        )
    )

    assert len(hits) == 1

    assert (
        hits[0]
        .bundle
        .identity
        .key
        == "hadeethenc:1751"
    )

    assert (
        len(
            hits[0]
            .bundle
            .records
        )
        == 2
    )


def test_fail_closed_runtime_filters_pending_source() -> None:
    hadith_index = HadithLocalIndex(
        runtime=runtime(
            manifest(
                "hadeethenc-official"
            ),
            manifest(
                "quranlab-hadith",
                approved=False,
            ),
        )
    )

    hadith_index.add_many(
        [
            record(
                source_id=(
                    "hadeethenc-official"
                ),
                number="1751",
                text="نص الحديث",
            ),
            record(
                source_id=(
                    "quranlab-hadith"
                ),
                number="1751",
                text="نص الحديث",
            ),
        ]
    )

    hits = (
        hadith_index.search_reference(
            collection_id="hadeethenc",
            hadith_number="1751",
        )
    )

    assert len(hits) == 1

    assert (
        len(
            hits[0]
            .bundle
            .records
        )
        == 1
    )

    assert (
        hits[0]
        .bundle
        .records[0]
        .primary_reference
        .source_id
        == "hadeethenc-official"
    )
