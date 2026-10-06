from __future__ import annotations

from pathlib import Path

from basira.competition.jamhara_warm_cache import (
    WarmJob,
    cache_path_for_url,
    default_jobs,
    localized_jobs,
)


def test_cache_path_matches_url_hash_contract(
    tmp_path: Path,
) -> None:
    url = (
        "https://islamic-content.com/"
        "dictionary/word/2704/en"
    )

    first = cache_path_for_url(
        tmp_path,
        url,
    )

    second = cache_path_for_url(
        tmp_path,
        url,
    )

    assert first == second

    assert first.parent == tmp_path

    assert (
        first.suffix
        == ".html"
    )


def test_default_jobs_are_sorted_and_unique() -> None:
    jobs = default_jobs(
        [
            4892,
            2704,
            2704,
            1197,
        ]
    )

    assert [
        job.word_id
        for job in jobs
    ] == [
        1197,
        2704,
        4892,
    ]

    assert all(
        job.kind == "default"
        for job in jobs
    )


def test_arabic_and_english_are_prioritized() -> None:
    jobs = localized_jobs(
        2704,
        [
            "ur",
            "en",
            "fr",
            "ar",
            "id",
            "en",
        ],
    )

    assert [
        job.language
        for job in jobs
    ] == [
        "ar",
        "en",
        "fr",
        "id",
        "ur",
    ]

    assert [
        job.priority
        for job in jobs
    ] == [
        10,
        10,
        20,
        20,
        20,
    ]


def test_warm_job_identity_is_url_based() -> None:
    job = WarmJob(
        url=(
            "https://islamic-content.com/"
            "dictionary/word/2704/en"
        ),
        word_id=2704,
        language="en",
        kind="localized",
        priority=10,
    )

    assert (
        job.word_id,
        job.language,
    ) == (
        2704,
        "en",
    )
