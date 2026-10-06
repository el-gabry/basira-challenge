from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path
from urllib.error import HTTPError, URLError

from basira.competition.jamhara import (
    BASE_URL,
    SOURCE_FAMILY,
    canonicalize_jamhara_units,
    jamhara_source_url,
    parse_jamhara_word_page,
)

SEED_URLS = (
    f"{BASE_URL}/dictionary/term/1",
    f"{BASE_URL}/dictionary/term/428",
)


CHARACTERIZED_WORD_IDS = (
    1197,
    2704,
    4892,
)


WORD_ROUTE_RE = re.compile(
    r"""href=["']"""
    r"""(?:https?://[^/"']+)?"""
    r"""/dictionary/word/"""
    r"""(\d+)"""
    r"""(?:/([a-z]{2}))?"""
    r"""(?:["'?#/])""",
    flags=re.I,
)

LANGUAGE_ROUTE_TEMPLATE = (
    r"/dictionary/word/{word_id}/"
    r"([a-z]{{2}})"
)


Fetch = Callable[
    [str],
    bytes,
]


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def canonical_json_bytes(
    value: object,
) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def discover_word_ids(
    seed_documents: Iterable[
        bytes
    ],
) -> tuple[
    list[int],
    dict[int, list[str]],
]:
    word_ids: set[int] = set()

    explicit_languages: dict[
        int,
        set[str],
    ] = {}

    for raw in seed_documents:
        html = raw.decode(
            "utf-8",
            errors="replace",
        )

        for match in (
            WORD_ROUTE_RE.finditer(
                html
            )
        ):
            word_id = int(
                match.group(1)
            )

            word_ids.add(
                word_id
            )

            language = (
                match.group(2)
            )

            if language:
                explicit_languages.setdefault(
                    word_id,
                    set(),
                ).add(
                    language.lower()
                )

    return (
        sorted(word_ids),
        {
            word_id: sorted(
                languages
            )
            for word_id, languages
            in sorted(
                explicit_languages.items()
            )
        },
    )


def discover_language_routes(
    raw: bytes,
    *,
    word_id: int,
) -> list[str]:
    html = raw.decode(
        "utf-8",
        errors="replace",
    )

    pattern = (
        LANGUAGE_ROUTE_TEMPLATE.format(
            word_id=word_id
        )
    )

    return sorted(
        {
            language.lower()
            for language in re.findall(
                pattern,
                html,
                flags=re.I,
            )
        }
    )


class CachedHTTPFetcher:
    def __init__(
        self,
        cache_dir: Path,
        *,
        delay_seconds: float = 0.2,
        retries: int = 3,
        timeout_seconds: float = 25.0,
    ) -> None:
        self.cache_dir = cache_dir
        self.delay_seconds = (
            delay_seconds
        )
        self.retries = retries
        self.timeout_seconds = (
            timeout_seconds
        )

        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _cache_path(
        self,
        url: str,
    ) -> Path:
        key = hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()

        return (
            self.cache_dir
            / f"{key}.html"
        )

    def __call__(
        self,
        url: str,
    ) -> bytes:
        cache_path = (
            self._cache_path(
                url
            )
        )

        if cache_path.exists():
            return cache_path.read_bytes()

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "BasiraCompetitionSnapshot/"
                "1.0"
            ),
            "Accept": (
                "text/html,"
                "application/xhtml+xml"
            ),
        }

        last_error: (
            Exception | None
        ) = None

        for attempt in range(
            1,
            self.retries + 1,
        ):
            request = (
                urllib.request.Request(
                    url,
                    headers=headers,
                )
            )

            try:
                with urllib.request.urlopen(
                    request,
                    timeout=(
                        self.timeout_seconds
                    ),
                ) as response:
                    raw = (
                        response.read()
                    )

                cache_path.write_bytes(
                    raw
                )

                if (
                    self.delay_seconds
                    > 0
                ):
                    time.sleep(
                        self.delay_seconds
                    )

                return raw

            except (
                HTTPError,
                URLError,
                TimeoutError,
            ) as exc:
                last_error = exc

                if (
                    attempt
                    < self.retries
                ):
                    time.sleep(
                        float(attempt)
                    )

        raise RuntimeError(
            f"failed to fetch {url!r}"
        ) from last_error




def merge_characterized_word_ids(
    word_ids: Iterable[int],
) -> list[int]:
    return sorted(
        set(word_ids)
        | set(
            CHARACTERIZED_WORD_IDS
        )
    )

