from __future__ import annotations

import hashlib
import json
import re
import unicodedata

from collections import Counter
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]

PDF = (
    ROOT
    / "data/competition/discovery/bayyinat/raw/artifact.body"
)

STRUCTURE = (
    ROOT
    / "data/competition/discovery/bayyinat/unit-structure.json"
)

SNAPSHOT = (
    ROOT
    / "data/competition/sources/shubuhat/bayyinat_units_v1.json"
)

CONTRACT = (
    ROOT
    / "data/competition/discovery/bayyinat/content-contract.json"
)


EXPECTED_SHA = (
    "619b7201833419b8fbf86c463208462"
    "b9a2a7f02ad2306a2667490f3b410ad4e"
)


DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = DIACRITICS.sub("", value)
    value = value.replace("ـ", "")

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

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def canon(value: str) -> str:
    value = norm(value)
    value = re.sub(r"[^ء-ي0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def is_noise(item: dict) -> bool:
    value = item["canon"]

    if not value:
        return True

    if re.fullmatch(r"\d{1,4}", value):
        return True

    if value == "بينات اسيلة منتقاة حول الاسلام":
        return True

    # recurring damaged running section heading
    if (
        item["line"] <= 2
        and value.startswith("ا اام")
    ):
        return True

    return False


# ============================================================
# EXACT INTERNAL STRUCTURAL LABELS
# ============================================================

def is_short_header(value: str) -> bool:
    """
    Includes both observed extraction families:

      مختصرم ا جاإة
      مختصرم الجواب

    Body phrases merely containing مختصر are excluded.
    """

    if len(value) > 45:
        return False

    if not value.startswith("مختصر"):
        return False

    return (
        "جواب" in value
        or "جاا" in value
        or "اجا" in value
    )


def is_detailed_header(value: str) -> bool:
    """
    Structural header only.

    Accepted:
      الجوابم التفصيلي
      التفصيلي الجوابم

    Rejected:
      وسيكون الجواب التفصيلي ...
      والجواب التفصيلي عن ...
    """

    if len(value) > 45:
        return False

    normal = (
        value.startswith("الجواب")
        and "تفصيلي" in value
    )

    reversed_extraction = (
        value.startswith("التفصيلي")
        and "جواب" in value
    )

    return (
        normal
        or reversed_extraction
    )


def is_gist_header(value: str) -> bool:
    return (
        len(value) <= 60
        and value.startswith("مضمو")
    )


def is_conclusion_header(value: str) -> bool:
    return (
        len(value) <= 80
        and value.startswith("خاتمة")
        and "جواب" in value
    )


def is_keyword_line(value: str) -> bool:
    return (
        "كلمات" in value
        and any(
            token in value
            for token in (
                "دللي",
                "دلال",
                "دليل",
            )
        )
    )


def is_related_line(value: str) -> bool:
    return (
        "اسيلة ذات علاقة"
        in value
    )


def is_similar_header(value: str) -> bool:
    return (
        len(value) <= 70
        and value.startswith("عبارات مشا")
    )


def text_from(items: list[dict]) -> str | None:
    values = [
        item["raw"].strip()
        for item in items
        if not is_noise(item)
        and item["raw"].strip()
    ]

    if not values:
        return None

    return "\n".join(values)


# ============================================================
# VERIFY SOURCE
# ============================================================

raw = PDF.read_bytes()

sha = hashlib.sha256(raw).hexdigest()

assert sha == EXPECTED_SHA


structure = json.loads(
    STRUCTURE.read_text(
        encoding="utf-8"
    )
)

assert (
    structure["unit_boundary_contract"]["status"]
    == "FROZEN"
)

assert len(structure["units"]) == 263


reader = PdfReader(str(PDF))

pages = [
    page.extract_text() or ""
    for page in reader.pages
]

assert len(pages) == 1259


# ============================================================
# PHYSICAL STREAM
# ============================================================

stream = []
coord = {}


for page_no, page in enumerate(
    pages,
    start=1,
):

    for line_no, raw_line in enumerate(
        page.splitlines(),
        start=1,
    ):

        item = {
            "page": page_no,
            "line": line_no,
            "raw": raw_line,
            "norm": norm(raw_line),
            "canon": canon(raw_line),
        }

        coord[
            (
                page_no,
                line_no,
            )
        ] = len(stream)

        stream.append(item)


def at(page: int, line: int) -> int:
    return coord[(page, line)]


# ============================================================
# PARSE 263 UNITS
# ============================================================

records = []

coverage = Counter()

short_failure = []
detailed_failure = []
ordering_failure = []


for position, unit in enumerate(
    structure["units"]
):

    ordinal = unit["ordinal"]

    marker = unit["marker"]
    question_heading = unit["question_heading"]
    answer_heading = unit["answer_heading"]

    m = at(
        marker["page"],
        marker["line"],
    )

    q = at(
        question_heading["page"],
        question_heading["line"],
    )

    a = at(
        answer_heading["page"],
        answer_heading["line"],
    )


    if ordinal < 263:

        next_marker = structure["units"][
            position + 1
        ]["marker"]

        end = at(
            next_marker["page"],
            next_marker["line"],
        )

    else:

        boundary = unit["end_boundary"]

        assert (
            boundary["kind"]
            == "FINAL_KEYWORD_FOOTER_INCLUSIVE"
        )

        end = (
            at(
                boundary["page"],
                boundary["line"],
            )
            + 1
        )


    assert m < q < a < end


    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title_items = [
        item
        for item in stream[m:q]
        if not is_noise(item)
    ]


    title_canon_lines = [
        item["canon"]
        for item in title_items
        if item["canon"]
    ]


    assert title_canon_lines


    # strip frozen extraction marker from first title line
    first_title = re.sub(
        rf"^\s*الم\s*{ordinal}\s*س\s*",
        "",
        title_canon_lines[0],
        count=1,
    ).strip()


    title_parts = (
        [first_title]
        if first_title
        else []
    )

    title_parts.extend(
        title_canon_lines[1:]
    )


    title = " ".join(title_parts).strip()

    assert title


    # --------------------------------------------------------
    # QUESTION REGION
    # --------------------------------------------------------

    question_items = [
        item
        for item in stream[
            q + 1:
            a
        ]
        if not is_noise(item)
    ]

    question_text = text_from(
        question_items
    )

    assert question_text


    similar_hits = [
        index
        for index, item in enumerate(
            question_items
        )
        if is_similar_header(
            item["canon"]
        )
    ]

    assert len(similar_hits) <= 1

    if similar_hits:
        coverage["SIMILAR"] += 1


    # --------------------------------------------------------
    # ANSWER REGION
    # --------------------------------------------------------

    answer_items = [
        item
        for item in stream[
            a + 1:
            end
        ]
        if not is_noise(item)
    ]


    short_hits = [
        index
        for index, item in enumerate(
            answer_items
        )
        if is_short_header(
            item["canon"]
        )
    ]


    detailed_hits = [
        index
        for index, item in enumerate(
            answer_items
        )
        if is_detailed_header(
            item["canon"]
        )
    ]


    gist_hits = [
        index
        for index, item in enumerate(
            answer_items
        )
        if is_gist_header(
            item["canon"]
        )
    ]


    conclusion_hits = [
        index
        for index, item in enumerate(
            answer_items
        )
        if is_conclusion_header(
            item["canon"]
        )
    ]


    keyword_hits = [
        index
        for index, item in enumerate(
            answer_items
        )
        if is_keyword_line(
            item["canon"]
        )
    ]


    related_hits = [
        index
        for index, item in enumerate(
            answer_items
        )
        if is_related_line(
            item["canon"]
        )
    ]


    if len(short_hits) != 1:
        short_failure.append(
            (
                ordinal,
                short_hits,
            )
        )

    if len(detailed_hits) != 1:
        detailed_failure.append(
            (
                ordinal,
                detailed_hits,
            )
        )


    assert len(gist_hits) <= 1
    assert len(conclusion_hits) <= 1
    assert len(keyword_hits) <= 1
    assert len(related_hits) <= 1


    if (
        len(short_hits) != 1
        or
        len(detailed_hits) != 1
    ):
        continue


    short_index = short_hits[0]
    detailed_index = detailed_hits[0]


    if short_index >= detailed_index:
        ordering_failure.append(
            ordinal
        )
        continue


    coverage["SHORT"] += 1
    coverage["DETAILED"] += 1

    if gist_hits:
        coverage["GIST"] += 1

    if conclusion_hits:
        coverage["CONCLUSION"] += 1

    if keyword_hits:
        coverage["KEYWORDS"] += 1

    if related_hits:
        coverage["RELATED"] += 1


    # --------------------------------------------------------
    # GIST SPAN
    # --------------------------------------------------------

    gist = None

    if gist_hits:

        gi = gist_hits[0]

        if gi < short_index:

            gist = text_from(
                answer_items[
                    gi + 1:
                    short_index
                ]
            )


    # --------------------------------------------------------
    # SHORT SPAN
    # --------------------------------------------------------

    short_answer = text_from(
        answer_items[
            short_index + 1:
            detailed_index
        ]
    )

    assert short_answer


    # --------------------------------------------------------
    # DETAILED END
    # --------------------------------------------------------

    post_detailed_markers = [
        index
        for index in (
            conclusion_hits
            + keyword_hits
            + related_hits
        )
        if index > detailed_index
    ]


    detailed_end = (
        min(post_detailed_markers)
        if post_detailed_markers
        else len(answer_items)
    )


    detailed_answer = text_from(
        answer_items[
            detailed_index + 1:
            detailed_end
        ]
    )

    assert detailed_answer


    # --------------------------------------------------------
    # CONCLUSION
    # --------------------------------------------------------

    conclusion = None

    if conclusion_hits:

        ci = conclusion_hits[0]

        later_metadata = [
            index
            for index in (
                keyword_hits
                + related_hits
            )
            if index > ci
        ]

        conclusion_end = (
            min(later_metadata)
            if later_metadata
            else len(answer_items)
        )

        conclusion = text_from(
            answer_items[
                ci + 1:
                conclusion_end
            ]
        )


    # --------------------------------------------------------
    # KEYWORDS
    # --------------------------------------------------------

    keywords = None

    if keyword_hits:

        item = answer_items[
            keyword_hits[0]
        ]

        value = item["canon"]

        split = value.find(
            "كلمات"
        )

        prefix = (
            value[:split].strip()
            if split >= 0
            else value
        )

        keywords = (
            prefix
            or None
        )


    # --------------------------------------------------------
    # RELATED QUESTIONS
    #
    # Preserve as block, not atomic evidentiary citations.
    # --------------------------------------------------------

    related_questions = None

    if related_hits:

        ri = related_hits[0]

        first = answer_items[ri]

        value = first["canon"]

        token = "اسيلة ذات علاقة"

        split = value.find(token)

        prefix = (
            value[:split].strip()
            if split >= 0
            else ""
        )


        related_parts = []

        if prefix:
            related_parts.append(
                prefix
            )


        for item in answer_items[
            ri + 1:
        ]:

            if not is_noise(item):
                related_parts.append(
                    item["raw"].strip()
                )


        if related_parts:
            related_questions = "\n".join(
                related_parts
            )


    records.append(
        {
            "ordinal":
                ordinal,

            "title":
                title,

            "question_text":
                question_text,

            "gist":
                gist,

            "short_answer":
                short_answer,

            "detailed_answer":
                detailed_answer,

            "conclusion":
                conclusion,

            "keywords":
                keywords,

            "related_questions":
                related_questions,

            "flags": {
                "similar_formulations_present":
                    bool(
                        similar_hits
                    ),

                "requires_primary_domain_routing":
                    True,

                "bayyinat_is_universal_primary_evidence":
                    False,

                "internal_citation_contract_frozen":
                    False,
            },

            "provenance": {
                "official_locator":
                    "https://dawa.center/file/7937",

                "artifact_sha256":
                    sha,

                "marker": {
                    "page":
                        marker["page"],

                    "line":
                        marker["line"],
                },

                "question_heading": {
                    "page":
                        question_heading[
                            "page"
                        ],

                    "line":
                        question_heading[
                            "line"
                        ],
                },

                "answer_heading": {
                    "page":
                        answer_heading[
                            "page"
                        ],

                    "line":
                        answer_heading[
                            "line"
                        ],
                },

                "end_boundary":
                    unit[
                        "end_boundary"
                    ],
            },
        }
    )


# ============================================================
# HARD CONTRACT
# ============================================================

if short_failure:
    raise AssertionError(
        f"SHORT failures: {short_failure}"
    )

if detailed_failure:
    raise AssertionError(
        f"DETAILED failures: {detailed_failure}"
    )

if ordering_failure:
    raise AssertionError(
        f"ordering failures: {ordering_failure}"
    )


assert len(records) == 263

assert coverage["SHORT"] == 263
assert coverage["DETAILED"] == 263

assert coverage["SIMILAR"] == 253
assert coverage["GIST"] == 178
assert coverage["CONCLUSION"] == 119
assert coverage["KEYWORDS"] == 243
assert coverage["RELATED"] == 74


# Known anomaly regressions.

by_id = {
    record["ordinal"]:
        record
    for record in records
}


for ordinal in (
    173,
    182,
):

    assert (
        by_id[
            ordinal
        ][
            "short_answer"
        ]
    )


for ordinal in (
    160,
    260,
):

    assert (
        by_id[
            ordinal
        ][
            "detailed_answer"
        ]
    )


snapshot = {
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
            sha,
    },

    "source_role": {
        "primary_conversational_source":
            True,

        "universal_primary_evidence":
            False,

        "cross_domain_primary_routing_required":
            True,

        "internal_citation_contract_frozen":
            False,

        "generic_shamela_fallback_allowed":
            False,
    },

    "field_contract": {
        "mandatory": [
            "title",
            "question_text",
            "short_answer",
            "detailed_answer",
            "provenance",
        ],

        "optional": [
            "gist",
            "conclusion",
            "keywords",
            "related_questions",
        ],

        "observed_counts": {
            key.lower():
                coverage[key]
            for key in (
                "SIMILAR",
                "GIST",
                "SHORT",
                "DETAILED",
                "CONCLUSION",
                "KEYWORDS",
                "RELATED",
            )
        },
    },

    "runtime_state": {
        "snapshot":
            "GOVERNED_READY",

        "standalone_adapter":
            "READY",

        "router_admission":
            "DEFERRED_TO_TRUST_SHIELD",

        "source_trust_passport":
            "DEFERRED_TO_TRUST_SHIELD",
    },

    "units":
        records,
}


