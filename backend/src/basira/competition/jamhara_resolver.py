from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
import unicodedata
from html import unescape
from pathlib import Path

import httpx

from basira.competition.jamhara import (
    jamhara_source_url,
    parse_jamhara_word_page,
    validate_jamhara_response_url,
)
from basira.competition.jamhara_snapshot import (
    canonical_json_bytes,
    sha256_bytes,
)
from basira.competition.jamhara_warm_cache import (
    cache_path_for_url,
)

_ARABIC_MARKS = re.compile(
    "["
    "\u0610-\u061a"
    "\u064b-\u065f"
    "\u0670"
    "\u06d6-\u06ed"
    "]"
)

_TITLE = re.compile(
    r"<title[^>]*>(.*?)</title>",
    flags=re.I | re.S,
)

_TAGS = re.compile(
    r"<[^>]+>"
)

_JAMHARA_TITLE = re.compile(
    r"^معنى\s*:\s*"
    r"(.*?)"
    r"\s*-\s*"
    r"(.*?)"
    r"\s*-\s*"
    r"الجمهرة$"
)


def normalize_term(
    value: str,
) -> str:
    value = unicodedata.normalize(
        "NFKC",
        value,
    )

    value = value.replace(
        "\u0640",
        "",
    )

    value = _ARABIC_MARKS.sub(
        "",
        value,
    )

    chars: list[str] = []

    for char in value.casefold():
        if (
            char.isalnum()
            or char.isspace()
        ):
            chars.append(char)
        else:
            chars.append(" ")

    return " ".join(
        "".join(chars).split()
    )


def extract_title_terms(
    raw: bytes,
) -> list[str]:
    html = raw.decode(
        "utf-8",
        errors="replace",
    )

    match = _TITLE.search(
        html
    )

    if not match:
        return []

    title = unescape(
        _TAGS.sub(
            " ",
            match.group(1),
        )
    )

    title = " ".join(
        title.split()
    )

    parsed = _JAMHARA_TITLE.fullmatch(
        title
    )

    if not parsed:
        return []

    values = []

    for value in (
        parsed.group(1),
        parsed.group(2),
    ):
        value = " ".join(
            value.split()
        ).strip()

        if (
            not value
            or value == "-"
        ):
            continue

        if value not in values:
            values.append(
                value
            )

    return values


