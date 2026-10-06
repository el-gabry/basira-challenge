from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from basira.normalization.quran import (
    normalize_quran_search_text,
)
from basira.sources.quran.tanzil.parser import (
    TanzilQuranParser,
)

BASE_URL = (
    "https://dev.surahapp.com/api/v1"
)

MAX_RETRIES = 4
REQUEST_DELAY_SECONDS = 0.15


@dataclass(
    frozen=True,
    slots=True,
)
class SurahAppSource:
    slug: str
    role: str
    coverage_mode: str


SOURCES = (
    SurahAppSource(
        slug="tafsir-katheer",
        role="tafsir",
        coverage_mode="complete_quran",
    ),
    SurahAppSource(
        slug="tafsir-saadi",
        role="tafsir",
        coverage_mode="complete_quran",
    ),
    SurahAppSource(
        slug="tafsir-mokhtasar",
        role="tafsir",
        coverage_mode="complete_quran",
    ),
    SurahAppSource(
        slug="ayat-nozool",
        role="revelation_context",
        coverage_mode="sparse",
    ),
)


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


def fetch(
    url: str,
    *,
    allow_not_found: bool = False,
) -> tuple[
    int,
    bytes,
    str,
]:
    last_error: Exception | None = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "BasiraVerify/1.0 "
                    "(trusted-source-ingestion)"
                ),
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=60,
            ) as response:
                return (
                    response.status,
                    response.read(),
                    response.headers.get(
                        "Content-Type",
                        "",
                    ),
                )

        except urllib.error.HTTPError as exc:
            body = exc.read()

            if (
                exc.code == 404
                and allow_not_found
            ):
                return (
                    404,
                    body,
                    exc.headers.get(
                        "Content-Type",
                        "",
                    ),
                )

            if (
                exc.code not in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }
                or attempt
                >= MAX_RETRIES
            ):
                raise RuntimeError(
                    "Surah App request failed: "
                    f"{url} → HTTP {exc.code}: "
                    f"{body[:500]!r}"
                ) from exc

            last_error = exc

        except (
            urllib.error.URLError,
            TimeoutError,
        ) as exc:
            last_error = exc

            if attempt >= MAX_RETRIES:
                break

        delay = 2 ** (
            attempt - 1
        )

        print(
            f"  retry in {delay}s..."
        )

        time.sleep(delay)

    raise RuntimeError(
        "Surah App request failed after "
        f"{MAX_RETRIES} attempts: {url}"
    ) from last_error


