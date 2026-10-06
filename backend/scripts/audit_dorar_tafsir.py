from __future__ import annotations

import hashlib
import json
from pathlib import Path

from basira.competition.dorar_tafsir import (
    DorarTafsirSectionKind,
    parse_dorar_tafsir_passage,
)


ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dorar-tafsir"
    / "raw"
    / "fatiha_passage.html"
)

OUT = (
    ROOT
    / "data"
    / "competition"
    / "audits"
    / "tafsir"
    / "dorar-tafsir-adversarial-v1.json"
)


EXPECTED_SECTIONS = {
    DorarTafsirSectionKind.GENERAL_MEANING,
    DorarTafsirSectionKind.WORD_MEANING,
    DorarTafsirSectionKind.GRAMMAR,
    DorarTafsirSectionKind.TAFSIR_AYAT,
    DorarTafsirSectionKind.EDUCATIONAL_BENEFITS,
    DorarTafsirSectionKind.SCHOLARLY_BENEFITS,
    DorarTafsirSectionKind.RHETORIC,
}


EXPECTED_ARTICLE_IDS = {
    DorarTafsirSectionKind.GENERAL_MEANING:
        "tt9",

    DorarTafsirSectionKind.WORD_MEANING:
        "tt7",

    DorarTafsirSectionKind.GRAMMAR:
        "tt8",

    DorarTafsirSectionKind.TAFSIR_AYAT:
        "tt4",

    DorarTafsirSectionKind.EDUCATIONAL_BENEFITS:
        "tt16",

    DorarTafsirSectionKind.SCHOLARLY_BENEFITS:
        "tt17",

    DorarTafsirSectionKind.RHETORIC:
        "tt18",
}