def _normalize_word_ids(
    word_ids: Iterable[int],
) -> list[int]:
    normalized = sorted(
        set(word_ids)
    )

    if not normalized:
        raise ValueError(
            "word_ids cannot be empty"
        )

    if any(
        word_id <= 0
        for word_id in normalized
    ):
        raise ValueError(
            "word_ids must be positive"
        )

    return normalized


def build_jamhara_snapshot(
    *,
    fetch: Fetch,
    word_ids: (
        Iterable[int] | None
    ) = None,
) -> tuple[
    dict[str, object],
    dict[str, object],
]:
    seed_hashes: dict[
        str,
        str,
    ] = {}

    if word_ids is None:
        seed_documents = []

        for seed_url in SEED_URLS:
            raw = fetch(
                seed_url
            )

            seed_documents.append(
                raw
            )

            seed_hashes[
                seed_url
            ] = sha256_bytes(
                raw
            )

        (
            candidates,
            seed_explicit_languages,
        ) = discover_word_ids(
            seed_documents
        )

        candidates = (
            merge_characterized_word_ids(
                candidates
            )
        )

        candidate_scope = (
            "SEED_DISCOVERED_PLUS_CHARACTERIZED"
        )

    else:
        candidates = (
            _normalize_word_ids(
                word_ids
            )
        )

        seed_explicit_languages = {}
        candidate_scope = (
            "EXPLICIT_WORD_IDS"
        )

    if not candidates:
        raise RuntimeError(
            "no Jamhara candidates discovered"
        )

    candidate_bytes = (
        "".join(
            f"{word_id}\n"
            for word_id in candidates
        )
    ).encode("utf-8")

    candidate_sha256 = (
        sha256_bytes(
            candidate_bytes
        )
    )

    accepted_units: list[
        dict[str, object]
    ] = []

    accepted_response_evidence: list[
        dict[str, object]
    ] = []

    rejected_views: list[
        dict[str, object]
    ] = []

    fetch_failures: list[
        dict[str, object]
    ] = []

    route_inventory: dict[
        str,
        int,
    ] = {}

    attempted_view_count = 0

    for ordinal, word_id in enumerate(
        candidates,
        1,
    ):
        default_url = (
            f"{BASE_URL}/dictionary/"
            f"word/{word_id}"
        )

        try:
            default_raw = fetch(
                default_url
            )
        except RuntimeError as exc:
            fetch_failures.append(
                {
                    "word_id": word_id,
                    "language": None,
                    "url": default_url,
                    "phase": (
                        "LANGUAGE_ROUTE_DISCOVERY"
                    ),
                    "error": str(exc),
                }
            )
            continue

        languages = set(
            discover_language_routes(
                default_raw,
                word_id=word_id,
            )
        )

        languages.update(
            seed_explicit_languages.get(
                word_id,
                [],
            )
        )

        for language in sorted(
            languages
        ):
            route_inventory[
                language
            ] = (
                route_inventory.get(
                    language,
                    0,
                )
                + 1
            )

            attempted_view_count += 1

            url = jamhara_source_url(
                word_id,
                language,
            )

            try:
                raw = fetch(
                    url
                )
            except RuntimeError as exc:
                fetch_failures.append(
                    {
                        "word_id": word_id,
                        "language": language,
                        "url": url,
                        "phase": (
                            "LOCALIZED_VIEW"
                        ),
                        "error": str(exc),
                    }
                )
                continue

            html = raw.decode(
                "utf-8",
                errors="replace",
            )

            unit = (
                parse_jamhara_word_page(
                    html,
                    word_id=word_id,
                    language=language,
                )
            )

            if unit is None:
                rejected_views.append(
                    {
                        "word_id": word_id,
                        "language": language,
                        "source_url": url,
                        "response_sha256": (
                            sha256_bytes(
                                raw
                            )
                        ),
                        "reason": (
                            "NO_USABLE_LOCALIZED_"
                            "PAYLOAD"
                        ),
                    }
                )
                continue

            unit = dict(
                unit
            )

            content_sha256 = (
                sha256_bytes(
                    canonical_json_bytes(
                        unit
                    )
                )
            )

            accepted_response_evidence.append(
                {
                    "word_id": word_id,
                    "language": language,
                    "source_url": url,
                    "response_sha256": (
                        sha256_bytes(
                            raw
                        )
                    ),
                    "content_sha256": (
                        content_sha256
                    ),
                }
            )

            unit[
                "content_sha256"
            ] = content_sha256

            accepted_units.append(
                unit
            )

        print(
            f"[{ordinal}/{len(candidates)}] "
            f"word_id={word_id} "
            f"routes={len(languages)}",
            flush=True,
        )

    canonical_units = (
        canonicalize_jamhara_units(
            accepted_units
        )
    )

    snapshot: dict[
        str,
        object,
    ] = {
        "schema_version": 1,
        "snapshot_id": (
            "jamhara-terminology-"
            "units-v1"
        ),
        "source_family": (
            SOURCE_FAMILY
        ),
        "domain": (
            "translation_terminology"
        ),
        "candidate_scope": (
            candidate_scope
        ),
        "candidate_count": len(
            candidates
        ),
        "candidate_word_ids_sha256": (
            candidate_sha256
        ),
        "unit_identity": [
            "word_id",
            "language",
        ],
        "units": canonical_units,
        "source_role": {
            "terminology_authority": True,
            "universal_primary_evidence": False,
            "cross_domain_primary_evidence": False,
        },
        "runtime_state": {
            "runtime_admission": (
                "PENDING_AUDIT"
            ),
            "source_trust_passport": (
                "NOT_ISSUED"
            ),
        },
    }

    snapshot_raw = (
        canonical_json_bytes(
            snapshot
        )
    )

    accepted_language_counts: dict[
        str,
        int,
    ] = {}

    for unit in canonical_units:
        language = str(
            unit["language"]
        )

        accepted_language_counts[
            language
        ] = (
            accepted_language_counts.get(
                language,
                0,
            )
            + 1
        )

    report: dict[
        str,
        object,
    ] = {
        "schema_version": 1,
        "build_id": (
            "jamhara-terminology-"
            "snapshot-build-v1"
        ),
        "candidate_scope": (
            candidate_scope
        ),
        "seed_urls": list(
            SEED_URLS
        ),
        "seed_response_sha256": (
            seed_hashes
        ),
        "candidate_count": len(
            candidates
        ),
        "candidate_word_ids_sha256": (
            candidate_sha256
        ),
        "attempted_view_count": (
            attempted_view_count
        ),
        "accepted_unit_count": len(
            canonical_units
        ),
        "rejected_view_count": len(
            rejected_views
        ),
        "fetch_failure_count": len(
            fetch_failures
        ),
        "advertised_route_counts": dict(
            sorted(
                route_inventory.items()
            )
        ),
        "accepted_language_counts": dict(
            sorted(
                accepted_language_counts.items()
            )
        ),
        "accepted_response_evidence": (
            accepted_response_evidence
        ),
        "rejected_views": (
            rejected_views
        ),
        "fetch_failures": (
            fetch_failures
        ),
        "snapshot_sha256": (
            sha256_bytes(
                snapshot_raw
            )
        ),
        "complete_without_fetch_errors": (
            len(fetch_failures)
            == 0
        ),
        "runtime_admission": (
            "PENDING_AUDIT"
        ),
    }

    return (
        snapshot,
        report,
    )