class SemanticStore:
    def __init__(
        self,
        path: Path,
    ) -> None:
        self.path = path

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = (
            sqlite3.connect(
                path,
                timeout=5.0,
            )
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS units (
                word_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                status TEXT NOT NULL,
                response_sha256 TEXT NOT NULL,
                content_sha256 TEXT,
                unit_json TEXT,
                updated_at REAL NOT NULL,
                PRIMARY KEY (
                    word_id,
                    language
                )
            )
            """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS terms (
                word_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                normalized_term TEXT NOT NULL,
                display_term TEXT NOT NULL,
                PRIMARY KEY (
                    word_id,
                    language,
                    normalized_term
                )
            )
            """
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def commit(self) -> None:
        self.connection.commit()

    def add_term(
        self,
        *,
        word_id: int,
        language: str,
        value: str,
    ) -> None:
        normalized = normalize_term(
            value
        )

        if not normalized:
            return

        self.connection.execute(
            """
            INSERT INTO terms (
                word_id,
                language,
                normalized_term,
                display_term
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT DO UPDATE SET
                display_term = excluded.display_term
            """,
            (
                word_id,
                language,
                normalized,
                value,
            ),
        )

    def cached_unit(
        self,
        *,
        word_id: int,
        language: str,
        response_sha256: str,
    ) -> tuple[
        bool,
        dict[str, object] | None,
    ]:
        row = self.connection.execute(
            """
            SELECT
                status,
                unit_json
            FROM units
            WHERE
                word_id = ?
                AND language = ?
                AND response_sha256 = ?
            """,
            (
                word_id,
                language,
                response_sha256,
            ),
        ).fetchone()

        if row is None:
            return (
                False,
                None,
            )

        status, unit_json = row

        if status != "usable":
            return (
                True,
                None,
            )

        assert unit_json is not None

        return (
            True,
            json.loads(
                unit_json
            ),
        )

    def store_parse_result(
        self,
        *,
        word_id: int,
        language: str,
        response_sha256: str,
        unit: dict[str, object] | None,
    ) -> dict[str, object] | None:
        if unit is None:
            self.connection.execute(
                """
                INSERT INTO units (
                    word_id,
                    language,
                    status,
                    response_sha256,
                    content_sha256,
                    unit_json,
                    updated_at
                )
                VALUES (?, ?, 'unavailable', ?, NULL, NULL, ?)
                ON CONFLICT (
                    word_id,
                    language
                )
                DO UPDATE SET
                    status = excluded.status,
                    response_sha256 = excluded.response_sha256,
                    content_sha256 = NULL,
                    unit_json = NULL,
                    updated_at = excluded.updated_at
                """,
                (
                    word_id,
                    language,
                    response_sha256,
                    time.time(),
                ),
            )

            return None

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

        unit[
            "content_sha256"
        ] = content_sha256

        unit_json = (
            canonical_json_bytes(
                unit
            ).decode("utf-8")
        )

        self.connection.execute(
            """
            INSERT INTO units (
                word_id,
                language,
                status,
                response_sha256,
                content_sha256,
                unit_json,
                updated_at
            )
            VALUES (?, ?, 'usable', ?, ?, ?, ?)
            ON CONFLICT (
                word_id,
                language
            )
            DO UPDATE SET
                status = excluded.status,
                response_sha256 = excluded.response_sha256,
                content_sha256 = excluded.content_sha256,
                unit_json = excluded.unit_json,
                updated_at = excluded.updated_at
            """,
            (
                word_id,
                language,
                response_sha256,
                content_sha256,
                unit_json,
                time.time(),
            ),
        )

        for field in (
            "localized_term",
            "canonical_arabic_term",
        ):
            value = unit.get(
                field
            )

            if isinstance(
                value,
                str,
            ):
                self.add_term(
                    word_id=word_id,
                    language=language,
                    value=value,
                )

        return unit

    def search_word_ids(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[int]:
        normalized = normalize_term(
            query
        )

        if not normalized:
            return []

        rows = self.connection.execute(
            """
            SELECT
                word_id,
                normalized_term
            FROM terms
            WHERE
                normalized_term = ?
                OR normalized_term LIKE ?
                OR normalized_term LIKE ?
            """,
            (
                normalized,
                f"{normalized}%",
                f"%{normalized}%",
            ),
        ).fetchall()

        ranked = sorted(
            rows,
            key=lambda row: (
                0
                if row[1] == normalized
                else (
                    1
                    if row[1].startswith(
                        normalized
                    )
                    else 2
                ),
                len(row[1]),
                row[0],
            ),
        )

        result = []

        for word_id, _term in ranked:
            if word_id not in result:
                result.append(
                    int(word_id)
                )

            if len(result) >= limit:
                break

        return result

    def metadata_float(
        self,
        key: str,
    ) -> float:
        row = self.connection.execute(
            """
            SELECT value
            FROM metadata
            WHERE key = ?
            """,
            (key,),
        ).fetchone()

        if row is None:
            return 0.0

        return float(
            row[0]
        )

    def set_metadata_float(
        self,
        key: str,
        value: float,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO metadata (
                key,
                value
            )
            VALUES (?, ?)
            ON CONFLICT(key)
            DO UPDATE SET
                value = excluded.value
            """,
            (
                key,
                repr(value),
            ),
        )


def _parse_cached_raw(
    *,
    store: SemanticStore,
    raw: bytes,
    word_id: int,
    language: str,
) -> dict[str, object] | None:
    response_sha256 = (
        sha256_bytes(
            raw
        )
    )

    (
        cached,
        cached_unit,
    ) = store.cached_unit(
        word_id=word_id,
        language=language,
        response_sha256=(
            response_sha256
        ),
    )

    if cached:
        return cached_unit

    unit = parse_jamhara_word_page(
        raw.decode(
            "utf-8",
            errors="replace",
        ),
        word_id=word_id,
        language=language,
    )

    return store.store_parse_result(
        word_id=word_id,
        language=language,
        response_sha256=(
            response_sha256
        ),
        unit=unit,
    )


def refresh_index_from_warmer(
    *,
    raw_cache_dir: Path,
    warmer_state_db: Path,
    store: SemanticStore,
) -> int:
    if not warmer_state_db.exists():
        return 0

    last_seen = (
        store.metadata_float(
            "warmer_last_updated_at"
        )
    )

    ledger = sqlite3.connect(
        warmer_state_db,
        timeout=5.0,
    )

    try:
        rows = ledger.execute(
            """
            SELECT
                url,
                word_id,
                language,
                kind,
                updated_at
            FROM warm_jobs
            WHERE
                status = 'done'
                AND updated_at > ?
            ORDER BY
                updated_at ASC,
                url ASC
            """,
            (last_seen,),
        ).fetchall()
    finally:
        ledger.close()

    indexed = 0
    max_seen = last_seen

    for (
        url,
        word_id,
        language,
        kind,
        updated_at,
    ) in rows:
        max_seen = max(
            max_seen,
            float(updated_at),
        )

        path = cache_path_for_url(
            raw_cache_dir,
            str(url),
        )

        if not path.exists():
            continue

        raw = path.read_bytes()

        if kind == "default":
            for term in (
                extract_title_terms(
                    raw
                )
            ):
                store.add_term(
                    word_id=int(
                        word_id
                    ),
                    language="",
                    value=term,
                )

            indexed += 1
            continue

        if (
            kind == "localized"
            and language
        ):
            _parse_cached_raw(
                store=store,
                raw=raw,
                word_id=int(
                    word_id
                ),
                language=str(
                    language
                ),
            )

            indexed += 1

    store.set_metadata_float(
        "warmer_last_updated_at",
        max_seen,
    )

    store.commit()

    return indexed


def resolve_word(
    *,
    word_id: int,
    language: str,
    raw_cache_dir: Path,
    store: SemanticStore,
    allow_network: bool = True,
    refresh: bool = False,
    timeout_seconds: float = 12.0,
) -> dict[str, object] | None:
    url = jamhara_source_url(
        word_id,
        language,
    )

    path = cache_path_for_url(
        raw_cache_dir,
        url,
    )

    raw: bytes | None = None

    if (
        path.exists()
        and not refresh
    ):
        raw = path.read_bytes()

    elif allow_network:
        raw_cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        response = httpx.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "BasiraCompetitionResolver/"
                    "1.0"
                ),
                "Accept": (
                    "text/html,"
                    "application/xhtml+xml"
                ),
            },
            timeout=timeout_seconds,
            follow_redirects=True,
        )

        response.raise_for_status()

        validate_jamhara_response_url(
            url,
            str(response.url),
        )

        raw = response.content

        tmp = path.with_suffix(
            ".tmp"
        )

        tmp.write_bytes(raw)
        tmp.replace(path)

    if raw is None:
        return None

    unit = _parse_cached_raw(
        store=store,
        raw=raw,
        word_id=word_id,
        language=language,
    )

    store.commit()

    return unit


def resolve_term(
    *,
    query: str,
    language: str,
    raw_cache_dir: Path,
    warmer_state_db: Path,
    store: SemanticStore,
    allow_network: bool = True,
) -> dict[str, object] | None:
    refresh_index_from_warmer(
        raw_cache_dir=raw_cache_dir,
        warmer_state_db=(
            warmer_state_db
        ),
        store=store,
    )

    candidates = (
        store.search_word_ids(
            query,
            limit=10,
        )
    )

    for word_id in candidates:
        unit = resolve_word(
            word_id=word_id,
            language=language,
            raw_cache_dir=(
                raw_cache_dir
            ),
            store=store,
            allow_network=(
                allow_network
            ),
        )

        if unit is not None:
            return {
                "query": query,
                "requested_language": (
                    language
                ),
                "resolved_language": (
                    language
                ),
                "fallback_to_arabic": (
                    False
                ),
                "unit": unit,
            }

        if language != "ar":
            arabic = resolve_word(
                word_id=word_id,
                language="ar",
                raw_cache_dir=(
                    raw_cache_dir
                ),
                store=store,
                allow_network=(
                    allow_network
                ),
            )

            if arabic is not None:
                return {
                    "query": query,
                    "requested_language": (
                        language
                    ),
                    "resolved_language": (
                        "ar"
                    ),
                    "fallback_to_arabic": (
                        True
                    ),
                    "unit": arabic,
                }

    return None


def main() -> int:
    home = Path.home()

    parser = argparse.ArgumentParser()

    group = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    group.add_argument(
        "--word-id",
        type=int,
    )

    group.add_argument(
        "--query",
        type=str,
    )

    parser.add_argument(
        "--language",
        default="en",
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=(
            home
            / ".cache"
            / "basira"
            / "jamhara-full-abfac30-v1"
        ),
    )

    parser.add_argument(
        "--warmer-state-db",
        type=Path,
        default=(
            home
            / ".cache"
            / "basira"
            / "jamhara-warmer-v1.sqlite3"
        ),
    )

    parser.add_argument(
        "--semantic-db",
        type=Path,
        default=(
            home
            / ".cache"
            / "basira"
            / "jamhara-semantic-v1.sqlite3"
        ),
    )

    parser.add_argument(
        "--offline",
        action="store_true",
    )

    args = parser.parse_args()

    store = SemanticStore(
        args.semantic_db
    )

    try:
        refresh_index_from_warmer(
            raw_cache_dir=(
                args.cache_dir
            ),
            warmer_state_db=(
                args.warmer_state_db
            ),
            store=store,
        )

        if args.word_id is not None:
            result = resolve_word(
                word_id=args.word_id,
                language=args.language,
                raw_cache_dir=(
                    args.cache_dir
                ),
                store=store,
                allow_network=(
                    not args.offline
                ),
            )
        else:
            assert args.query is not None

            result = resolve_term(
                query=args.query,
                language=args.language,
                raw_cache_dir=(
                    args.cache_dir
                ),
                warmer_state_db=(
                    args.warmer_state_db
                ),
                store=store,
                allow_network=(
                    not args.offline
                ),
            )

        if result is None:
            print(
                json.dumps(
                    {
                        "status": (
                            "UNAVAILABLE"
                        )
                    },
                    indent=2,
                )
            )

            return 3

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