def main() -> None:

    raw = SOURCE.read_bytes()

    html = raw.decode(
        "utf-8",
        errors="replace",
    )

    passage = (
        parse_dorar_tafsir_passage(
            html=html,
            canonical_url=(
                "https://dorar.net/tafseer/1/1"
            ),
        )
    )

    failures: list[str] = []

    actual_sections = {
        section.section_kind
        for section
        in passage.sections
    }

    if actual_sections != EXPECTED_SECTIONS:
        failures.append(
            "canonical section set mismatch: "
            f"{sorted(x.value for x in actual_sections)}"
        )

    for section in passage.sections:

        expected_article_id = (
            EXPECTED_ARTICLE_IDS.get(
                section.section_kind
            )
        )

        if (
            expected_article_id is not None
            and section.article_id
            != expected_article_id
        ):
            failures.append(
                "canonical article id mismatch: "
                f"{section.section_kind.value}: "
                f"expected {expected_article_id}; "
                f"got {section.article_id}"
            )

    empty_sections = [
        section.section_kind.value
        for section in passage.sections
        if not section.explanation_text.strip()
    ]

    if empty_sections:
        failures.append(
            "empty canonical sections: "
            + ", ".join(
                empty_sections
            )
        )

    total_quran_contexts = sum(
        len(
            section.quran_contexts
        )
        for section in passage.sections
    )

    total_quran_refs = sum(
        len(
            section.quran_references
        )
        for section in passage.sections
    )

    total_citations = sum(
        len(
            section.citations
        )
        for section in passage.sections
    )

    narration_citations = [
        citation
        for section in passage.sections
        for citation in (
            section.narration_citations
        )
    ]

    grade_citations = [
        grade
        for section in passage.sections
        for grade in (
            section.reported_grade_citations
        )
    ]

    if total_quran_contexts < 1:
        failures.append(
            "no Quran context extracted"
        )

    if total_quran_refs < 1:
        failures.append(
            "no Quran references extracted"
        )

    if total_citations < 20:
        failures.append(
            "unexpectedly low citation extraction"
        )

    if len(narration_citations) < 2:
        failures.append(
            "too few narration source citations"
        )

    if len(grade_citations) < 1:
        failures.append(
            "no reported grading provenance extracted"
        )

    # --------------------------------------------------------
    # Quran / Tafsir boundary checks
    # --------------------------------------------------------
    #
    # IMPORTANT:
    #
    # String overlap is NOT a provenance violation.
    #
    # Example:
    #
    # <span class="aaya">مالِك</span>
    #
    # followed later by ordinary explanatory prose that also
    # contains the word "مالِك".
    #
    # The same string belongs to two legitimate semantic
    # roles. We therefore audit SOURCE-NODE ROUTING.
    # --------------------------------------------------------

    quran_source_text_node_count = sum(
        (
            section
            .quran_context_text_node_count
        )
        for section
        in passage.sections
    )

    quran_provenance_violation_count = sum(
        (
            section
            .quran_context_text_nodes_routed_to_explanation
        )
        for section
        in passage.sections
    )

    if quran_source_text_node_count < 1:
        failures.append(
            "no Quran-context source text nodes observed"
        )

    if quran_provenance_violation_count:
        failures.append(
            "Quran-origin source text nodes were "
            "routed to Tafsir explanation"
        )

    # Lexical overlap is retained as a diagnostic only.
    #
    # It may occur legitimately when a mufassir repeats one
    # word or phrase from the ayah during explanation.
    quran_string_overlap_count = 0

    quran_string_overlap_examples = []

    for section in passage.sections:

        for quran_text in section.quran_contexts:

            if (
                quran_text
                and quran_text
                in section.explanation_text
            ):
                quran_string_overlap_count += 1

                if (
                    len(
                        quran_string_overlap_examples
                    )
                    < 20
                ):
                    quran_string_overlap_examples.append(
                        {
                            "section":
                                section
                                .section_kind
                                .value,

                            "article_id":
                                section.article_id,

                            "quran_text":
                                quran_text[:200],

                            "interpretation":
                                "lexical_overlap_not_provenance_leak",
                        }
                    )

    # --------------------------------------------------------
    # We NEVER convert citation frequency into authenticity.
    # We NEVER independently grade hadith/athar.
    # --------------------------------------------------------

    report_sections = []

    for section in passage.sections:

        report_sections.append(
            {
                "kind":
                    section.section_kind.value,

                "article_id":
                    section.article_id,

                "heading":
                    section.heading,

                "explanation_chars":
                    len(
                        section.explanation_text
                    ),

                "quran_context_count":
                    len(
                        section.quran_contexts
                    ),

                "quran_reference_count":
                    len(
                        section.quran_references
                    ),

                "citation_count":
                    len(
                        section.citations
                    ),

                "narration_citation_count":
                    len(
                        section.narration_citations
                    ),

                "reported_grade_citation_count":
                    len(
                        section.reported_grade_citations
                    ),

                "quran_context_text_node_count":
                    section
                    .quran_context_text_node_count,

                "quran_context_text_nodes_routed_to_explanation":
                    section
                    .quran_context_text_nodes_routed_to_explanation,

                "reported_grade_previews": [
                    {
                        "language":
                            list(
                                item
                                .explicit_grade_language
                            ),

                        "text":
                            item.citation_text[:700],
                    }
                    for item in (
                        section
                        .reported_grade_citations
                    )
                ][:10],
            }
        )

    result = {
        "audit_id":
            "dorar-tafsir-adversarial-v1",

        "provider":
            "Dorar al-Sunniyyah",

        "source_id":
            passage.source_id,

        "canonical_url":
            passage.canonical_url,

        "response_sha256":
            hashlib.sha256(
                raw
            ).hexdigest(),

        "checks": {
            "canonical_sections":
                (
                    "PASS"
                    if actual_sections
                    == EXPECTED_SECTIONS
                    else "FAIL"
                ),

            "canonical_article_ids":
                (
                    "PASS"
                    if all(
                        (
                            EXPECTED_ARTICLE_IDS.get(
                                section.section_kind
                            )
                            == section.article_id
                        )
                        for section
                        in passage.sections
                    )
                    and actual_sections
                    == EXPECTED_SECTIONS
                    else "FAIL"
                ),

            "quran_tafsir_boundary":
                (
                    "PASS"
                    if (
                        total_quran_contexts >= 1
                        and quran_source_text_node_count >= 1
                        and quran_provenance_violation_count == 0
                    )
                    else "FAIL"
                ),

            "quran_reference_preservation":
                (
                    "PASS"
                    if total_quran_refs >= 1
                    else "FAIL"
                ),

            "citation_preservation":
                (
                    "PASS"
                    if total_citations >= 20
                    else "FAIL"
                ),

            "narration_source_preservation":
                (
                    "PASS"
                    if len(
                        narration_citations
                    ) >= 2
                    else "FAIL"
                ),

            "reported_grading_provenance":
                (
                    "PASS"
                    if len(
                        grade_citations
                    ) >= 1
                    else "FAIL"
                ),

            "independent_isnad_grading":
                "PROHIBITED",

            "authenticity_from_frequency":
                "PROHIBITED",

            "tafsir_as_canonical_quran":
                "PROHIBITED",

            "direct_fiqh_ruling_from_tafsir":
                "PROHIBITED",
        },

        "metrics": {
            "section_count":
                len(passage.sections),

            "quran_context_count":
                total_quran_contexts,

            "quran_reference_count":
                total_quran_refs,

            "citation_count":
                total_citations,

            "narration_citation_count":
                len(
                    narration_citations
                ),

            "reported_grade_citation_count":
                len(
                    grade_citations
                ),

            "quran_context_source_text_node_count":
                quran_source_text_node_count,

            "quran_provenance_violation_count":
                quran_provenance_violation_count,

            "quran_string_overlap_count":
                quran_string_overlap_count,
        },

        "sections":
            report_sections,

        "quran_string_overlap_examples":
            quran_string_overlap_examples,

        "failures":
            failures,

        "result":
            (
                "PASS"
                if not failures
                else "FAIL"
            ),

        "runtime_admission":
            "PENDING_AUDIT",

        "source_trust_passport":
            "NOT_ISSUED",
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
        "DORAR TAFSIR ADVERSARIAL AUDIT"
    )

    print(
        "============================================"
    )

    print(
        "Sections:",
        len(passage.sections),
    )

    for section in passage.sections:
        print(
            " ",
            section.section_kind.value,
            "|",
            section.article_id,
            "| quran:",
            len(section.quran_contexts),
            "| refs:",
            len(section.quran_references),
            "| citations:",
            len(section.citations),
            "| narration:",
            len(section.narration_citations),
            "| grades:",
            len(
                section.reported_grade_citations
            ),
        )

    print()
    print(
        "Quran contexts:",
        total_quran_contexts,
    )

    print(
        "Quran references:",
        total_quran_refs,
    )

    print(
        "Citations:",
        total_citations,
    )

    print(
        "Narration citations:",
        len(
            narration_citations
        ),
    )

    print(
        "Reported grade citations:",
        len(
            grade_citations
        ),
    )

    print(
        "Quran source text nodes:",
        quran_source_text_node_count,
    )

    print(
        "Quran provenance violations:",
        quran_provenance_violation_count,
    )

    print(
        "Quran lexical overlaps (diagnostic):",
        quran_string_overlap_count,
    )

    print()
    print(
        "Independent isnad grading: PROHIBITED"
    )

    print(
        "Authenticity from frequency: PROHIBITED"
    )

    print(
        "Runtime admission: PENDING_AUDIT"
    )

    print()
    print(
        "RESULT:",
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
