from __future__ import annotations

import hashlib
import json
from pathlib import Path

from basira.competition.dorar_aqeedah import (
    DorarAqeedahSourceNoteKind,
    parse_dorar_aqeedah_passage,
)


ROOT = Path(
    __file__
).resolve().parents[1]


RAW = (
    ROOT
    / "data/competition/discovery/"
    "dorar-aqeedah/raw/"
    "detailed_evidence.html"
)


DISCOVERY = (
    ROOT
    / "data/competition/discovery/"
    "dorar-aqeedah/"
    "discovery.json"
)


OUT = (
    ROOT
    / "data/competition/audits/"
    "aqeedah/"
    "dorar-aqeedah-adversarial-v1.json"
)


URL = (
    "https://dorar.net/aqeeda/420"
)


def check(
    condition: bool,
    name: str,
    failures: list[str],
) -> str:

    if condition:
        return "PASS"

    failures.append(
        name
    )

    return "FAIL"


def main() -> None:

    raw = RAW.read_bytes()

    response_sha256 = (
        hashlib.sha256(
            raw
        ).hexdigest()
    )

    discovery = json.loads(
        DISCOVERY.read_text(
            encoding="utf-8"
        )
    )

    expected_sha = (
        discovery[
            "cases"
        ][
            "detailed_evidence"
        ][
            "sha256"
        ]
    )

    if response_sha256 != expected_sha:
        raise SystemExit(
            "Captured Aqeedah artifact hash "
            "does not match characterization"
        )

    html = raw.decode(
        "utf-8",
        errors="replace",
    )

    passage = (
        parse_dorar_aqeedah_passage(
            html=html,
            canonical_url=URL,
        )
    )

    failures: list[str] = []

    hadith_notes = [
        note
        for note in passage.source_notes
        if (
            DorarAqeedahSourceNoteKind
            .HADITH_SOURCE_NOTE
            in note.kinds
        )
    ]

    grading_notes = [
        note
        for note in passage.source_notes
        if (
            DorarAqeedahSourceNoteKind
            .REPORTED_HADITH_GRADING
            in note.kinds
        )
    ]

    bibliographic_notes = [
        note
        for note in passage.source_notes
        if (
            DorarAqeedahSourceNoteKind
            .BIBLIOGRAPHIC_REFERENCE
            in note.kinds
        )
    ]

    all_quran_context_safe = all(
        item.canonical_quran_witness
        is False
        for item in passage.quran_contexts
    )

    no_forced_pairing = all(
        item.automatically_paired_to_context
        is False
        for item
        in passage.quran_references
    )

    all_notes_no_authority_promotion = all(
        note.aqeedah_authority_promotion
        is False
        for note
        in passage.source_notes
    )

    all_notes_no_independent_auth = all(
        note.independent_authenticity_judgment
        is False
        for note
        in passage.source_notes
    )

    ui_tokens = (
        "محتويات الصفحة",
        "الرابط المختصر",
        "انظر أيضا",
        "السابق",
        "التالي",
    )

    ui_leaks = [
        value
        for value in ui_tokens
        if value
        in passage.explanation_text
    ]

    checks = {
        "characterized_artifact_hash":
            check(
                response_sha256
                == expected_sha,

                "characterized_artifact_hash",

                failures,
            ),

        "canonical_root_exactly_one":
            check(
                passage.routing
                .canonical_root_count
                == 1,

                "canonical_root_exactly_one",

                failures,
            ),

        "direct_article_body_exactly_one":
            check(
                passage.routing
                .direct_article_body_count
                == 1,

                "direct_article_body_exactly_one",

                failures,
            ),

        "canonical_title":
            check(
                "مَسائِلُ الأسماءِ والصِّفاتِ"
                in passage.title,

                "canonical_title",

                failures,
            ),

        "ui_exclusion":
            check(
                not ui_leaks,

                "ui_exclusion",

                failures,
            ),

        "source_node_provenance":
            check(
                passage.routing
                .provenance_violation_count
                == 0,

                "source_node_provenance",

                failures,
            ),

        "quran_context_count":
            check(
                len(
                    passage.quran_contexts
                )
                == 5,

                "quran_context_count",

                failures,
            ),

        "quran_reference_count":
            check(
                len(
                    passage.quran_references
                )
                == 4,

                "quran_reference_count",

                failures,
            ),

        "source_note_count":
            check(
                len(
                    passage.source_notes
                )
                == 23,

                "source_note_count",

                failures,
            ),

        "quran_context_not_canonical_witness":
            check(
                all_quran_context_safe,

                "quran_context_not_canonical_witness",

                failures,
            ),

        "no_forced_quran_pairing":
            check(
                no_forced_pairing
                and (
                    len(
                        passage.quran_contexts
                    )
                    != len(
                        passage.quran_references
                    )
                ),

                "no_forced_quran_pairing",

                failures,
            ),

        "hadith_source_notes_preserved":
            check(
                len(
                    hadith_notes
                )
                >= 3,

                "hadith_source_notes_preserved",

                failures,
            ),

        "reported_grading_preserved":
            check(
                len(
                    grading_notes
                )
                >= 1,

                "reported_grading_preserved",

                failures,
            ),

        "bibliographic_references_preserved":
            check(
                len(
                    bibliographic_notes
                )
                >= 15,

                "bibliographic_references_preserved",

                failures,
            ),

        "bibliographic_authority_promotion":
            (
                "PROHIBITED"
                if all_notes_no_authority_promotion
                else "FAIL"
            ),

        "independent_hadith_authenticity":
            (
                "PROHIBITED"
                if all_notes_no_independent_auth
                else "FAIL"
            ),

        "hadith_matn_structural_extraction":
            (
                "NOT_SUPPORTED"
                if (
                    passage
                    .hadith_matn_structurally_extractable
                    is False
                )
                else "FAIL"
            ),

        "generic_shamela_fallback":
            "PROHIBITED",
    }

    if (
        checks[
            "bibliographic_authority_promotion"
        ]
        != "PROHIBITED"
    ):
        failures.append(
            "bibliographic_authority_promotion"
        )

    if (
        checks[
            "independent_hadith_authenticity"
        ]
        != "PROHIBITED"
    ):
        failures.append(
            "independent_hadith_authenticity"
        )

    if (
        checks[
            "hadith_matn_structural_extraction"
        ]
        != "NOT_SUPPORTED"
    ):
        failures.append(
            "hadith_matn_structural_extraction"
        )

    metrics = {
        "response_bytes":
            len(
                raw
            ),

        "response_sha256":
            response_sha256,

        "title_chars":
            len(
                passage.title
            ),

        "explanation_chars":
            len(
                passage.explanation_text
            ),

        "quran_context_count":
            len(
                passage.quran_contexts
            ),

        "quran_reference_count":
            len(
                passage.quran_references
            ),

        "source_note_count":
            len(
                passage.source_notes
            ),

        "hadith_source_note_count":
            len(
                hadith_notes
            ),

        "reported_hadith_grading_note_count":
            len(
                grading_notes
            ),

        "bibliographic_reference_note_count":
            len(
                bibliographic_notes
            ),

        "quran_context_text_node_count":
            (
                passage.routing
                .quran_context_text_node_count
            ),

        "quran_reference_text_node_count":
            (
                passage.routing
                .quran_reference_text_node_count
            ),

        "source_note_text_node_count":
            (
                passage.routing
                .source_note_text_node_count
            ),

        "explanation_text_node_count":
            (
                passage.routing
                .explanation_text_node_count
            ),

        "provenance_violation_count":
            (
                passage.routing
                .provenance_violation_count
            ),

        "ui_leaks":
            ui_leaks,
    }

    result = {
        "audit_id":
            "dorar-aqeedah-adversarial-v1",

        "provider":
            "Dorar al-Sunniyyah",

        "source_family":
            "DORAR_AQEEDA",

        "adapter_contract":
            "dorar-aqeedah-canonical-article-v1",

        "canonical_url":
            URL,

        "response_sha256":
            response_sha256,

        "adapter_status":
            "AUDITED",

        "runtime_admission":
            "NOT_ADMITTED",

        "source_trust_passport":
            "NOT_ISSUED",

        "structural_limitations": [
            (
                "Hadith matn is not independently "
                "delimited by the observed Aqeedah DOM."
            ),
            (
                "Quran contexts and Quran references "
                "are preserved independently and are "
                "not force-paired."
            ),
            (
                "Bibliographic citations are provenance "
                "only and do not promote Aqeedah authority."
            ),
            (
                "Reported Hadith grading remains attributed "
                "source-note provenance and requires the "
                "Hadith foundation for authentication."
            )
        ],

        "checks":
            checks,

        "metrics":
            metrics,

        "failures":
            failures,

        "result":
            (
                "PASS"
                if not failures
                else "FAIL"
            ),
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

    print()
    print(
        "============================================"
    )

    print(
        "DORAR AQEEDAH ADVERSARIAL AUDIT"
    )

    print(
        "============================================"
    )

    print(
        "Response SHA256:",
        response_sha256,
    )

    print(
        "Title chars:",
        metrics[
            "title_chars"
        ],
    )

    print(
        "Explanation chars:",
        metrics[
            "explanation_chars"
        ],
    )

    print(
        "Quran contexts:",
        metrics[
            "quran_context_count"
        ],
    )

    print(
        "Quran references:",
        metrics[
            "quran_reference_count"
        ],
    )

    print(
        "Source notes:",
        metrics[
            "source_note_count"
        ],
    )

    print(
        "Hadith-source notes:",
        metrics[
            "hadith_source_note_count"
        ],
    )

    print(
        "Reported grading notes:",
        metrics[
            "reported_hadith_grading_note_count"
        ],
    )

    print(
        "Bibliographic notes:",
        metrics[
            "bibliographic_reference_note_count"
        ],
    )

    print(
        "Provenance violations:",
        metrics[
            "provenance_violation_count"
        ],
    )

    print(
        "UI leaks:",
        len(
            ui_leaks
        ),
    )

    print()
    print(
        "Quran canonical promotion:",
        checks[
            "quran_context_not_canonical_witness"
        ],
    )

    print(
        "Forced Quran pairing:",
        checks[
            "no_forced_quran_pairing"
        ],
    )

    print(
        "Bibliographic authority promotion:",
        checks[
            "bibliographic_authority_promotion"
        ],
    )

    print(
        "Independent Hadith authentication:",
        checks[
            "independent_hadith_authenticity"
        ],
    )

    print(
        "Hadith matn extraction:",
        checks[
            "hadith_matn_structural_extraction"
        ],
    )

    print()
    print(
        "RESULT:",
        result[
            "result"
        ],
    )

    print(
        "ADAPTER:",
        result[
            "adapter_status"
        ],
    )

    print(
        "RUNTIME:",
        result[
            "runtime_admission"
        ],
    )

    print(
        "PASSPORT:",
        result[
            "source_trust_passport"
        ],
    )

    if failures:

        print()

        for failure in failures:
            print(
                "FAIL:",
                failure,
            )

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
