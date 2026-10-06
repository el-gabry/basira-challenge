from __future__ import annotations

import hashlib
import json
import re
import unicodedata

from collections import Counter
from pathlib import Path

import pypdf
from pypdf import PdfReader


ROOT = Path(
    __file__
).resolve().parents[1]


PDF = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "bayyinat"
    / "raw"
    / "artifact.body"
)


OUTPUT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "bayyinat"
    / "unit-structure.json"
)


EXPECTED_SHA256 = (
    "619b7201833419b8fbf86c463208462"
    "b9a2a7f02ad2306a2667490f3b410ad4e"
)


DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


def normalize(
    value: str,
) -> str:

    value = unicodedata.normalize(
        "NFKC",
        value,
    )

    value = DIACRITICS.sub(
        "",
        value,
    )

    value = value.replace(
        "ـ",
        "",
    )

    value = value.translate(
        str.maketrans(
            {
                "أ": "ا",
                "إ": "ا",
                "آ": "ا",
                "ٱ": "ا",
                "ى": "ي",
                "ؤ": "و",
                "ئ": "ي",
            }
        )
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


QUESTION_LABELS = {
    normalize("سؤال"),
    normalize("السؤال"),
}


ANSWER_LABELS = {
    normalize("جواب"),
    normalize("الجواب"),
    normalize("الإجابة"),
    normalize("الاجابة"),
}


# IMPORTANT:
#
# This is an extraction marker observed in the frozen official
# PDF text layer.
#
# It is NOT interpreted as the semantic Arabic spelling of a
# heading such as "المسألة".
#
TITLE_MARKER = re.compile(
    r"^\s*الم\s*(\d{1,3})\s*س"
)


FOOTER_SECONDARY_MARKERS = (
    "دلال",
    "دللي",
    "دليل",
)


END_MATTER_MARKERS = (
    "مراجع",
    "المراجع",
    "فهرس",
    "الفهرس",
    "المصادر",
    "استبانة",
    "الخاتمة",
    "الختام",
)


def is_keyword_footer(
    item: dict,
) -> bool:

    value = item[
        "norm"
    ]

    if (
        normalize("كلمات")
        not in value
    ):
        return False

    return any(
        normalize(marker)
        in value
        for marker
        in FOOTER_SECONDARY_MARKERS
    )


raw = PDF.read_bytes()

actual_sha = hashlib.sha256(
    raw
).hexdigest()


if actual_sha != EXPECTED_SHA256:

    raise SystemExit(
        "Bayyinat frozen artifact SHA256 mismatch"
    )


reader = PdfReader(
    str(PDF)
)


pages = [
    page.extract_text()
    or ""
    for page in reader.pages
]


if len(
    pages
) != 1259:

    raise SystemExit(
        f"unexpected Bayyinat page count: {len(pages)}"
    )


# ============================================================
# GLOBAL NONEMPTY LINE STREAM
# ============================================================

stream = []

global_index = 0


for page_no, page in enumerate(
    pages,
    start=1,
):

    for line_no, raw_line in enumerate(
        page.splitlines(),
        start=1,
    ):

        value = normalize(
            raw_line
        )

        if not value:
            continue

        stream.append(
            {
                "index":
                    global_index,

                "page":
                    page_no,

                "line":
                    line_no,

                "raw":
                    raw_line,

                "norm":
                    value,
            }
        )

        global_index += 1


# ============================================================
# STRUCTURAL MARKERS
# ============================================================

markers = []

questions = []

answers = []


for item in stream:

    marker_match = TITLE_MARKER.match(
        item[
            "norm"
        ]
    )

    if marker_match:

        markers.append(
            {
                **item,

                "ordinal":
                    int(
                        marker_match.group(
                            1
                        )
                    ),
            }
        )


    if (
        item[
            "norm"
        ]
        in QUESTION_LABELS
    ):

        questions.append(
            item
        )


    if (
        item[
            "norm"
        ]
        in ANSWER_LABELS
    ):

        answers.append(
            item
        )


assert len(markers) == 263
assert len(questions) == 263
assert len(answers) == 263


assert [
    marker[
        "ordinal"
    ]
    for marker in markers
] == list(
    range(
        1,
        264
    )
)


# ============================================================
# M / Q / A GLOBAL EVENT CONTRACT
# ============================================================

events = []


for marker in markers:

    events.append(
        {
            **marker,
            "kind":
                "M",
        }
    )


for item in questions:

    events.append(
        {
            **item,
            "kind":
                "Q",
        }
    )


for item in answers:

    events.append(
        {
            **item,
            "kind":
                "A",
        }
    )


events.sort(
    key=lambda item:
        item[
            "index"
        ]
)


event_kinds = [
    event[
        "kind"
    ]
    for event in events
]


expected_event_kinds = []

for _ in range(
    263
):

    expected_event_kinds.extend(
        [
            "M",
            "Q",
            "A",
        ]
    )


assert (
    event_kinds
    == expected_event_kinds
)


transition_counts = Counter(
    (
        left[
            "kind"
        ],
        right[
            "kind"
        ],
    )
    for left, right in zip(
        events,
        events[1:],
    )
)


assert (
    transition_counts[
        (
            "M",
            "Q",
        )
    ]
    == 263
)

assert (
    transition_counts[
        (
            "Q",
            "A",
        )
    ]
    == 263
)

assert (
    transition_counts[
        (
            "A",
            "M",
        )
    ]
    == 262
)


# ============================================================
# UNIT MAP
# ============================================================

units = []


for ordinal in range(
    1,
    264
):

    marker = markers[
        ordinal - 1
    ]

    question = questions[
        ordinal - 1
    ]

    answer = answers[
        ordinal - 1
    ]


    assert (
        marker[
            "index"
        ]
        < question[
            "index"
        ]
        < answer[
            "index"
        ]
    )


    assert (
        marker[
            "page"
        ]
        == question[
            "page"
        ]
    )


    page_lines = pages[
        marker[
            "page"
        ]
        - 1
    ].splitlines()


    title_lines = [
        raw_line
        for raw_line
        in page_lines[
            marker[
                "line"
            ]
            - 1
            :
            question[
                "line"
            ]
            - 1
        ]
        if normalize(
            raw_line
        )
    ]


    assert len(
        title_lines
    ) in {
        1,
        2,
    }


    if ordinal < 263:

        next_marker = markers[
            ordinal
        ]

        assert (
            answer[
                "index"
            ]
            < next_marker[
                "index"
            ]
        )

        end_boundary = {
            "kind":
                "NEXT_NUMBERED_TITLE_MARKER_EXCLUSIVE",

            "next_ordinal":
                ordinal + 1,

            "page":
                next_marker[
                    "page"
                ],

            "line":
                next_marker[
                    "line"
                ],
        }

    else:

        end_boundary = None


    units.append(
        {
            "ordinal":
                ordinal,

            "marker": {
                "page":
                    marker[
                        "page"
                    ],

                "line":
                    marker[
                        "line"
                    ],
            },

            "question_heading": {
                "page":
                    question[
                        "page"
                    ],

                "line":
                    question[
                        "line"
                    ],
            },

            "answer_heading": {
                "page":
                    answer[
                        "page"
                    ],

                "line":
                    answer[
                        "line"
                    ],
            },

            "title_line_count":
                len(
                    title_lines
                ),

            "end_boundary":
                end_boundary,
        }
    )


title_line_distribution = Counter(
    unit[
        "title_line_count"
    ]
    for unit in units
)


assert (
    title_line_distribution[
        1
    ]
    == 173
)

assert (
    title_line_distribution[
        2
    ]
    == 90
)


# ============================================================
# UNIVERSAL KEYWORD-FOOTER HYPOTHESIS
#
# Explicitly record its rejection.
# ============================================================

footer_counts = []

zero_footer_units = []


for ordinal in range(
    1,
    264
):

    start = markers[
        ordinal - 1
    ][
        "index"
    ]

    if ordinal < 263:

        stop = markers[
            ordinal
        ][
            "index"
        ]

    else:

        stop = (
            stream[
                -1
            ][
                "index"
            ]
            + 1
        )


    unit_items = [
        item
        for item in stream
        if (
            start
            <= item[
                "index"
            ]
            < stop
        )
    ]


    unit_footers = [
        item
        for item in unit_items
        if is_keyword_footer(
            item
        )
    ]


    footer_counts.append(
        len(
            unit_footers
        )
    )


    if not unit_footers:

        zero_footer_units.append(
            ordinal
        )


assert (
    Counter(
        footer_counts
    )
    == {
        0: 20,
        1: 243,
    }
)


expected_zero_footer_units = [
    15,
    16,
    17,
    21,
    25,
    26,
    27,
    30,
    31,
    37,
    42,
    43,
    45,
    46,
    49,
    54,
    87,
    89,
    95,
    227,
]


assert (
    zero_footer_units
    == expected_zero_footer_units
)


# ============================================================
# FINAL UNIT #263
#
# Global keyword-footer rule is rejected, but #263 itself has
# exactly one footer after its answer.
# ============================================================

final_marker = markers[
    -1
]

final_answer = answers[
    -1
]


final_items = [
    item
    for item in stream
    if (
        item[
            "index"
        ]
        >= final_marker[
            "index"
        ]
    )
]


final_footers = [
    item
    for item in final_items
    if (
        item[
            "index"
        ]
        > final_answer[
            "index"
        ]
        and
        is_keyword_footer(
            item
        )
    )
]


assert (
    len(
        final_footers
    )
    == 1
)


final_footer = final_footers[
    0
]


assert (
    final_footer[
        "page"
    ]
    == 1253
)


assert (
    final_footer[
        "line"
    ]
    == 8
)


assert (
    final_answer[
        "index"
    ]
    < final_footer[
        "index"
    ]
)


# ============================================================
# END MATTER AFTER FINAL FOOTER
# ============================================================

end_matter_hits = []


for item in stream:

    if (
        item[
            "index"
        ]
        <= final_footer[
            "index"
        ]
    ):
        continue


    for marker in END_MATTER_MARKERS:

        if (
            normalize(
                marker
            )
            in item[
                "norm"
            ]
        ):

            end_matter_hits.append(
                {
                    "marker":
                        marker,

                    "page":
                        item[
                            "page"
                        ],

                    "line":
                        item[
                            "line"
                        ],

                    "raw":
                        item[
                            "raw"
                        ],
                }
            )


assert end_matter_hits


reference_hits = [
    hit
    for hit in end_matter_hits
    if (
        hit[
            "marker"
        ]
        in {
            "مراجع",
            "المراجع",
        }
    )
]


survey_hits = [
    hit
    for hit in end_matter_hits
    if (
        hit[
            "marker"
        ]
        == "استبانة"
    )
]


assert reference_hits
assert survey_hits


assert min(
    hit[
        "page"
    ]
    for hit in reference_hits
) == 1255


assert min(
    hit[
        "page"
    ]
    for hit in survey_hits
) == 1257


# Freeze final semantic boundary.

units[
    -1
][
    "end_boundary"
] = {
    "kind":
        "FINAL_KEYWORD_FOOTER_INCLUSIVE",

    "page":
        final_footer[
            "page"
        ],

    "line":
        final_footer[
            "line"
        ],
}


# ============================================================
# OUTPUT
# ============================================================

payload = {
    "schema_version":
        1,

    "source":
        "BAYYINAT",

    "official_locator":
        "https://dawa.center/file/7937",

    "artifact": {
        "kind":
            "pdf",

        "page_count":
            1259,

        "sha256":
            actual_sha,

        "extractor":
            "pypdf",

        "extractor_version":
            pypdf.__version__,
    },

    "title_marker_contract": {
        "status":
            "FROZEN_FOR_THIS_ARTIFACT",

        "semantic_interpretation":
            "NONE",

        "extraction_regex":
            r"^\s*الم\s*(\d{1,3})\s*س",

        "global_hit_count":
            263,

        "ordinal_sequence":
            "1..263",

        "unique":
            True,

        "same_page_before_question_heading":
            "263/263",

        "title_line_distribution": {
            "one_line":
                173,

            "two_lines":
                90,
        },
    },

    "qa_contract": {
        "status":
            "STRUCTURALLY_STABLE",

        "question_heading_count":
            263,

        "answer_heading_count":
            263,

        "event_cycle":
            "M,Q,A x263",

        "m_to_q":
            263,

        "q_to_a":
            263,

        "a_to_next_m":
            262,
    },

    "keyword_footer_hypothesis": {
        "global_contract":
            False,

        "units_with_detected_footer":
            243,

        "units_without_detected_footer":
            20,

        "zero_footer_unit_ids":
            zero_footer_units,

        "allowed_as_universal_terminator":
            False,
    },

    "unit_boundary_contract": {
        "status":
            "FROZEN",

        "start_boundary":
            "NUMBERED_TITLE_MARKER_INCLUSIVE",

        "nonfinal_units": {
            "ordinals":
                "1..262",

            "end_boundary":
                "NEXT_NUMBERED_TITLE_MARKER_EXCLUSIVE",

            "validated":
                "262/262",
        },

        "final_unit": {
            "ordinal":
                263,

            "end_boundary":
                "FINAL_KEYWORD_FOOTER_INCLUSIVE",

            "footer_page":
                final_footer[
                    "page"
                ],

            "footer_line":
                final_footer[
                    "line"
                ],

            "references_begin_page":
                1255,

            "survey_begin_page":
                1257,

            "uses_eof_as_semantic_boundary":
                False,
        },
    },

    "source_role_constraints": {
        "bayyinat_is_primary_conversational_source":
            True,

        "bayyinat_is_universal_primary_evidence":
            False,

        "cross_domain_claims_route_to_primary_domains":
            True,

        "internal_citation_channel_frozen":
            False,

        "generic_shamela_fallback_allowed":
            False,
    },

    "runtime_state": {
        "runtime_admission":
            "PENDING_AUDIT",

        "adapter":
            "NOT_IMPLEMENTED",

        "source_trust_passport":
            "NOT_ISSUED",
    },

    "end_matter_observations": {
        "reference_hits":
            end_matter_hits,
    },

    "units":
        units,
}


OUTPUT.write_text(
    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)


print(
    "============================================"
)

print(
    "BAYYINAT UNIT STRUCTURE AUDIT"
)

print(
    "============================================"
)

print(
    "Artifact:",
    actual_sha
)

print(
    "Markers:",
    len(
        markers
    )
)

print(
    "Questions:",
    len(
        questions
    )
)

print(
    "Answers:",
    len(
        answers
    )
)

print(
    "Title lines:",
    dict(
        sorted(
            title_line_distribution.items()
        )
    )
)

print(
    "Universal footer:",
    False
)

print(
    "Footer coverage:",
    "243/263"
)

print(
    "Non-final boundary:",
    "262/262 next-marker"
)

print(
    "Final boundary:",
    (
        f"footer page "
        f"{final_footer['page']} "
        f"line "
        f"{final_footer['line']}"
    )
)

print(
    "References:",
    "page 1255"
)

print(
    "Survey:",
    "page 1257"
)

print(
    "UNIT BOUNDARY CONTRACT: FROZEN"
)

print(
    "RUNTIME: PENDING_AUDIT"
)

print(
    "ADAPTER: NOT_IMPLEMENTED"
)

print(
    "PASSPORT: NOT_ISSUED"
)