def write_build(
    *,
    snapshot: dict[str, object],
    report: dict[str, object],
    output_path: Path,
    report_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(
        canonical_json_bytes(
            snapshot
        )
    )

    report_path.write_bytes(
        canonical_json_bytes(
            report
        )
    )


def _parse_word_ids(
    value: str,
) -> list[int]:
    return _normalize_word_ids(
        int(part.strip())
        for part in value.split(",")
        if part.strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--report",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=(
            Path.home()
            / ".cache"
            / "basira"
            / "jamhara-v1"
        ),
    )

    parser.add_argument(
        "--word-ids",
        type=str,
        default=None,
    )

    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.2,
    )

    args = parser.parse_args()

    fetch = CachedHTTPFetcher(
        args.cache_dir,
        delay_seconds=(
            args.delay_seconds
        ),
    )

    word_ids = (
        _parse_word_ids(
            args.word_ids
        )
        if args.word_ids
        else None
    )

    snapshot, report = (
        build_jamhara_snapshot(
            fetch=fetch,
            word_ids=word_ids,
        )
    )

    write_build(
        snapshot=snapshot,
        report=report,
        output_path=args.output,
        report_path=args.report,
    )

    print(
        json.dumps(
            {
                "candidate_count": (
                    report[
                        "candidate_count"
                    ]
                ),
                "attempted_view_count": (
                    report[
                        "attempted_view_count"
                    ]
                ),
                "accepted_unit_count": (
                    report[
                        "accepted_unit_count"
                    ]
                ),
                "rejected_view_count": (
                    report[
                        "rejected_view_count"
                    ]
                ),
                "fetch_failure_count": (
                    report[
                        "fetch_failure_count"
                    ]
                ),
                "snapshot_sha256": (
                    report[
                        "snapshot_sha256"
                    ]
                ),
            },
            indent=2,
        )
    )

    if (
        report[
            "fetch_failure_count"
        ]
        != 0
    ):
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
