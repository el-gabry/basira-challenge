from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXPECTED_SOURCES = (
    "tafsir-katheer",
    "tafsir-saadi",
    "tafsir-mokhtasar",
    "ayat-nozool",
)

COMPLETE_SOURCES = {
    "tafsir-katheer",
    "tafsir-saadi",
    "tafsir-mokhtasar",
}


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"{path}: expected JSON object."
        )

    return value


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def write_json(
    path: Path,
    value: object,
) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def build_source_entry(
    *,
    snapshot_root: Path,
    source_slug: str,
) -> dict[str, Any]:
    source_root = (
        snapshot_root
        / source_slug
    )

    manifest_path = (
        source_root
        / "snapshot-manifest.json"
    )

    project_path = (
        source_root
        / "project.json"
    )

    corpus_path = (
        source_root
        / "corpus.json"
    )

    audit_path = (
        snapshot_root
        / "audits"
        / "quran-alignment"
        / (
            f"{source_slug}"
            "-quran-alignment.json"
        )
    )

    for path in (
        manifest_path,
        project_path,
        corpus_path,
        audit_path,
    ):
        if not path.exists():
            raise FileNotFoundError(
                path
            )

    manifest = load_json(
        manifest_path
    )

    project = load_json(
        project_path
    )

    audit = load_json(
        audit_path
    )

    record_count = int(
        manifest[
            "record_count"
        ]
    )

    corpus_sha256 = (
        sha256_file(
            corpus_path
        )
    )

    if (
        corpus_sha256
        != manifest[
            "corpus_sha256"
        ]
    ):
        raise ValueError(
            f"{source_slug}: corpus SHA256 "
            "does not match source manifest."
        )

    if (
        audit.get("status")
        != "PASS"
    ):
        raise ValueError(
            f"{source_slug}: Quran alignment "
            "audit is not PASS."
        )

    source_reference_count_raw = (
        audit.get(
            "source_reference_count"
        )
    )

    if source_reference_count_raw is None:
        source_reference_count_raw = (
            audit.get(
                "total_references"
            )
        )

    if source_reference_count_raw is None:
        raise ValueError(
            f"{source_slug}: Quran alignment "
            "audit has no reference count."
        )

    source_reference_count = int(
        source_reference_count_raw
    )

    if (
        source_reference_count
        != record_count
    ):
        raise ValueError(
            f"{source_slug}: record count "
            "does not match audited references."
        )

    unresolved = int(
        audit[
            "unresolved_reference_count"
        ]
    )

    if unresolved != 0:
        raise ValueError(
            f"{source_slug}: unresolved Quran "
            f"alignment count is {unresolved}."
        )

    if (
        source_slug
        in COMPLETE_SOURCES
    ):
        if record_count != 6_236:
            raise ValueError(
                f"{source_slug}: expected "
                "6236 complete-Quran records, "
                f"received {record_count}."
            )

        if (
            manifest[
                "coverage_mode"
            ]
            != "complete_quran"
        ):
            raise ValueError(
                f"{source_slug}: expected "
                "complete_quran coverage."
            )

    else:
        if (
            manifest[
                "coverage_mode"
            ]
            != "sparse"
        ):
            raise ValueError(
                f"{source_slug}: expected "
                "sparse coverage."
            )

        if not (
            0
            < record_count
            <= 6_236
        ):
            raise ValueError(
                f"{source_slug}: invalid "
                f"sparse count {record_count}."
            )

    return {
        "source_id": (
            manifest[
                "source_id"
            ]
        ),
        "source_slug": (
            source_slug
        ),
        "title": (
            project[
                "title"
            ]
        ),
        "description": (
            project[
                "description"
            ]
        ),
        "project_type": (
            project[
                "type"
            ]
        ),
        "role": (
            manifest[
                "role"
            ]
        ),
        "coverage_mode": (
            manifest[
                "coverage_mode"
            ]
        ),
        "record_count": (
            record_count
        ),
        "unique_reference_count": (
            source_reference_count
        ),
        "corpus_file": (
            str(
                corpus_path.relative_to(
                    snapshot_root
                )
            )
        ),
        "corpus_sha256": (
            corpus_sha256
        ),
        "quran_alignment": {
            "canonical_source": (
                audit[
                    "canonical_source"
                ]
            ),
            "script_comparison": (
                audit[
                    "script_comparison"
                ]
            ),
            "exact_matches": (
                audit[
                    "exact_matches"
                ]
            ),
            "orthographically_equivalent": (
                audit[
                    "orthographically_equivalent"
                ]
            ),
            "unresolved_reference_count": (
                unresolved
            ),
            "status": (
                audit[
                    "status"
                ]
            ),
            "audit_file": (
                str(
                    audit_path.relative_to(
                        snapshot_root
                    )
                )
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--snapshot-root",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    entries = [
        build_source_entry(
            snapshot_root=(
                args.snapshot_root
            ),
            source_slug=source_slug,
        )
        for source_slug
        in EXPECTED_SOURCES
    ]

    total_records = sum(
        int(
            entry[
                "record_count"
            ]
        )
        for entry in entries
    )

    manifest = {
        "snapshot_type": (
            "surahapp-scholarly-sources"
        ),
        "snapshot_version": "v1",
        "provider": (
            "Surah App / Tafsir Center"
        ),
        "built_at": (
            datetime.now(UTC)
            .isoformat()
        ),
        "source_count": (
            len(entries)
        ),
        "total_record_count": (
            total_records
        ),
        "integrity_status": (
            "PASS"
        ),
        "sources": (
            entries
        ),
    }

    output_path = (
        args.snapshot_root
        / "snapshot-manifest.json"
    )

    write_json(
        output_path,
        manifest,
    )

    print(
        "=" * 88
    )
    print(
        "SURAH APP AGGREGATE SNAPSHOT"
    )
    print(
        "=" * 88
    )

    for entry in entries:
        alignment = (
            entry[
                "quran_alignment"
            ]
        )

        print(
            entry["source_slug"],
            "→",
            entry["record_count"],
            "records",
            "| alignment:",
            alignment["status"],
            "| unresolved:",
            alignment[
                "unresolved_reference_count"
            ],
        )

    print()
    print(
        "Sources:",
        len(entries),
    )
    print(
        "Total records:",
        total_records,
    )
    print(
        "Integrity:",
        "PASS",
    )
    print(
        "Manifest:",
        output_path,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