SNAPSHOT.write_text(
    json.dumps(
        snapshot,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)


contract = {
    "schema_version":
        1,

    "source":
        "BAYYINAT",

    "status":
        "FROZEN",

    "artifact_sha256":
        sha,

    "unit_count":
        263,

    "mandatory_fields": {
        "SHORT":
            "263/263",

        "DETAILED":
            "263/263",
    },

    "optional_fields": {
        "SIMILAR":
            "253/263",

        "GIST":
            "178/263",

        "CONCLUSION":
            "119/263",

        "KEYWORDS":
            "243/263",

        "RELATED":
            "74/263",
    },

    "resolved_extraction_anomalies": {
        "short_alternate_header_units": [
            173,
            182,
        ],

        "detailed_body_false_positive_units": [
            160,
            260,
        ],

        "reversed_detailed_header_unit": [
            100,
        ],

        "short_body_false_positive_unit": [
            50,
        ],
    },

    "metadata_model": {
        "keywords_optional":
            True,

        "related_questions_optional":
            True,

        "independent":
            True,

        "xor":
            False,

        "neither_units": [
            95,
            227,
        ],
    },

    "citation_contract":
        "NOT_FROZEN",

    "runtime_admission":
        "DEFERRED_TO_TRUST_SHIELD",
}


CONTRACT.write_text(
    json.dumps(
        contract,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)


print("============================================")
print("BAYYINAT GOVERNED SNAPSHOT BUILT")
print("============================================")
print("Units:", len(records))
print("SHORT:", coverage["SHORT"])
print("DETAILED:", coverage["DETAILED"])
print("SIMILAR:", coverage["SIMILAR"])
print("GIST:", coverage["GIST"])
print("CONCLUSION:", coverage["CONCLUSION"])
print("KEYWORDS:", coverage["KEYWORDS"])
print("RELATED:", coverage["RELATED"])
print()
print("CONTENT CONTRACT: FROZEN")
print("SNAPSHOT: GOVERNED_READY")
print("ROUTER ADMISSION: DEFERRED_TO_TRUST_SHIELD")
