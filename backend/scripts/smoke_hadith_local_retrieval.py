from __future__ import annotations

import argparse
from pathlib import Path

from basira.models.source_manifest import (
    IntegrityStatus,
    SourceDomain,
    SourceManifest,
    SourceRole,
    SourceStatus,
)
from basira.retrieval.arabic_query import (
    ArabicDialect,
    build_arabic_query,
    normalize_arabic_search_text,
)
from basira.retrieval.hadith_index import (
    HadithLocalIndex,
    HadithMatchType,
)
from basira.sources.hadith.hadeethenc.parser import (
    HadeethEncOfficialParser,
)
from basira.sources.hadith.hadeethenc.workbook import (
    load_hadeethenc_arabic_workbook,
    load_hadeethenc_english_workbook,
)
from basira.sources.registry import (
    TrustedSourceRegistry,
)
from basira.sources.runtime_access import (
    FailClosedSourceRuntime,
)

EXPECTED_RECORDS = 3_582
TARGET_ID = 1751


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run real-data smoke validation for "
            "Basira local Hadith retrieval."
        )
    )

    parser.add_argument(
        "--arabic",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--english",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def runtime() -> FailClosedSourceRuntime:
    manifest = SourceManifest(
        source_id="hadeethenc-official",
        source_name=(
            "HadeethEnc Official Hadith Releases"
        ),
        domain=SourceDomain.HADITH,
        role=SourceRole.AUTHORITATIVE_REFERENCE,
        status=SourceStatus.APPROVED,
        integrity_status=IntegrityStatus.VERIFIED,
    )

    return FailClosedSourceRuntime(
        TrustedSourceRegistry(
            [manifest]
        )
    )


def main() -> int:
    args = parse_args()

    arabic = (
        load_hadeethenc_arabic_workbook(
            args.arabic
        )
    )

    english = (
        load_hadeethenc_english_workbook(
            args.english
        )
    )

    assert (
        len(arabic.rows)
        == EXPECTED_RECORDS
    )

    english_by_id = {
        row.id: row
        for row in english.rows
    }

    parser = (
        HadeethEncOfficialParser()
    )

    index = HadithLocalIndex(
        runtime=runtime()
    )

    records_by_id = {}

    for row in arabic.rows:
        english_row = (
            english_by_id.get(
                row.id
            )
        )

        record = parser.parse(
            row.model_dump(),
            arabic_release=(
                arabic.release
            ),
            english_payload=(
                english_row.model_dump()
                if english_row is not None
                else None
            ),
            english_release=(
                english.release
                if english_row is not None
                else None
            ),
        )

        index.add(record)

        records_by_id[
            row.id
        ] = record

    assert (
        len(records_by_id)
        == EXPECTED_RECORDS
    )

    target = records_by_id[
        TARGET_ID
    ]

    target_text = (
        target.text_variants[0]
        .arabic_text
    )

    print("=" * 88)
    print(
        "BASIRA — HADITH LOCAL RETRIEVAL SMOKE"
    )
    print("=" * 88)

    print(
        "Indexed records:",
        len(records_by_id),
    )

    print(
        "Target identity:",
        f"hadeethenc:{TARGET_ID}",
    )

    # -------------------------------------------------
    # 1. Exact reference
    # -------------------------------------------------

    reference_hits = (
        index.search_reference(
            collection_id="hadeethenc",
            hadith_number=str(
                TARGET_ID
            ),
        )
    )

    assert len(
        reference_hits
    ) == 1

    assert (
        reference_hits[0]
        .match_type
        is HadithMatchType
        .EXACT_REFERENCE
    )

    assert (
        reference_hits[0]
        .bundle
        .identity
        .key
        == f"hadeethenc:{TARGET_ID}"
    )

    print(
        "Exact reference:",
        "PASS",
    )

    # -------------------------------------------------
    # 2. Exact Arabic text
    # -------------------------------------------------

    exact_hits = (
        index.search_text(
            target_text
        )
    )

    assert exact_hits

    assert (
        exact_hits[0]
        .match_type
        is HadithMatchType
        .EXACT_ARABIC
    )

    print(
        "Exact Arabic:",
        "PASS",
    )

    # -------------------------------------------------
    # 3. Normalized Arabic
    # -------------------------------------------------

    normalized_text = (
        normalize_arabic_search_text(
            target_text
        )
    )

    normalized_hits = (
        index.search_text(
            normalized_text
        )
    )

    assert normalized_hits

    assert (
        normalized_hits[0]
        .match_type
        in {
            HadithMatchType
            .NORMALIZED_ARABIC,
            HadithMatchType
            .EXACT_ARABIC,
        }
    )

    print(
        "Normalized Arabic:",
        "PASS",
    )

    # -------------------------------------------------
    # 4. Phrase retrieval
    # -------------------------------------------------

    tokens = (
        normalized_text.split()
    )

    if len(tokens) < 5:
        raise AssertionError(
            "Target Hadith is too short "
            "for phrase smoke validation."
        )

    phrase = " ".join(
        tokens[2:7]
    )

    phrase_hits = (
        index.search_text(
            phrase
        )
    )

    assert phrase_hits

    assert any(
        hit.bundle.identity.key
        == f"hadeethenc:{TARGET_ID}"
        for hit in phrase_hits
    )

    assert (
        phrase_hits[0]
        .match_type
        is HadithMatchType.PHRASE
    )

    print(
        "Phrase retrieval:",
        "PASS",
    )

    print(
        "Phrase:",
        repr(phrase),
    )

    # -------------------------------------------------
    # 5. Dialect-ready query understanding
    # -------------------------------------------------

    gulf = build_arabic_query(
        "وش صحة هالحديث؟"
    )

    egyptian = build_arabic_query(
        "الحديث ده صح ولا ايه؟"
    )

    levantine = build_arabic_query(
        "شو صحة هاد الحديث؟"
    )

    msa = build_arabic_query(
        "ما صحة هذا الحديث؟"
    )

    assert (
        gulf.dialect
        is ArabicDialect.GULF
    )

    assert (
        egyptian.dialect
        is ArabicDialect.EGYPTIAN
    )

    assert (
        levantine.dialect
        is ArabicDialect.LEVANTINE
    )

    assert (
        msa.dialect
        is ArabicDialect.UNKNOWN
    )

    print()
    print("DIALECT QUERY UNDERSTANDING")

    print(
        " Gulf:",
        gulf.dialect.value,
        "→",
        gulf.intent_text,
    )

    print(
        " Egyptian:",
        egyptian.dialect.value,
        "→",
        egyptian.intent_text,
    )

    print(
        " Levantine:",
        levantine.dialect.value,
        "→",
        levantine.intent_text,
    )

    print(
        " MSA/common:",
        msa.dialect.value,
        "→",
        msa.intent_text,
    )

    # -------------------------------------------------
    # Result
    # -------------------------------------------------

    print()
    print("=" * 88)
    print(
        "HADITH LOCAL RETRIEVAL RESULT: PASS"
    )
    print(
        "3,582 official HadeethEnc records "
        "indexed successfully."
    )
    print(
        "Reference, exact-text, normalized-text, "
        "and phrase retrieval passed."
    )
    print(
        "Arabic dialect query representation "
        "passed without modifying source text."
    )
    print("=" * 88)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
