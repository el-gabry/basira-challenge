from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.retrieval.arabic_query import (
    normalize_arabic_search_text,
)
from basira.sources.shamela.hierarchy import (
    ShamelaBookHierarchy,
)

_SCHEMA_VERSION = "1"

_DEFAULT_WINDOW_SIZE = 192
_DEFAULT_WINDOW_OVERLAP = 32

_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u0621-\u064a]+")

_STOPWORDS = frozenset(
    {
        "ما",
        "ماذا",
        "هل",
        "في",
        "من",
        "عن",
        "على",
        "الى",
        "إلى",
        "هو",
        "هي",
        "هذا",
        "هذه",
        "لماذا",
        "كيف",
        "معنى",
        "معني",
        "شرح",
        "يقول",
        "قال",
        "الاسلام",
        "الإسلام",
        "what",
        "why",
        "how",
        "does",
        "do",
        "is",
        "are",
        "the",
        "a",
        "an",
        "in",
        "of",
        "about",
        "say",
        "says",
        "meaning",
        "explain",
        "islam",
        "islamic",
    }
)


def _normalized(
    value: str,
) -> str:
    return normalize_arabic_search_text(value).casefold()


def _tokens(
    value: str,
) -> tuple[str, ...]:
    normalized = _normalized(value)

    return tuple(
        token
        for token in _TOKEN_RE.findall(normalized)
        if len(token) > 1 and token not in _STOPWORDS
    )


def _fts_match_query(
    value: str,
) -> str | None:
    terms = tuple(dict.fromkeys(_tokens(value)))

    if not terms:
        return None

    return " OR ".join(f'"{term}"' for term in terms)


def _fingerprint(
    hierarchies: Iterable[ShamelaBookHierarchy],
) -> str:
    digest = hashlib.sha256()

    ordered = sorted(
        hierarchies,
        key=lambda item: (
            item.book.source_id,
            item.book.book_id,
        ),
    )

    for hierarchy in ordered:
        book = hierarchy.book

        for value in (
            book.source_id,
            book.source_version,
            book.source_snapshot_id,
            book.source_snapshot_sha256,
            book.book_id,
            book.raw_book_sha256,
        ):
            digest.update(value.encode("utf-8"))
            digest.update(b"\0")

        for span in sorted(
            hierarchy.spans,
            key=lambda item: (
                item.ordinal,
                item.span_id,
            ),
        ):
            digest.update(span.span_id.encode("utf-8"))
            digest.update(b"\0")
            digest.update(span.raw_text_sha256.encode("ascii"))
            digest.update(b"\n")

    return digest.hexdigest()


def _index_fingerprint(
    *,
    corpus_fingerprint: str,
    window_size: int,
    window_overlap: int,
) -> str:
    digest = hashlib.sha256()

    digest.update(corpus_fingerprint.encode("ascii"))

    digest.update(b"\0")

    digest.update(str(window_size).encode("ascii"))

    digest.update(b"\0")

    digest.update(str(window_overlap).encode("ascii"))

    return digest.hexdigest()


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaFtsHit:
    passage: ScholarlyPassage

    score: float

    matched_window_id: str

    token_start: int

    token_end: int


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaFtsStats:
    passage_count: int

    window_count: int

    book_count: int

    corpus_fingerprint: str

    index_fingerprint: str

    window_size: int

    window_overlap: int


