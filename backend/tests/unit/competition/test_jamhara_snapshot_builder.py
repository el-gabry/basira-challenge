from __future__ import annotations

from basira.competition.jamhara_snapshot import (
    build_jamhara_snapshot,
    canonical_json_bytes,
    discover_language_routes,
    discover_word_ids,
    merge_characterized_word_ids,
    sha256_bytes,
)

SEED_A = b"""
<a href="/dictionary/word/4892">
x
</a>
<a href="/dictionary/word/2704/ar">
x
</a>
"""

SEED_B = b"""
<a href="/dictionary/word/2704/en">
x
</a>
<a href="/dictionary/word/2204">
x
</a>
"""


DEFAULT_2704 = b"""
<a href="/dictionary/word/2704/en">
English
</a>
<a href="/dictionary/word/2704/ar">
Arabic
</a>
"""

DEFAULT_4892 = b"""
<a href="/dictionary/word/4892/en">
English
</a>
"""

DEFAULT_2204 = b"""
<a href="/dictionary/word/2204/en">
English
</a>
"""


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
    <h5>
      من موسوعة المصطلحات الإسلامية
    </h5>
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
    <h5>
      من موسوعة المصطلحات الإسلامية
    </h5>
    <div>
      <h2>التعريف</h2>
      <p>Moving meaning to another language.</p>
    </div>
  </div>
</div>
</body>
</html>
""".encode()


RICH_4892_EN = """
<html>
<head>
<title>
معنى : Islamic advocacy - الدعوة الإسلامية - الجمهرة
</title>
</head>
<body>
<div class="entry-main-content">
  <div>
    <h5>
      من موسوعة المصطلحات الإسلامية
    </h5>
    <div>
      <h2>التعريف</h2>
      <p>Conveying the message of Islam.</p>
    </div>
  </div>
