from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow.parquet as pq

from basira.sources.hadith.hadeethenc.parser import (
    HadeethEncOfficialParser,
)
from basira.sources.hadith.hadeethenc.workbook import (
    load_hadeethenc_arabic_workbook,
    load_hadeethenc_english_workbook,
)
from basira.sources.hadith.quranlab.parser import (
    QuranLabSnapshotParser,
)
from basira.verification.hadith_identity import (
    HadithIdentityResolver,
    HadithIdentityScope,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Basira canonical Hadith "
            "identity resolution using the official "
            "HadeethEnc and QuranLab snapshots."
        )
    )

    parser.add_argument(
        "--official-ar",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--official-en",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--quranlab-root",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def load_parquet_rows(
    root: Path,
    config: str,
) -> list[dict]:
    files = sorted(
        (root / config).glob(
            "*.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No Parquet files for {config}"
        )

    rows: list[dict] = []

    for file in files:
        rows.extend(
            pq.read_table(
                file
            ).to_pylist()
        )

    return rows


def main() -> int:
    args = parse_args()

    official_ar = (
        load_hadeethenc_arabic_workbook(
            args.official_ar
        )
    )

    official_en = (
        load_hadeethenc_english_workbook(
            args.official_en
        )
    )

    quranlab_ar = load_parquet_rows(
        args.quranlab_root,
        "hadeethenc-ar",
    )

    quranlab_en = load_parquet_rows(
        args.quranlab_root,
        "hadeethenc-en",
    )

    official_en_by_id = {
        row.id: row
        for row in official_en.rows
    }

    quranlab_ar_by_id = {
        int(row["hadeethenc_id"]): row
        for row in quranlab_ar
    }

    quranlab_en_by_id = {
        int(row["hadeethenc_id"]): row
        for row in quranlab_en
    }

    official_parser = (
        HadeethEncOfficialParser()
    )

    quranlab_parser = (
        QuranLabSnapshotParser()
    )

    resolver = (
        HadithIdentityResolver()
    )

    official_identities = {}
    quranlab_identities = {}

    for row in official_ar.rows:
        english = (
            official_en_by_id.get(
                row.id
            )
        )

        record = official_parser.parse(
            row.model_dump(),
            arabic_release=(
                official_ar.release
            ),
            english_payload=(
                english.model_dump()
                if english is not None
                else None
            ),
            english_release=(
                official_en.release
                if english is not None
                else None
            ),
        )

        identity = resolver.resolve(
            record
        )

        assert (
            identity.scope
            is HadithIdentityScope
            .SHARED_EXTERNAL_REFERENCE
        )

        assert (
            identity.key
            not in official_identities
        )

        official_identities[
            identity.key
        ] = record

    for hadith_id, row in (
        quranlab_ar_by_id.items()
    ):
        english = (
            quranlab_en_by_id.get(
                hadith_id
            )
        )

        record = (
            quranlab_parser.parse(
                config="hadeethenc-ar",
                payload=row,
                paired_payload=english,
            )
        )

        identity = resolver.resolve(
            record
        )

        assert (
            identity.scope
            is HadithIdentityScope
            .SHARED_EXTERNAL_REFERENCE
        )

        assert (
            identity.key
            not in quranlab_identities
        )

        quranlab_identities[
            identity.key
        ] = record

    official_keys = set(
        official_identities
    )

    quranlab_keys = set(
        quranlab_identities
    )

    shared = (
        official_keys
        & quranlab_keys
    )

    official_only = (
        official_keys
        - quranlab_keys
    )

    quranlab_only = (
        quranlab_keys
        - official_keys
    )

    assert (
        len(official_keys)
        == 3_582
    )

    assert (
        len(quranlab_keys)
        == 3_574
    )

    assert len(shared) == 3_574
    assert len(official_only) == 8
    assert len(quranlab_only) == 0

    expected_official_only = {
        "hadeethenc:65585",
        "hadeethenc:65960",
        "hadeethenc:65990",
        "hadeethenc:66108",
        "hadeethenc:66109",
        "hadeethenc:66117",
        "hadeethenc:66285",
        "hadeethenc:66286",
    }

    assert (
        official_only
        == expected_official_only
    )

    print("=" * 88)
    print(
        "BASIRA — HADITH CANONICAL IDENTITY"
    )
    print("=" * 88)

    print(
        "Official identities:",
        len(official_keys),
    )

    print(
        "QuranLab identities:",
        len(quranlab_keys),
    )

    print(
        "Shared identities:",
        len(shared),
    )

    print(
        "Official-only identities:",
        len(official_only),
    )

    print(
        "QuranLab-only identities:",
        len(quranlab_only),
    )

    print()
    print("Official-only keys:")

    for key in sorted(
        official_only
    ):
        print(" ", key)

    print()
    print("=" * 88)
    print(
        "HADITH IDENTITY RESULT: PASS"
    )
    print(
        "3,574 independently observed "
        "HadeethEnc records resolve to the "
        "same shared identities."
    )
    print(
        "8 official-only identities remain "
        "preserved without false merging."
    )
    print("=" * 88)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
