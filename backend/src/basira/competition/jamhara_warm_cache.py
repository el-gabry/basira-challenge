from __future__ import annotations

import argparse
import asyncio
import hashlib
import sqlite3
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import httpx

from basira.competition.jamhara import (
    BASE_URL,
    jamhara_source_url,
)
from basira.competition.jamhara_snapshot import (
    SEED_URLS,
    CachedHTTPFetcher,
    discover_language_routes,
    discover_word_ids,
    merge_characterized_word_ids,
)

DEFAULT_CONCURRENCY = 12
DEFAULT_TIMEOUT_SECONDS = 25.0
DEFAULT_RETRIES = 3


@dataclass(frozen=True)
class WarmJob:
    url: str
    word_id: int
    language: str | None
    kind: str
    priority: int


def cache_path_for_url(
    cache_dir: Path,
    url: str,
) -> Path:
    digest = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()

    return (
        cache_dir
        / f"{digest}.html"
    )


class WarmLedger:
    def __init__(
        self,
        path: Path,
    ) -> None:
        self.path = path

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = sqlite3.connect(
            self.path
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS warm_jobs (
                url TEXT PRIMARY KEY,
                word_id INTEGER NOT NULL,
                language TEXT,
                kind TEXT NOT NULL,
                priority INTEGER NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                response_sha256 TEXT,
                last_error TEXT,
                updated_at REAL NOT NULL
            )
            """
        )

        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def upsert_job(
        self,
        job: WarmJob,
    ) -> None:
        self.connection.execute(
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
            VALUES (?, ?, ?, ?, ?, 'pending', 0, ?)
            ON CONFLICT(url) DO UPDATE SET
                word_id = excluded.word_id,
                language = excluded.language,
                kind = excluded.kind,
                priority = excluded.priority
            """,
            (
                job.url,
                job.word_id,
                job.language,
                job.kind,
                job.priority,
                time.time(),
            ),
        )

    def mark_done(
        self,
        job: WarmJob,
        response_sha256: str,
    ) -> None:
        self.connection.execute(
            """
            UPDATE warm_jobs
            SET
                status = 'done',
                attempts = attempts + 1,
                response_sha256 = ?,
                last_error = NULL,
                updated_at = ?
            WHERE url = ?
            """,
            (
                response_sha256,
                time.time(),
                job.url,
            ),
        )

    def mark_cached(
        self,
        job: WarmJob,
        response_sha256: str,
    ) -> None:
        self.connection.execute(
            """
            UPDATE warm_jobs
            SET
                status = 'done',
                response_sha256 = ?,
                last_error = NULL,
                updated_at = ?
            WHERE url = ?
            """,
            (
                response_sha256,
                time.time(),
                job.url,
            ),
        )

    def mark_failed(
        self,
        job: WarmJob,
        error: str,
    ) -> None:
        self.connection.execute(
            """
            UPDATE warm_jobs
            SET
                status = 'failed',
                attempts = attempts + 1,
                last_error = ?,
                updated_at = ?
            WHERE url = ?
            """,
            (
                error,
                time.time(),
                job.url,
            ),
        )

    def commit(self) -> None:
        self.connection.commit()

    def counts(
        self,
    ) -> dict[str, int]:
        rows = self.connection.execute(
            """
            SELECT status, COUNT(*)
            FROM warm_jobs
            GROUP BY status
            """
        ).fetchall()

        result = {
            "pending": 0,
            "done": 0,
            "failed": 0,
        }

        for status, count in rows:
            result[str(status)] = int(count)

        return result


def sha256_bytes(
    raw: bytes,
) -> str:
    return hashlib.sha256(
        raw
    ).hexdigest()


def default_jobs(
    word_ids: Iterable[int],
) -> list[WarmJob]:
    return [
        WarmJob(
            url=(
                f"{BASE_URL}/dictionary/"
                f"word/{word_id}"
            ),
            word_id=word_id,
            language=None,
            kind="default",
            priority=0,
        )
        for word_id in sorted(
            set(word_ids)
        )
    ]