</div>
</body>
</html>
""".encode()


EMPTY_2204_EN = b"""
<html>
<head>
<title>
\xd9\x85\xd8\xb9\xd9\x86\xd9\x89 :
- \xd8\xa8\xd9\x8a\xd8\xa7\xd9\x86
- \xd8\xa7\xd9\x84\xd8\xac\xd9\x85\xd9\x87\xd8\xb1\xd8\xa9
</title>
</head>
<body></body>
</html>
"""


def test_seed_discovery_is_sorted_and_deduplicated() -> None:
    ids, languages = (
        discover_word_ids(
            [
                SEED_A,
                SEED_B,
            ]
        )
    )

    assert ids == [
        2204,
        2704,
        4892,
    ]

    assert languages == {
        2704: [
            "ar",
            "en",
        ],
    }


def test_language_routes_are_sorted_unique() -> None:
    routes = (
        discover_language_routes(
            DEFAULT_2704,
            word_id=2704,
        )
    )

    assert routes == [
        "ar",
        "en",
    ]


def test_snapshot_builder_is_deterministic_and_fail_closed() -> None:
    documents = {
        (
            "https://islamic-content.com/"
            "dictionary/word/2204"
        ): DEFAULT_2204,
        (
            "https://islamic-content.com/"
            "dictionary/word/2204/en"
        ): EMPTY_2204_EN,
        (
            "https://islamic-content.com/"
            "dictionary/word/2704"
        ): DEFAULT_2704,
        (
            "https://islamic-content.com/"
            "dictionary/word/2704/ar"
        ): RICH_2704_AR,
        (
            "https://islamic-content.com/"
            "dictionary/word/2704/en"
        ): RICH_2704_EN,
        (
            "https://islamic-content.com/"
            "dictionary/word/4892"
        ): DEFAULT_4892,
        (
            "https://islamic-content.com/"
            "dictionary/word/4892/en"
        ): RICH_4892_EN,
    }

    def fetch(url: str) -> bytes:
        return documents[url]

    first_snapshot, first_report = (
        build_jamhara_snapshot(
            fetch=fetch,
            word_ids=[
                4892,
                2204,
                2704,
            ],
        )
    )

    second_snapshot, second_report = (
        build_jamhara_snapshot(
            fetch=fetch,
            word_ids=[
                2704,
                4892,
                2204,
            ],
        )
    )

    assert (
        canonical_json_bytes(
            first_snapshot
        )
        == canonical_json_bytes(
            second_snapshot
        )
    )

    assert (
        first_report[
            "snapshot_sha256"
        ]
        == second_report[
            "snapshot_sha256"
        ]
    )

    identities = [
        (
            unit["word_id"],
            unit["language"],
        )
        for unit in first_snapshot[
            "units"
        ]
    ]

    assert identities == [
        (2704, "ar"),
        (2704, "en"),
        (4892, "en"),
    ]

    assert (
        first_report[
            "rejected_view_count"
        ]
        == 1
    )

    assert (
        first_report[
            "fetch_failure_count"
        ]
        == 0
    )


def test_snapshot_hash_is_hash_of_canonical_snapshot_bytes() -> None:
    documents = {
        (
            "https://islamic-content.com/"
            "dictionary/word/4892"
        ): DEFAULT_4892,
        (
            "https://islamic-content.com/"
            "dictionary/word/4892/en"
        ): RICH_4892_EN,
    }

    def fetch(url: str) -> bytes:
        return documents[url]

    snapshot, report = (
        build_jamhara_snapshot(
            fetch=fetch,
            word_ids=[4892],
        )
    )

    assert (
        report["snapshot_sha256"]
        == sha256_bytes(
            canonical_json_bytes(
                snapshot
            )
        )
    )


def test_dynamic_html_bytes_do_not_change_semantic_snapshot() -> None:
    default_a = b"""
    <html>
      <script nonce="capture-a"></script>
      <a href="/dictionary/word/4892/en">
        English
      </a>
    </html>
    """

    default_b = b"""
    <html>
      <script nonce="capture-b"></script>
      <a href="/dictionary/word/4892/en">
        English
      </a>
    </html>
    """

    localized_a = """
    <html>
    <head>
      <title>
        معنى : Islamic advocacy - الدعوة الإسلامية - الجمهرة
      </title>
      <script nonce="capture-a">
        window.dynamic = "A";
      </script>
    </head>
    <body>
      <div class="entry-main-content">
        <div>
          <h5>
            من موسوعة المصطلحات الإسلامية
          </h5>
          <div>
            <h2>التعريف</h2>
            <p>
              Conveying the message of Islam.
            </p>
          </div>
        </div>
      </div>
    </body>
    </html>
    """.encode()

    localized_b = """
    <html>
    <head>
      <title>
        معنى : Islamic advocacy - الدعوة الإسلامية - الجمهرة
      </title>
      <script nonce="capture-b">
        window.dynamic = "B";
      </script>
    </head>
    <body>
      <div class="entry-main-content">
        <div>
          <h5>
            من موسوعة المصطلحات الإسلامية
          </h5>
          <div>
            <h2>التعريف</h2>
            <p>
              Conveying the message of Islam.
            </p>
          </div>
        </div>
      </div>
    </body>
    </html>
    """.encode()

    url_default = (
        "https://islamic-content.com/"
        "dictionary/word/4892"
    )

    url_en = (
        "https://islamic-content.com/"
        "dictionary/word/4892/en"
    )

    documents_a = {
        url_default: default_a,
        url_en: localized_a,
    }

    documents_b = {
        url_default: default_b,
        url_en: localized_b,
    }

    def fetch_a(url: str) -> bytes:
        return documents_a[url]

    def fetch_b(url: str) -> bytes:
        return documents_b[url]

    snapshot_a, report_a = (
        build_jamhara_snapshot(
            fetch=fetch_a,
            word_ids=[4892],
        )
    )

    snapshot_b, report_b = (
        build_jamhara_snapshot(
            fetch=fetch_b,
            word_ids=[4892],
        )
    )

    assert (
        canonical_json_bytes(
            snapshot_a
        )
        == canonical_json_bytes(
            snapshot_b
        )
    )

    assert (
        report_a["snapshot_sha256"]
        == report_b["snapshot_sha256"]
    )

    evidence_a = report_a[
        "accepted_response_evidence"
    ][0]

    evidence_b = report_b[
        "accepted_response_evidence"
    ][0]

    assert (
        evidence_a["response_sha256"]
        != evidence_b["response_sha256"]
    )

    assert (
        evidence_a["content_sha256"]
        == evidence_b["content_sha256"]
    )

    unit = snapshot_a["units"][0]

    assert "response_sha256" not in unit

    assert (
        unit["content_sha256"]
        == evidence_a["content_sha256"]
    )



def test_characterized_ids_complete_seed_candidate_universe() -> None:
    seed_ids = [
        2,
        1197,
        2704,
        12382,
    ]

    result = (
        merge_characterized_word_ids(
            seed_ids
        )
    )

    assert result == [
        2,
        1197,
        2704,
        4892,
        12382,
    ]
