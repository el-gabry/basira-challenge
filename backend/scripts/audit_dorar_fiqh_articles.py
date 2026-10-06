from __future__ import annotations

import hashlib
import json
from pathlib import Path

from basira.competition.dorar_fiqh import (
    parse_dorar_fiqh_article,
)


ROOT = Path(__file__).resolve().parents[1]

ARTICLE_DIR = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dorar-fiqh"
    / "articles"
)

OUT = (
    ROOT
    / "data"
    / "competition"
    / "audits"
    / "fiqh"
    / "dorar-fiqh-adversarial-v1.json"
)


CASES = {
    "comparative": {
        "path":
            ARTICLE_DIR
            / "comparative.html",

        "url":
            "https://dorar.net/feqhia/424",

        "require_disagreement":
            True,

        "minimum_positions":
            2,

        "expected_positions":
            2,

        "expected_ordinals":
            [1, 2],

        "require_position_citations":
            True,

        "expected_madhhabs_by_ordinal": {
            1: ["hanafi", "maliki"],
            2: ["shafii", "hanbali"],
        },
    },

    "single": {
        "path":
            ARTICLE_DIR
            / "single.html",

        "url":
            "https://dorar.net/feqhia/435",

        "require_disagreement":
            False,

        "minimum_positions":
            0,
    },
}


def main() -> None:

    reports = []
    failures = []

    for case_id, config in (
        CASES.items()
    ):
        path = config["path"]

        raw = path.read_bytes()

        html = raw.decode(
            "utf-8",
            errors="replace",
        )

        article = (
            parse_dorar_fiqh_article(
                html=html,
                canonical_url=(
                    config["url"]
                ),
            )
        )

        report = {
            "case_id":
                case_id,

            "source_id":
                article.source_id,

            "url":
                article.canonical_url,

            "response_sha256":
                hashlib.sha256(
                    raw
                ).hexdigest(),

            "title":
                article.article_title,

            "explicit_disagreement":
                article.explicit_disagreement,

            "explicit_consensus_language":
                article.explicit_consensus_language,

            "position_count":
                len(
                    article.positions
                ),

            "positions": [
                {
                    "ordinal":
                        p.ordinal,

                    "madhhabs": [
                        m.value
                        for m in p.madhhabs
                    ],

                    "citation_count":
                        len(
                            p.citations
                        ),

                    "citations":
                        list(
                            p.citations
                        ),

                    "text_preview":
                        p.text[:1000],
                }
                for p
                in article.positions
            ],
        }

        if (
            config[
                "require_disagreement"
            ]
            and not article
            .explicit_disagreement
        ):
            failures.append(
                f"{case_id}: "
                "explicit disagreement lost"
            )

        if (
            len(article.positions)
            < config[
                "minimum_positions"
            ]
        ):
            failures.append(
                f"{case_id}: "
                "too few positions extracted"
            )

        expected_positions = config.get(
            "expected_positions"
        )

        if (
            expected_positions is not None
            and len(article.positions)
            != expected_positions
        ):
            failures.append(
                f"{case_id}: expected exactly "
                f"{expected_positions} positions; "
                f"got {len(article.positions)}"
            )

        expected_ordinals = config.get(
            "expected_ordinals"
        )

        actual_ordinals = [
            item.ordinal
            for item in article.positions
        ]

        if (
            expected_ordinals is not None
            and actual_ordinals
            != expected_ordinals
        ):
            failures.append(
                f"{case_id}: expected ordinals "
                f"{expected_ordinals}; "
                f"got {actual_ordinals}"
            )

        if config.get(
            "require_position_citations"
        ):
            for position in article.positions:
                if not position.citations:
                    failures.append(
                        f"{case_id}: position "
                        f"{position.ordinal} "
                        "has no extracted citations"
                    )

        expected_madhhabs = config.get(
            "expected_madhhabs_by_ordinal",
            {},
        )

        for position in article.positions:
            expected = expected_madhhabs.get(
                position.ordinal
            )

            if expected is None:
                continue

            actual = sorted(
                madhhab.value
                for madhhab
                in position.madhhabs
            )

            if actual != sorted(expected):
                failures.append(
                    f"{case_id}: position "
                    f"{position.ordinal} "
                    f"expected madhhabs "
                    f"{sorted(expected)}; "
                    f"got {actual}"
                )

        reports.append(
            report
        )

    comparative = reports[0]

    # --------------------------------------------------------
    # Safety:
    # no auto-tarjih output is created by this adapter.
    # It extracts source structure only.
    # --------------------------------------------------------

    result = {
        "audit_id":
            "dorar-fiqh-adversarial-v1",

        "provider":
            "Dorar al-Sunniyyah",

        "source_family":
            "DORAR_FIQH",

        "checks": {
            "canonical_article_capture":
                "PASS",

            "disagreement_preserved":
                (
                    "PASS"
                    if (
                        comparative[
                            "explicit_disagreement"
                        ]
                        and comparative[
                            "position_count"
                        ] >= 2
                    )
                    else "FAIL"
                ),

            "automated_tarjih":
                "PROHIBITED",

            "majority_vote":
                "PROHIBITED",

            "consensus_inference_from_madhhab_count":
                "PROHIBITED",

            "personal_fatwa":
                "PROHIBITED",
        },

        "cases":
            reports,

        "failures":
            failures,

        "result":
            (
                "PASS"
                if not failures
                else "FAIL"
            ),

        "runtime_admission":
            "PENDING_SOURCE_PASSPORT",
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        "Comparative disagreement:",
        comparative[
            "explicit_disagreement"
        ],
    )

    print(
        "Comparative positions:",
        comparative[
            "position_count"
        ],
    )

    for position in (
        comparative["positions"]
    ):
        print(
            " position",
            position["ordinal"],
            "| madhhabs:",
            ",".join(
                position["madhhabs"]
            )
            or "unspecified",
            "| citations:",
            position[
                "citation_count"
            ],
        )

    print()
    print(
        "Automated tarjih: PROHIBITED"
    )

    print(
        "Consensus from counts: PROHIBITED"
    )

    print()
    print(
        "FIQH ADVERSARIAL AUDIT:",
        result["result"],
    )

    if failures:
        for failure in failures:
            print(
                "FAIL:",
                failure,
            )

        raise SystemExit(1)


if __name__ == "__main__":
    main()