def localized_jobs(
    word_id: int,
    languages: Iterable[str],
) -> list[WarmJob]:
    unique = sorted(
        set(languages),
        key=lambda language: (
            0
            if language in {
                "ar",
                "en",
            }
            else 1,
            language,
        ),
    )

    jobs = []

    for language in unique:
        priority = (
            10
            if language in {
                "ar",
                "en",
            }
            else 20
        )

        jobs.append(
            WarmJob(
                url=jamhara_source_url(
                    word_id,
                    language,
                ),
                word_id=word_id,
                language=language,
                kind="localized",
                priority=priority,
            )
        )

    return jobs


async def fetch_job(
    *,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    cache_dir: Path,
    ledger: WarmLedger,
    job: WarmJob,
    retries: int,
) -> tuple[
    WarmJob,
    str,
]:
    path = cache_path_for_url(
        cache_dir,
        job.url,
    )

    if path.exists():
        raw = path.read_bytes()

        ledger.mark_cached(
            job,
            sha256_bytes(raw),
        )

        return (
            job,
            "cached",
        )

    last_error: (
        Exception | None
    ) = None

    async with semaphore:
        for attempt in range(
            1,
            retries + 1,
        ):
            try:
                response = await client.get(
                    job.url
                )

                response.raise_for_status()

                raw = response.content

                tmp = path.with_suffix(
                    ".tmp"
                )

                tmp.write_bytes(raw)
                tmp.replace(path)

                ledger.mark_done(
                    job,
                    sha256_bytes(raw),
                )

                return (
                    job,
                    "downloaded",
                )

            except (
                httpx.HTTPError,
                OSError,
            ) as exc:
                last_error = exc

                if attempt < retries:
                    await asyncio.sleep(
                        min(
                            float(attempt),
                            3.0,
                        )
                    )

    ledger.mark_failed(
        job,
        repr(last_error),
    )

    return (
        job,
        "failed",
    )


async def warm_jobs(
    *,
    jobs: list[WarmJob],
    cache_dir: Path,
    ledger: WarmLedger,
    concurrency: int,
    timeout_seconds: float,
    retries: int,
    label: str,
) -> dict[str, int]:
    cache_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for job in jobs:
        ledger.upsert_job(job)

    ledger.commit()

    semaphore = asyncio.Semaphore(
        concurrency
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "BasiraCompetitionCacheWarmer/"
            "1.0"
        ),
        "Accept": (
            "text/html,"
            "application/xhtml+xml"
        ),
    }

    timeout = httpx.Timeout(
        timeout_seconds
    )

    completed = 0
    downloaded = 0
    cached = 0
    failed = 0

    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
        limits=httpx.Limits(
            max_connections=concurrency,
            max_keepalive_connections=(
                concurrency
            ),
        ),
    ) as client:
        tasks = [
            asyncio.create_task(
                fetch_job(
                    client=client,
                    semaphore=semaphore,
                    cache_dir=cache_dir,
                    ledger=ledger,
                    job=job,
                    retries=retries,
                )
            )
            for job in jobs
        ]

        total = len(tasks)

        for task in asyncio.as_completed(
            tasks
        ):
            _job, status = await task

            completed += 1

            if status == "downloaded":
                downloaded += 1
            elif status == "cached":
                cached += 1
            else:
                failed += 1

            if (
                completed % 100 == 0
                or completed == total
            ):
                ledger.commit()

                print(
                    f"[{label}] "
                    f"{completed}/{total} "
                    f"downloaded={downloaded} "
                    f"cached={cached} "
                    f"failed={failed}",
                    flush=True,
                )

    ledger.commit()

    return {
        "total": len(jobs),
        "downloaded": downloaded,
        "cached": cached,
        "failed": failed,
    }


def candidate_word_ids(
    cache_dir: Path,
) -> list[int]:
    fetch = CachedHTTPFetcher(
        cache_dir,
        delay_seconds=0,
    )

    seed_documents = [
        fetch(url)
        for url in SEED_URLS
    ]

    ids, _ = discover_word_ids(
        seed_documents
    )

    return merge_characterized_word_ids(
        ids
    )


