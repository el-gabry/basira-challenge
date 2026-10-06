from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from basira.sources.hadith.hadeethenc.workbook import (
    load_hadeethenc_arabic_workbook,
    load_hadeethenc_english_workbook,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a sanitized Basira snapshot manifest "
            "for official HadeethEnc XLSX releases."
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

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> int:
    args = parse_args()

    arabic = load_hadeethenc_arabic_workbook(
        args.arabic
    )

    english = load_hadeethenc_english_workbook(
        args.english
    )

    manifest = {
        "source_id": "hadeethenc-official",
        "repository": "hadeethenc.com",
        "revision": (
            f"ar-{arabic.release.version}"
            f"+en-{english.release.version}"
        ),
        "integrity_status": "verified_local_copy",
        "snapshot_manifest_sha256": None,
        "artifacts": [
            {
                "config": (
                    f"ar-{arabic.release.version}"
                ),
                "path": args.arabic.name,
                "sha256": sha256_file(
                    args.arabic
                ),
                "size_bytes": (
                    args.arabic.stat().st_size
                ),
                "row_count": len(
                    arabic.rows
                ),
            },
            {
                "config": (
                    f"en-{english.release.version}"
                ),
                "path": args.english.name,
                "sha256": sha256_file(
                    args.english
                ),
                "size_bytes": (
                    args.english.stat().st_size
                ),
                "row_count": len(
                    english.rows
                ),
            },
        ],
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("Created:", args.output)
    print(
        "Arabic release:",
        arabic.release.version,
    )
    print(
        "Arabic rows:",
        len(arabic.rows),
    )
    print(
        "English release:",
        english.release.version,
    )
    print(
        "English rows:",
        len(english.rows),
    )
    print(
        "Artifact rows:",
        (
            len(arabic.rows)
            + len(english.rows)
        ),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