def parse_json(
    payload: bytes,
    *,
    label: str,
) -> object:
    try:
        return json.loads(
            payload.decode("utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON from {label}."
        ) from exc


def build_expected_quran(
    *,
    uthmani_path: Path,
    simple_plain_path: Path,
) -> tuple[
    dict[int, tuple[int, ...]],
    dict[tuple[int, int], str],
]:
    verses = (
        TanzilQuranParser()
        .parse_files(
            uthmani_path,
            simple_plain_path,
        )
    )

    by_surah: dict[
        int,
        list[int],
    ] = {}

    normalized_text: dict[
        tuple[int, int],
        str,
    ] = {}

    for verse in verses:
        by_surah.setdefault(
            verse.surah_number,
            [],
        ).append(
            verse.ayah_number
        )

        normalized_text[
            (
                verse.surah_number,
                verse.ayah_number,
            )
        ] = (
            normalize_quran_search_text(
                verse.text_search
            )
        )

    expected_by_surah = {
        surah: tuple(
            sorted(ayahs)
        )
        for surah, ayahs
        in by_surah.items()
    }

    if len(expected_by_surah) != 114:
        raise ValueError(
            "Expected 114 Quran surahs."
        )

    return (
        expected_by_surah,
        normalized_text,
    )


def fetch_project_metadata(
    source: SurahAppSource,
) -> dict[str, object]:
    url = (
        f"{BASE_URL}/project/"
        f"{source.slug}"
    )

    status, payload, _ = fetch(
        url
    )

    if status != 200:
        raise RuntimeError(
            f"Project metadata failed: {url}"
        )

    value = parse_json(
        payload,
        label=url,
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            "Project metadata must be an object."
        )

    required = {
        "title",
        "type",
        "locale_type",
        "description",
    }

    if not required.issubset(
        value
    ):
        raise ValueError(
            "Incomplete Surah App project metadata "
            f"for {source.slug}."
        )

    return value


def validate_row(
    *,
    row: object,
    source: SurahAppSource,
    expected_surah: int,
    expected_refs: set[
        tuple[int, int]
    ],
    canonical_texts: dict[
        tuple[int, int],
        str,
    ],
) -> tuple[
    dict[str, object],
    bool,
]:
    if not isinstance(
        row,
        dict,
    ):
        raise ValueError(
            f"{source.slug}: row is not an object."
        )

    required = {
        "content",
        "sura_number",
        "sura_name",
        "aya_number",
        "aya_text",
    }

    if not required.issubset(
        row
    ):
        raise ValueError(
            f"{source.slug}: missing fields "
            f"{sorted(required - set(row))}."
        )

    surah = int(
        str(row["sura_number"])
    )

    ayah = int(
        str(row["aya_number"])
    )

    reference = (
        surah,
        ayah,
    )

    if surah != expected_surah:
        raise ValueError(
            f"{source.slug}: expected surah "
            f"{expected_surah}, received {surah}."
        )

    if reference not in expected_refs:
        raise ValueError(
            f"{source.slug}: unexpected Quran "
            f"reference {surah}:{ayah}."
        )

    content = str(
        row["content"]
    )

    if not content.strip():
        raise ValueError(
            f"{source.slug}: empty content at "
            f"{surah}:{ayah}."
        )

    aya_text = str(
        row["aya_text"]
    )

    if not aya_text.strip():
        raise ValueError(
            f"{source.slug}: empty aya_text at "
            f"{surah}:{ayah}."
        )

    aligned = (
        normalize_quran_search_text(
            aya_text
        )
        == canonical_texts[
            reference
        ]
    )

    return (
        row,
        aligned,
    )


def download_source(
    *,
    source: SurahAppSource,
    output_root: Path,
    expected_by_surah: dict[
        int,
        tuple[int, ...],
    ],
    canonical_texts: dict[
        tuple[int, int],
        str,
    ],
) -> dict[str, object]:
    source_root = (
        output_root
        / source.slug
    )

    raw_root = (
        source_root
        / "raw"
    )

    raw_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata = (
        fetch_project_metadata(
            source
        )
    )

    write_json(
        source_root
        / "project.json",
        metadata,
    )

    combined: list[
        dict[str, object]
    ] = []

    seen_refs: set[
        tuple[int, int]
    ] = set()

    alignment_mismatches: list[
        str
    ] = []

    empty_surahs: list[
        int
    ] = []

    print()
    print("=" * 88)
    print(
        f"DOWNLOADING: {source.slug}"
    )
    print(
        "TITLE:",
        metadata["title"],
    )
    print(
        "ROLE:",
        source.role,
    )
    print(
        "COVERAGE:",
        source.coverage_mode,
    )
    print("=" * 88)

    for surah in range(
        1,
        115,
    ):
        ayahs = (
            expected_by_surah[
                surah
            ]
        )

        start_ayah = ayahs[0]
        end_ayah = ayahs[-1]

        url = (
            f"{BASE_URL}/aya/"
            f"{source.slug}/"
            f"{surah}/"
            f"{start_ayah}/"
            f"{end_ayah}"
        )

        print(
            f"[{source.slug}] "
            f"surah {surah:03d}/114 "
            f"({start_ayah}-{end_ayah})"
        )

        status, raw, content_type = (
            fetch(
                url,
                allow_not_found=(
                    source.coverage_mode
                    == "sparse"
                ),
            )
        )

        raw_path = (
            raw_root
            / f"surah-{surah:03d}.json"
        )

        raw_path.write_bytes(
            raw
        )

        if status == 404:
            empty_surahs.append(
                surah
            )
            continue

        if (
            "application/json"
            not in content_type.lower()
        ):
            raise ValueError(
                f"{source.slug}: non-JSON response "
                f"for surah {surah}: "
                f"{content_type!r}"
            )

        payload = parse_json(
            raw,
            label=url,
        )

        if not isinstance(
            payload,
            list,
        ):
            raise ValueError(
                f"{source.slug}: range endpoint "
                "must return a list."
            )

        expected_refs = {
            (
                surah,
                ayah,
            )
            for ayah in ayahs
        }

        returned_refs: set[
            tuple[int, int]
        ] = set()

        for value in payload:
            row, aligned = (
                validate_row(
                    row=value,
                    source=source,
                    expected_surah=surah,
                    expected_refs=(
                        expected_refs
                    ),
                    canonical_texts=(
                        canonical_texts
                    ),
                )
            )

            reference = (
                int(
                    str(
                        row[
                            "sura_number"
                        ]
                    )
                ),
                int(
                    str(
                        row[
                            "aya_number"
                        ]
                    )
                ),
            )

            if reference in returned_refs:
                raise ValueError(
                    f"{source.slug}: duplicate "
                    f"{reference[0]}:"
                    f"{reference[1]} "
                    "inside response."
                )

            if reference in seen_refs:
                raise ValueError(
                    f"{source.slug}: duplicate "
                    f"{reference[0]}:"
                    f"{reference[1]} "
                    "across snapshot."
                )

            returned_refs.add(
                reference
            )

            seen_refs.add(
                reference
            )

            combined.append(
                row
            )

            if not aligned:
                alignment_mismatches.append(
                    f"{reference[0]}:"
                    f"{reference[1]}"
                )

        if (
            source.coverage_mode
            == "complete_quran"
            and returned_refs
            != expected_refs
        ):
            missing = (
                expected_refs
                - returned_refs
            )

            extra = (
                returned_refs
                - expected_refs
            )

            raise ValueError(
                f"{source.slug}: incomplete "
                f"surah {surah}. "
                f"Missing: "
                f"{sorted(missing)[:20]}. "
                f"Extra: "
                f"{sorted(extra)[:20]}."
            )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    combined.sort(
        key=lambda row: (
            int(
                str(
                    row[
                        "sura_number"
                    ]
                )
            ),
            int(
                str(
                    row[
                        "aya_number"
                    ]
                )
            ),
        )
    )

    if (
        source.coverage_mode
        == "complete_quran"
        and len(combined)
        != 6_236
    ):
        raise ValueError(
            f"{source.slug}: expected 6236 "
            f"records, received "
            f"{len(combined)}."
        )

    corpus_path = (
        source_root
        / "corpus.json"
    )

    write_json(
        corpus_path,
        combined,
    )

    manifest = {
        "provider": (
            "Surah App / Tafsir Center"
        ),
        "provider_url": (
            "https://surahapp.com/"
        ),
        "source_slug": (
            source.slug
        ),
        "source_id": (
            f"surahapp-{source.slug}"
        ),
        "title": (
            metadata["title"]
        ),
        "description": (
            metadata["description"]
        ),
        "role": (
            source.role
        ),
        "coverage_mode": (
            source.coverage_mode
        ),
        "downloaded_at": (
            datetime.now(UTC)
            .isoformat()
        ),
        "record_count": (
            len(combined)
        ),
        "unique_reference_count": (
            len(seen_refs)
        ),
        "empty_surah_count": (
            len(empty_surahs)
        ),
        "empty_surahs": (
            empty_surahs
        ),
        "naive_search_normalization_difference_count": (
            len(
                alignment_mismatches
            )
        ),
        "naive_search_normalization_differences": (
            alignment_mismatches
        ),
        "corpus_file": (
            corpus_path.name
        ),
        "corpus_sha256": (
            sha256_file(
                corpus_path
            )
        ),
    }

    write_json(
        source_root
        / "snapshot-manifest.json",
        manifest,
    )

    print()
    print(
        source.slug,
        "PASS",
    )

    print(
        "Records:",
        len(combined),
    )

    print(
        "Unique references:",
        len(seen_refs),
    )

    print(
        "Empty surahs:",
        len(empty_surahs),
    )

    print(
        "Naive normalization differences:",
        len(
            alignment_mismatches
        ),
    )

    print(
        "SHA256:",
        manifest[
            "corpus_sha256"
        ],
    )

    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--uthmani",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--simple-plain",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        default=None,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        expected_by_surah,
        canonical_texts,
    ) = build_expected_quran(
        uthmani_path=args.uthmani,
        simple_plain_path=(
            args.simple_plain
        ),
    )

    selected = SOURCES

    if args.sources:
        requested = set(
            args.sources
        )

        known = {
            source.slug
            for source in SOURCES
        }

        unknown = (
            requested - known
        )

        if unknown:
            raise ValueError(
                "Unknown Surah App source(s): "
                f"{sorted(unknown)}"
            )

        selected = tuple(
            source
            for source in SOURCES
            if source.slug
            in requested
        )

    manifests = []

    for source in selected:
        manifests.append(
            download_source(
                source=source,
                output_root=(
                    args.output_dir
                ),
                expected_by_surah=(
                    expected_by_surah
                ),
                canonical_texts=(
                    canonical_texts
                ),
            )
        )

    root_manifest = {
        "snapshot_type": (
            "surahapp-scholarly-sources"
        ),
        "built_at": (
            datetime.now(UTC)
            .isoformat()
        ),
        "source_count": (
            len(manifests)
        ),
        "total_record_count": sum(
            int(
                manifest[
                    "record_count"
                ]
            )
            for manifest
            in manifests
        ),
        "sources": [
            {
                "source_id": (
                    manifest["source_id"]
                ),
                "source_slug": (
                    manifest[
                        "source_slug"
                    ]
                ),
                "title": (
                    manifest["title"]
                ),
                "role": (
                    manifest["role"]
                ),
                "coverage_mode": (
                    manifest[
                        "coverage_mode"
                    ]
                ),
                "record_count": (
                    manifest[
                        "record_count"
                    ]
                ),
                "corpus_sha256": (
                    manifest[
                        "corpus_sha256"
                    ]
                ),
            }
            for manifest in manifests
        ],
    }

    write_json(
        args.output_dir
        / "snapshot-manifest.json",
        root_manifest,
    )

    print()
    print("=" * 88)
    print(
        "SURAH APP SNAPSHOT: PASS"
    )
    print("=" * 88)

    for manifest in manifests:
        print(
            manifest["source_slug"],
            "→",
            manifest["record_count"],
            "records",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