def localized_jobs_from_cache(
    *,
    cache_dir: Path,
    word_ids: Iterable[int],
) -> tuple[
    list[WarmJob],
    list[int],
]:
    jobs: list[WarmJob] = []
    missing_defaults: list[int] = []

    for word_id in word_ids:
        url = (
            f"{BASE_URL}/dictionary/"
            f"word/{word_id}"
        )

        path = cache_path_for_url(
            cache_dir,
            url,
        )

        if not path.exists():
            missing_defaults.append(
                word_id
            )
            continue

        raw = path.read_bytes()

        languages = (
            discover_language_routes(
                raw,
                word_id=word_id,
            )
        )

        jobs.extend(
            localized_jobs(
                word_id,
                languages,
            )
        )

    jobs = sorted(
        {
            job.url: job
            for job in jobs
        }.values(),
        key=lambda job: (
            job.priority,
            job.word_id,
            job.language or "",
        ),
    )

    return (
        jobs,
        missing_defaults,
    )


async def run(
    *,
    cache_dir: Path,
    state_db: Path,
    concurrency: int,
    timeout_seconds: float,
    retries: int,
) -> int:
    ledger = WarmLedger(
        state_db
    )

    try:
        word_ids = candidate_word_ids(
            cache_dir
        )

        if len(word_ids) != 4382:
            raise RuntimeError(
                "unexpected Jamhara "
                "candidate count: "
                f"{len(word_ids)}"
            )

        print(
            "candidate_count =",
            len(word_ids),
            flush=True,
        )

        defaults = default_jobs(
            word_ids
        )

        default_result = await warm_jobs(
            jobs=defaults,
            cache_dir=cache_dir,
            ledger=ledger,
            concurrency=concurrency,
            timeout_seconds=(
                timeout_seconds
            ),
            retries=retries,
            label="default",
        )

        print(
            "default_result =",
            default_result,
            flush=True,
        )

        (
            localized,
            missing_defaults,
        ) = localized_jobs_from_cache(
            cache_dir=cache_dir,
            word_ids=word_ids,
        )

        if missing_defaults:
            print(
                "missing_default_pages =",
                len(missing_defaults),
                flush=True,
            )

        print(
            "localized_job_count =",
            len(localized),
            flush=True,
        )

        core = [
            job
            for job in localized
            if job.language
            in {
                "ar",
                "en",
            }
        ]

        other = [
            job
            for job in localized
            if job.language
            not in {
                "ar",
                "en",
            }
        ]

        core_result = await warm_jobs(
            jobs=core,
            cache_dir=cache_dir,
            ledger=ledger,
            concurrency=concurrency,
            timeout_seconds=(
                timeout_seconds
            ),
            retries=retries,
            label="core-ar-en",
        )

        print(
            "core_result =",
            core_result,
            flush=True,
        )

        other_result = await warm_jobs(
            jobs=other,
            cache_dir=cache_dir,
            ledger=ledger,
            concurrency=concurrency,
            timeout_seconds=(
                timeout_seconds
            ),
            retries=retries,
            label="other-languages",
        )

        print(
            "other_result =",
            other_result,
            flush=True,
        )

        counts = ledger.counts()

        print(
            "ledger_counts =",
            counts,
            flush=True,
        )

        failed = (
            default_result["failed"]
            + core_result["failed"]
            + other_result["failed"]
        )

        return (
            0
            if failed == 0
            else 2
        )

    finally:
        ledger.close()


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--cache-dir",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--state-db",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
    )

    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
    )

    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
    )

    args = parser.parse_args()

    if not (
        1
        <= args.concurrency
        <= 32
    ):
        raise SystemExit(
            "concurrency must be 1..32"
        )

    return asyncio.run(
        run(
            cache_dir=args.cache_dir,
            state_db=args.state_db,
            concurrency=args.concurrency,
            timeout_seconds=(
                args.timeout_seconds
            ),
            retries=args.retries,
        )
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