class ShamelaFtsIndex:
    """
    Persistent FTS5 retrieval index over governed
    Shamela evidence.

    Canonical evidence and retrieval windows are kept
    separate:

    * passages are stable source-derived evidence;
    * windows are disposable ranking artifacts;
    * search always collapses windows back to the
      original parent ScholarlyPassage.

    The SQLite database is an index artifact, never
    the source of religious truth or canonical text.
    """

    def __init__(
        self,
        path: Path,
    ) -> None:
        self.path = Path(path)

        if not self.path.is_file():
            raise ValueError(f"Shamela FTS index does not exist: {self.path}")

        self._validate()

    @classmethod
    def build(
        cls,
        path: Path,
        hierarchies: Iterable[ShamelaBookHierarchy],
        *,
        window_size: int = (_DEFAULT_WINDOW_SIZE),
        window_overlap: int = (_DEFAULT_WINDOW_OVERLAP),
    ) -> ShamelaFtsIndex:
        if window_size <= 0:
            raise ValueError("window_size must be positive")

        if window_overlap < 0:
            raise ValueError("window_overlap cannot be negative")

        if window_overlap >= window_size:
            raise ValueError("window_overlap must be smaller than window_size")

        items = tuple(hierarchies)

        if not items:
            raise ValueError("At least one Shamela hierarchy is required")

        path = Path(path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp = path.with_suffix(path.suffix + ".tmp")

        temp.unlink(missing_ok=True)

        corpus_fp = _fingerprint(items)

        index_fp = _index_fingerprint(
            corpus_fingerprint=(corpus_fp),
            window_size=window_size,
            window_overlap=(window_overlap),
        )

        connection = sqlite3.connect(temp)

        try:
            connection.execute("PRAGMA foreign_keys = ON")

            connection.execute("PRAGMA journal_mode = OFF")

            connection.execute("PRAGMA synchronous = OFF")

            cls._create_schema(connection)

            passage_ids: set[str] = set()

            passage_count = 0
            window_count = 0

            stride = window_size - window_overlap

            ordered = sorted(
                items,
                key=lambda item: (
                    item.book.source_id,
                    item.book.book_id,
                ),
            )

            for hierarchy in ordered:
                spans = sorted(
                    hierarchy.spans,
                    key=lambda item: (
                        item.ordinal,
                        item.span_id,
                    ),
                )

                for span in spans:
                    passage = hierarchy.to_scholarly_passage(span.span_id)

                    if passage.passage_id in passage_ids:
                        raise ValueError(f"Duplicate passage ID: {passage.passage_id}")

                    passage_ids.add(passage.passage_id)

                    context = hierarchy.context_envelope(span.span_id)

                    title_context = " ".join(
                        (
                            passage.work_title,
                            *context.ancestor_titles,
                            passage.author_name or "",
                        )
                    )

                    madhhab = passage.metadata.get("madhhab")

                    cursor = connection.execute(
                        """
                            INSERT INTO passages (
                                passage_id,
                                source_id,
                                source_version,
                                domain,
                                work_id,
                                work_title,
                                author_name,
                                institution,
                                publisher,
                                source_url,
                                section_title,
                                chapter_title,
                                volume,
                                page,
                                madhhab,
                                raw_text,
                                metadata_json
                            )
                            VALUES (
                                ?, ?, ?, ?, ?, ?, ?,
                                ?, ?, ?, ?, ?, ?, ?,
                                ?, ?, ?
                            )
                            """,
                        (
                            passage.passage_id,
                            passage.source_id,
                            passage.source_version,
                            passage.domain.value,
                            passage.work_id,
                            passage.work_title,
                            passage.author_name,
                            passage.institution,
                            passage.publisher,
                            passage.source_url,
                            passage.section_title,
                            passage.chapter_title,
                            passage.volume,
                            passage.page,
                            madhhab,
                            passage.text,
                            json.dumps(
                                passage.metadata,
                                ensure_ascii=False,
                                sort_keys=True,
                            ),
                        ),
                    )

                    passage_rowid = cursor.lastrowid

                    passage_count += 1

                    body_tokens = _tokens(passage.text)

                    title_search = _normalized(title_context)

                    if body_tokens:
                        start = 0

                        while start < len(body_tokens):
                            end = min(
                                start + window_size,
                                len(body_tokens),
                            )

                            window_tokens = body_tokens[start:end]

                            body_search = " ".join(window_tokens)

                            window_id = f"{passage.passage_id}:w:{start}:{end}"

                            connection.execute(
                                """
                                INSERT INTO retrieval_windows (
                                    window_id,
                                    passage_rowid,
                                    token_start,
                                    token_end,
                                    body_search,
                                    title_search
                                )
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    window_id,
                                    passage_rowid,
                                    start,
                                    end,
                                    body_search,
                                    title_search,
                                ),
                            )

                            window_count += 1

                            if end >= len(body_tokens):
                                break

                            start += stride

                    elif title_search:
                        window_id = f"{passage.passage_id}:w:0:0"

                        connection.execute(
                            """
                            INSERT INTO retrieval_windows (
                                window_id,
                                passage_rowid,
                                token_start,
                                token_end,
                                body_search,
                                title_search
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                window_id,
                                passage_rowid,
                                0,
                                0,
                                "",
                                title_search,
                            ),
                        )

                        window_count += 1

            connection.execute(
                """
                INSERT INTO retrieval_windows_fts(
                    retrieval_windows_fts
                )
                VALUES ('rebuild')
                """
            )

            meta = {
                "schema_version": (_SCHEMA_VERSION),
                "passage_count": str(passage_count),
                "window_count": str(window_count),
                "book_count": str(len(items)),
                "corpus_fingerprint": (corpus_fp),
                "index_fingerprint": (index_fp),
                "window_size": str(window_size),
                "window_overlap": str(window_overlap),
            }

            connection.executemany(
                """
                INSERT INTO index_meta(
                    key,
                    value
                )
                VALUES (?, ?)
                """,
                tuple(meta.items()),
            )

            connection.commit()

            check = connection.execute("PRAGMA integrity_check").fetchone()

            if check is None or check[0] != "ok":
                raise ValueError("SQLite integrity_check failed")

        finally:
            connection.close()

        temp.replace(path)

        return cls(path)

    @staticmethod
    def _create_schema(
        connection: sqlite3.Connection,
    ) -> None:
        connection.executescript(
            """
            CREATE TABLE index_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE passages (
                rowid INTEGER PRIMARY KEY,
                passage_id TEXT NOT NULL UNIQUE,
                source_id TEXT NOT NULL,
                source_version TEXT,
                domain TEXT NOT NULL,
                work_id TEXT,
                work_title TEXT NOT NULL,
                author_name TEXT,
                institution TEXT,
                publisher TEXT,
                source_url TEXT,
                section_title TEXT,
                chapter_title TEXT,
                volume TEXT,
                page TEXT,
                madhhab TEXT,
                raw_text TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );

            CREATE INDEX passages_domain_idx
                ON passages(domain);

            CREATE INDEX passages_madhhab_idx
                ON passages(madhhab);

            CREATE INDEX passages_work_idx
                ON passages(work_id);

            CREATE TABLE retrieval_windows (
                rowid INTEGER PRIMARY KEY,
                window_id TEXT NOT NULL UNIQUE,
                passage_rowid INTEGER NOT NULL,
                token_start INTEGER NOT NULL,
                token_end INTEGER NOT NULL,
                body_search TEXT NOT NULL,
                title_search TEXT NOT NULL,
                FOREIGN KEY(passage_rowid)
                    REFERENCES passages(rowid)
                    ON DELETE CASCADE
            );

            CREATE INDEX windows_parent_idx
                ON retrieval_windows(
                    passage_rowid
                );

            CREATE VIRTUAL TABLE retrieval_windows_fts
            USING fts5(
                body_search,
                title_search,
                content='retrieval_windows',
                content_rowid='rowid',
                tokenize='unicode61'
            );
            """
        )

    def _validate(
        self,
    ) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row

            check = connection.execute("PRAGMA quick_check").fetchone()

            if check is None or check[0] != "ok":
                raise ValueError("Invalid Shamela FTS database")

            meta = dict(
                connection.execute(
                    """
                    SELECT key, value
                    FROM index_meta
                    """
                ).fetchall()
            )

            if meta.get("schema_version") != _SCHEMA_VERSION:
                raise ValueError("Unsupported Shamela FTS schema version")

            passage_count = connection.execute(
                """
                    SELECT COUNT(*)
                    FROM passages
                    """
            ).fetchone()[0]

            window_count = connection.execute(
                """
                    SELECT COUNT(*)
                    FROM retrieval_windows
                    """
            ).fetchone()[0]

            if passage_count != int(meta["passage_count"]):
                raise ValueError("Passage-count metadata mismatch")

            if window_count != int(meta["window_count"]):
                raise ValueError("Window-count metadata mismatch")

    @property
    def stats(
        self,
    ) -> ShamelaFtsStats:
        with sqlite3.connect(self.path) as connection:
            meta = dict(
                connection.execute(
                    """
                    SELECT key, value
                    FROM index_meta
                    """
                ).fetchall()
            )

        return ShamelaFtsStats(
            passage_count=int(meta["passage_count"]),
            window_count=int(meta["window_count"]),
            book_count=int(meta["book_count"]),
            corpus_fingerprint=(meta["corpus_fingerprint"]),
            index_fingerprint=(meta["index_fingerprint"]),
            window_size=int(meta["window_size"]),
            window_overlap=int(meta["window_overlap"]),
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        domains: tuple[
            ScholarlyDomain,
            ...,
        ] = (),
        madhhabs: tuple[
            str,
            ...,
        ] = (),
        excluded_madhhabs: tuple[
            str,
            ...,
        ] = (),
        book_ids: tuple[
            str,
            ...,
        ] = (),
    ) -> tuple[
        ShamelaFtsHit,
        ...,
    ]:
        if limit <= 0:
            return ()

        match_query = _fts_match_query(query)

        if match_query is None:
            return ()

        conditions = ["retrieval_windows_fts MATCH ?"]

        params: list[object] = [match_query]

        if domains:
            placeholders = ", ".join("?" for _ in domains)

            conditions.append(f"p.domain IN ({placeholders})")

            params.extend(domain.value for domain in domains)

        if madhhabs:
            placeholders = ", ".join("?" for _ in madhhabs)

            conditions.append(f"p.madhhab IN ({placeholders})")

            params.extend(madhhabs)

        if excluded_madhhabs:
            placeholders = ", ".join("?" for _ in excluded_madhhabs)

            conditions.append(
                f"(p.madhhab IS NULL OR p.madhhab NOT IN ({placeholders}))"
            )

            params.extend(excluded_madhhabs)

        if book_ids:
            placeholders = ", ".join("?" for _ in book_ids)

            conditions.append(f"p.work_id IN ({placeholders})")

            params.extend(book_ids)

        overfetch = max(
            limit * 8,
            40,
        )

        params.append(overfetch)

        sql = f"""
            SELECT
                p.*,
                w.window_id,
                w.token_start,
                w.token_end,
                bm25(
                    retrieval_windows_fts,
                    1.0,
                    2.5
                ) AS rank_score
            FROM retrieval_windows_fts
            JOIN retrieval_windows AS w
              ON w.rowid =
                 retrieval_windows_fts.rowid
            JOIN passages AS p
              ON p.rowid =
                 w.passage_rowid
            WHERE {" AND ".join(conditions)}
            ORDER BY
                rank_score ASC,
                p.passage_id ASC,
                w.token_start ASC
            LIMIT ?
        """

        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row

            rows = connection.execute(
                sql,
                params,
            ).fetchall()

        hits = []

        seen_passages: set[str] = set()

        for row in rows:
            passage_id = row["passage_id"]

            if passage_id in seen_passages:
                continue

            seen_passages.add(passage_id)

            metadata = json.loads(row["metadata_json"])

            passage = ScholarlyPassage(
                passage_id=passage_id,
                source_id=row["source_id"],
                domain=(ScholarlyDomain(row["domain"])),
                work_id=row["work_id"],
                work_title=row["work_title"],
                text=row["raw_text"],
                author_name=row["author_name"],
                institution=row["institution"],
                publisher=row["publisher"],
                source_version=row["source_version"],
                source_url=row["source_url"],
                section_title=row["section_title"],
                chapter_title=row["chapter_title"],
                volume=row["volume"],
                page=row["page"],
                metadata=metadata,
            )

            hits.append(
                ShamelaFtsHit(
                    passage=passage,
                    score=-float(row["rank_score"]),
                    matched_window_id=(row["window_id"]),
                    token_start=int(row["token_start"]),
                    token_end=int(row["token_end"]),
                )
            )

            if len(hits) >= limit:
                break

        return tuple(hits)
