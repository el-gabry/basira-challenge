from __future__ import annotations

import sqlite3
from pathlib import Path

from basira.competition.jamhara import (
    jamhara_source_url,
)
from basira.competition.jamhara_resolver import (
    SemanticStore,
    extract_title_terms,
    normalize_term,
    refresh_index_from_warmer,
    resolve_term,
    resolve_word,
)
from basira.competition.jamhara_warm_cache import (
    cache_path_for_url,
)

DEFAULT_2704 = """
<html>
<head>
<title>
معنى : التَّرْجَمَة - الترجمة - الجمهرة
</title>
</head>
<body></body>
</html>
""".encode()


RICH_2704_AR = """
<html>
<head>
<title>
معنى : التَّرْجَمَة - الترجمة - الجمهرة
</title>
</head>
<body>
<div class="entry-main-content">
<div>
<h5>من موسوعة المصطلحات الإسلامية</h5>
<div>
<h2>التعريف</h2>
<p>نقل الكلام من لغة إلى أخرى.</p>
</div>
</div>
</div>
</body>
</html>
""".encode()


RICH_2704_EN = """
<html>
<head>
<title>
معنى : Translation - الترجمة - الجمهرة
</title>
</head>
<body>
<div class="entry-main-content">
<div>
<h5>من موسوعة المصطلحات الإسلامية</h5>
<div>
<h2>التعريف</h2>
<p>Moving meaning to another language.</p>
</div>
</div>
</div>
</body>
</html>
""".encode()


EMPTY_2704_EN = """
<html>
<head>
<title>
معنى : - الترجمة - الجمهرة
</title>
</head>
<body></body>
</html>
""".encode()


def write_raw(
    cache: Path,
    url: str,
    raw: bytes,
) -> None:
    cache.mkdir(
        parents=True,
        exist_ok=True,
    )

    cache_path_for_url(
        cache,
        url,
    ).write_bytes(
        raw
    )


def make_ledger(
    path: Path,
    rows: list[
        tuple[
            str,
            int,
            str | None,
            str,
            float,
        ]
    ],
) -> None:
    con = sqlite3.connect(
        path
    )

    con.execute(
        """
        CREATE TABLE warm_jobs (
            url TEXT PRIMARY KEY,
            word_id INTEGER NOT NULL,
            language TEXT,
            kind TEXT NOT NULL,
            priority INTEGER NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL,
            response_sha256 TEXT,
            last_error TEXT,
            updated_at REAL NOT NULL
        )
        """
    )

    for (
        url,
        word_id,
        language,
        kind,
        updated_at,
    ) in rows:
        con.execute(
            """
            INSERT INTO warm_jobs (
                url,
                word_id,
                language,
                kind,
                priority,
                status,
                attempts,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, 0,
                'done', 0, ?
            )
            """,
            (
                url,
                word_id,
                language,
                kind,
                updated_at,
            ),
        )

    con.commit()
    con.close()


def test_normalize_arabic_term() -> None:
    assert (
        normalize_term(
            "التَّرْجَمَة"
        )
        == "الترجمة"
    )


def test_extract_default_title_terms() -> None:
    assert extract_title_terms(
        DEFAULT_2704
    ) == [
        "التَّرْجَمَة",
        "الترجمة",
    ]


def test_cached_word_resolution_is_offline(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "raw"
    db = tmp_path / "semantic.sqlite3"

    url = jamhara_source_url(
        2704,
        "en",
    )

    write_raw(
        cache,
        url,
        RICH_2704_EN,
    )

    store = SemanticStore(db)

    try:
        unit = resolve_word(
            word_id=2704,
            language="en",
            raw_cache_dir=cache,
            store=store,
            allow_network=False,
        )

        assert unit is not None

        assert (
            unit["localized_term"]
            == "Translation"
        )

        assert unit[
            "content_sha256"
        ]
    finally:
        store.close()


def test_warmer_ledger_builds_term_index(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "raw"
    state = tmp_path / "warmer.sqlite3"
    semantic = (
        tmp_path
        / "semantic.sqlite3"
    )

    default_url = (
        "https://islamic-content.com/"
        "dictionary/word/2704"
    )

    en_url = jamhara_source_url(
        2704,
        "en",
    )

    write_raw(
        cache,
        default_url,
        DEFAULT_2704,
    )

    write_raw(
        cache,
        en_url,
        RICH_2704_EN,
    )

    make_ledger(
        state,
        [
            (
                default_url,
                2704,
                None,
                "default",
                1.0,
            ),
            (
                en_url,
                2704,
                "en",
                "localized",
                2.0,
            ),
        ],
    )

    store = SemanticStore(
        semantic
    )

    try:
        indexed = (
            refresh_index_from_warmer(
                raw_cache_dir=cache,
                warmer_state_db=state,
                store=store,
            )
        )

        assert indexed == 2

        assert (
            store.search_word_ids(
                "الترجمة"
            )
            == [2704]
        )

        assert (
            store.search_word_ids(
                "Translation"
            )
            == [2704]
        )
    finally:
        store.close()


def test_term_resolution_falls_back_to_arabic(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "raw"
    state = tmp_path / "warmer.sqlite3"
    semantic = (
        tmp_path
        / "semantic.sqlite3"
    )

    default_url = (
        "https://islamic-content.com/"
        "dictionary/word/2704"
    )

    en_url = jamhara_source_url(
        2704,
        "en",
    )

    ar_url = jamhara_source_url(
        2704,
        "ar",
    )

    write_raw(
        cache,
        default_url,
        DEFAULT_2704,
    )

    write_raw(
        cache,
        en_url,
        EMPTY_2704_EN,
    )

    write_raw(
        cache,
        ar_url,
        RICH_2704_AR,
    )

    make_ledger(
        state,
        [
            (
                default_url,
                2704,
                None,
                "default",
                1.0,
            )
        ],
    )

    store = SemanticStore(
        semantic
    )

    try:
        result = resolve_term(
            query="الترجمة",
            language="en",
            raw_cache_dir=cache,
            warmer_state_db=state,
            store=store,
            allow_network=False,
        )

        assert result is not None

        assert (
            result[
                "resolved_language"
            ]
            == "ar"
        )

        assert (
            result[
                "fallback_to_arabic"
            ]
            is True
        )

        assert (
            result["unit"][
                "localized_term"
            ]
            == "التَّرْجَمَة"
        )
    finally:
        store.close()
