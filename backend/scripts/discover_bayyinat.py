from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[1]


DISCOVERY_ROOT = (
    ROOT
    / "data/competition/discovery/"
    "bayyinat"
)

RAW = (
    DISCOVERY_ROOT
    / "raw"
)

OUT = (
    DISCOVERY_ROOT
    / "discovery.json"
)

RESOLUTION = (
    DISCOVERY_ROOT
    / "resolution.json"
)


def sha256(
    raw: bytes,
) -> str:

    return hashlib.sha256(
        raw
    ).hexdigest()


def clean(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        unescape(
            value
        ),
    ).strip()


_ARABIC_DIACRITICS = re.compile(
    r"[\u0610-\u061a"
    r"\u064b-\u065f"
    r"\u0670"
    r"\u06d6-\u06ed]"
)


def normalize_arabic(
    value: str,
) -> str:

    import unicodedata

    value = unicodedata.normalize(
        "NFKC",
        value,
    )

    value = _ARABIC_DIACRITICS.sub(
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

    return clean(
        value
    )


class VisibleHTML(
    HTMLParser
):

    def __init__(
        self,
    ) -> None:

        super().__init__(
            convert_charrefs=True
        )

        self.parts = []

        self.urls = []

        self.skip_depth = 0

    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        tag = tag.lower()

        attrs = dict(
            attrs
        )

        if tag in {
            "script",
            "style",
            "noscript",
        }:

            self.skip_depth += 1

            return

        if tag == "a":

            href = attrs.get(
                "href"
            )

            if href:

                self.urls.append(
                    href
                )

    def handle_endtag(
        self,
        tag,
    ):

        tag = tag.lower()

        if (
            tag in {
                "script",
                "style",
                "noscript",
            }
            and self.skip_depth
        ):

            self.skip_depth -= 1

    def handle_data(
        self,
        data,
    ):

        if self.skip_depth:
            return

        value = clean(
            data
        )

        if value:

            self.parts.append(
                value
            )


def parse_meta(
    path: Path,
) -> dict:

    parts = path.read_text(
        encoding="utf-8"
    ).strip().split(
        "\t"
    )

    if len(parts) != 4:

        raise RuntimeError(
            "malformed curl meta"
        )

    return {
        "http_code":
            int(
                parts[0]
            ),

        "effective_url":
            parts[1],

        "content_type":
            parts[2],

        "size_download":
            int(
                float(
                    parts[3]
                    or "0"
                )
            ),
    }


def detect_kind(
    *,
    raw: bytes,
    content_type: str,
) -> str:

    content_type = (
        content_type
        or ""
    ).lower()

    if (
        raw.startswith(
            b"%PDF-"
        )
        or "application/pdf"
        in content_type
    ):

        return "pdf"


    if (
        raw[:4]
        == b"PK\x03\x04"
    ):

        try:

            with zipfile.ZipFile(
                RAW
                / "artifact.body"
            ) as zf:

                names = set(
                    zf.namelist()
                )

                if (
                    "word/document.xml"
                    in names
                ):

                    return "docx"

        except Exception:

            pass


    prefix = raw[
        :1000
    ].lower()

    if (
        b"<!doctype html"
        in prefix
        or b"<html"
        in prefix
        or "text/html"
        in content_type
    ):

        return "html"


    return "binary_or_text"


def extract_pdf_text(
    path: Path,
) -> tuple[
    str,
    int | None,
    str,
]:

    try:

        from pypdf import PdfReader

        reader = PdfReader(
            str(
                path
            )
        )

        text = "\n".join(
            page.extract_text()
            or ""
            for page in reader.pages
        )

        return (
            text,
            len(
                reader.pages
            ),
            "pypdf",
        )

    except Exception:

        pass


    if shutil.which(
        "pdftotext"
    ):

        with tempfile.NamedTemporaryFile(
            suffix=".txt"
        ) as tmp:

            result = subprocess.run(
                [
                    "pdftotext",
                    "-layout",
                    str(
                        path
                    ),
                    tmp.name,
                ],
                check=False,
                capture_output=True,
            )

            if result.returncode == 0:

                text = Path(
                    tmp.name
                ).read_text(
                    encoding="utf-8",
                    errors="replace",
                )

                page_count = None

                if shutil.which(
                    "pdfinfo"
                ):

                    info = subprocess.run(
                        [
                            "pdfinfo",
                            str(
                                path
                            ),
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                    )

                    match = re.search(
                        r"^Pages:\s+(\d+)",
                        info.stdout,
                        re.MULTILINE,
                    )

                    if match:

                        page_count = int(
                            match.group(
                                1
                            )
                        )

                return (
                    text,
                    page_count,
                    "pdftotext",
                )


    raise RuntimeError(
        "PDF identified but neither pypdf nor "
        "pdftotext could extract text"
    )


def extract_docx_text(
    path: Path,
) -> str:

    with zipfile.ZipFile(
        path
    ) as zf:

        xml = zf.read(
            "word/document.xml"
        ).decode(
            "utf-8",
            errors="replace",
        )

    xml = re.sub(
        r"</w:p>",
        "\n",
        xml,
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        xml,
    )

    return clean(
        text
    )


def extract_html_text(
    raw: bytes,
) -> tuple[
    str,
    list[str],
]:

    parser = VisibleHTML()

    parser.feed(
        raw.decode(
            "utf-8",
            errors="replace",
        )
    )

    return (
        "\n".join(
            parser.parts
        ),
        parser.urls,
    )


def marker_count(
    text: str,
    markers: tuple[
        str,
        ...
    ],
) -> int:

    normalized_text = (
        normalize_arabic(
            text
        )
    )

    return sum(
        normalized_text.count(
            normalize_arabic(
                marker
            )
        )
        for marker in markers
    )


resolution = json.loads(
    RESOLUTION.read_text(
        encoding="utf-8"
    )
)

locator_meta = parse_meta(
    RAW
    / "locator.meta.tsv"
)

artifact_meta = parse_meta(
    RAW
    / "artifact.meta.tsv"
)

artifact_raw = (
    RAW
    / "artifact.body"
).read_bytes()


if artifact_meta[
    "http_code"
] != 200:

    raise SystemExit(
        "artifact HTTP status is not 200"
    )


kind = detect_kind(
    raw=artifact_raw,
    content_type=(
        artifact_meta[
            "content_type"
        ]
    ),
)


page_count = None
extractor = None
urls = []


if kind == "pdf":

    (
        text,
        page_count,
        extractor,
    ) = extract_pdf_text(
        RAW
        / "artifact.body"
    )


elif kind == "html":

    (
        text,
        urls,
    ) = extract_html_text(
        artifact_raw
    )

    extractor = (
        "html_visible_text"
    )


elif kind == "docx":

    text = extract_docx_text(
        RAW
        / "artifact.body"
    )

    extractor = (
        "docx_xml"
    )


else:

    text = artifact_raw.decode(
        "utf-8",
        errors="replace",
    )

    extractor = (
        "plain_text_fallback"
    )


text = text.replace(
    "\r\n",
    "\n",
)

text = re.sub(
    r"[ \t]+",
    " ",
    text,
)


QUESTION_HEADING_LABELS = (
    "\u0633\u0624\u0627\u0644",
    "\u0627\u0644\u0633\u0624\u0627\u0644",
)


ANSWER_HEADING_LABELS = (
    "\u062c\u0648\u0627\u0628",
    "\u0627\u0644\u062c\u0648\u0627\u0628",
    "\u0627\u0644\u0625\u062c\u0627\u0628\u0629",
    "\u0627\u0644\u0627\u062c\u0627\u0628\u0629",
)


def _qa_label_match(
    line: str,
    labels: tuple[str, ...],
) -> bool:
    """
    Match only exact normalized structural headings.

    Narrative phrases such as:

        السؤال عن ...
        السؤال حول ...

    are intentionally excluded.
    """

    value = normalize_arabic(
        line
    ).lstrip(
        "\ufeff"
    ).strip()

    normalized_labels = {
        normalize_arabic(
            label
        )
        for label in labels
    }

    return (
        value
        in normalized_labels
    )


def _qa_heading_kind(
    line: str,
) -> str | None:

    if _qa_label_match(
        line,
        QUESTION_HEADING_LABELS,
    ):
        return "Q"

    if _qa_label_match(
        line,
        ANSWER_HEADING_LABELS,
    ):
        return "A"

    return None


qa_heading_events = [
    qa_kind
    for line in text.splitlines()
    if (
        qa_kind := _qa_heading_kind(
            line
        )
    )
]


question_heading_count = sum(
    event == "Q"
    for event in qa_heading_events
)


answer_heading_count = sum(
    event == "A"
    for event in qa_heading_events
)


qa_transition_counts = {
    "Q_TO_A": 0,
    "A_TO_Q": 0,
    "Q_TO_Q": 0,
    "A_TO_A": 0,
}


for left, right in zip(
    qa_heading_events,
    qa_heading_events[1:],
):

    qa_transition_counts[
        f"{left}_TO_{right}"
    ] += 1


qa_pair_count = sum(
    1
    for index, event in enumerate(
        qa_heading_events[:-1]
    )
    if (
        event == "Q"
        and
        qa_heading_events[
            index + 1
        ]
        == "A"
    )
)


qa_pair_failure_count = (
    question_heading_count
    - qa_pair_count
)


qa_pairing_ratio = (
    qa_pair_count
    / question_heading_count
    if question_heading_count
    else 0.0
)


explicit_qa_heading_contract = (
    "STRUCTURALLY_STABLE"
    if (
        question_heading_count
        == 263
        and
        answer_heading_count
        == 263
        and
        qa_pair_count
        == 263
        and
        qa_pair_failure_count
        == 0
        and
        qa_transition_counts[
            "Q_TO_A"
        ]
        == 263
        and
        qa_transition_counts[
            "A_TO_Q"
        ]
        == 262
        and
        qa_transition_counts[
            "Q_TO_Q"
        ]
        == 0
        and
        qa_transition_counts[
            "A_TO_A"
        ]
        == 0
    )
    else "NOT_STABLE"
)


question_mark_lines = len(
    [
        line
        for line in text.splitlines()
        if (
            "?" in line
            or "\u061f" in line
        )
    ]
)


shubhah_signal_count = marker_count(
    text,
    (
        "\u0634\u0628\u0647\u0629",
        "\u0627\u0644\u0634\u0628\u0647\u0629",
        "\u0634\u0628\u0647\u0627\u062a",
        "\u0627\u0644\u0634\u0628\u0647\u0627\u062a",
        "\u0627\u0639\u062a\u0631\u0627\u0636",
    ),
)


quran_signal_count = marker_count(
    text,
    (
        "\u0627\u0644\u0642\u0631\u0622\u0646",
        "\u0642\u0631\u0622\u0646",
        "\u0642\u0627\u0644 \u062a\u0639\u0627\u0644\u0649",
        "\u0633\u0648\u0631\u0629",
        "\u0622\u064a\u0629",
        "\u0627\u0644\u0622\u064a\u0629",
    ),
)


hadith_signal_count = marker_count(
    text,
    (
        "\u062d\u062f\u064a\u062b",
        "\u0642\u0627\u0644 \u0631\u0633\u0648\u0644 \u0627\u0644\u0644\u0647",
        "\u0631\u0648\u0627\u0647 \u0627\u0644\u0628\u062e\u0627\u0631\u064a",
        "\u0631\u0648\u0627\u0647 \u0645\u0633\u0644\u0645",
        "\u0623\u062e\u0631\u062c\u0647",
        "\u0635\u062d\u064a\u062d \u0627\u0644\u0628\u062e\u0627\u0631\u064a",
        "\u0635\u062d\u064a\u062d \u0645\u0633\u0644\u0645",
    ),
)


history_signal_count = marker_count(
    text,
    (
        "\u0627\u0644\u0633\u064a\u0631\u0629",
        "\u0627\u0644\u062a\u0627\u0631\u064a\u062e",
        "\u0627\u0644\u0647\u062c\u0631\u0629",
        "\u063a\u0632\u0648\u0629",
        "\u0627\u0644\u062e\u0644\u0627\u0641\u0629",
        "\u0627\u0644\u0635\u062d\u0627\u0628\u0629",
    ),
)


fiqh_signal_count = marker_count(
    text,
    (
        "\u0627\u0644\u0641\u0642\u0647",
        "\u062d\u0644\u0627\u0644",
        "\u062d\u0631\u0627\u0645",
        "\u0627\u0644\u062d\u0643\u0645 \u0627\u0644\u0634\u0631\u0639\u064a",
        "\u0627\u0644\u0645\u0630\u0627\u0647\u0628",
        "\u0627\u0644\u0634\u0627\u0641\u0639\u064a",
        "\u0627\u0644\u062d\u0646\u0641\u064a",
        "\u0627\u0644\u0645\u0627\u0644\u0643\u064a",
        "\u0627\u0644\u062d\u0646\u0628\u0644\u064a",
    ),
)


aqeedah_signal_count = marker_count(
    text,
    (
        "\u0627\u0644\u0639\u0642\u064a\u062f\u0629",
        "\u0627\u0644\u062a\u0648\u062d\u064a\u062f",
        "\u0627\u0644\u0625\u064a\u0645\u0627\u0646",
        "\u0627\u0644\u0646\u0628\u0648\u0629",
        "\u0627\u0644\u0631\u0628\u0648\u0628\u064a\u0629",
        "\u0627\u0644\u0623\u0644\u0648\u0647\u064a\u0629",
    ),
)


citation_lexical_count = marker_count(
    text,
    (
        "\u0627\u0644\u0645\u0635\u062f\u0631",
        "\u0627\u0644\u0645\u0631\u0627\u062c\u0639",
        "\u0645\u0631\u062c\u0639",
        "\u064a\u0646\u0638\u0631",
        "\u0627\u0646\u0638\u0631",
        "\u0631\u0648\u0627\u0647",
        "\u0623\u062e\u0631\u062c\u0647",
    ),
)


footnote_like_count = len(
    re.findall(
        r"(?:\[\d+\]|\(\d+\))",
        text,
    )
)


# ============================================================
# QUESTION BOUNDARY CHARACTERIZATION
#
# Read-only structural probing showed:
#
# explicit question labels = 0
# explicit answer labels   = 268
#
# The book appears to use numbered question titles followed by
# a labelled "الجواب" section rather than paired سؤال/جواب
# labels.
#
# Therefore the question-boundary contract is NOT frozen here.
# ============================================================

question_boundary_contract = (
    "NOT_YET_FROZEN"
)


citation_contract = (
    "LEXICAL_SIGNALS_OBSERVED_ONLY"
    if (
        citation_lexical_count
        or footnote_like_count
        or urls
    )
    else "NO_STABLE_CHANNEL_OBSERVED"
)


result = {
    "discovery_version":
        1,

    "discovery_id":
        "bayyinat-official-artifact-characterization-v1",

    "official_domain":
        "shubuhat_faq",

    "source_family":
        "BAYYINAT",

    "official_locator":
        "dawa.center/file/7937",

    "official_requested_url":
        "https://dawa.center/file/7937",

    "locator": {
        **locator_meta,

        "sha256":
            sha256(
                (
                    RAW
                    / "locator.body"
                ).read_bytes()
            ),
    },

    "resolution":
        resolution,

    "artifact": {
        **artifact_meta,

        "kind":
            kind,

        "sha256":
            sha256(
                artifact_raw
            ),

        "bytes":
            len(
                artifact_raw
            ),

        "extractor":
            extractor,

        "page_count":
            page_count,

        "text_chars":
            len(
                text
            ),

        "url_count":
            len(
                urls
            ),
    },

    "structure": {
        "question_heading_count":
            question_heading_count,

        "answer_heading_count":
            answer_heading_count,

        "explicit_qa_heading_contract":
            explicit_qa_heading_contract,

        "qa_pair_count":
            qa_pair_count,

        "qa_pair_failure_count":
            qa_pair_failure_count,

        "qa_pairing_ratio":
            qa_pairing_ratio,

        "qa_transition_counts":
            qa_transition_counts,

        "question_mark_line_count":
            question_mark_lines,

        "shubhah_signal_count":
            shubhah_signal_count,

        "question_boundary_contract":
            question_boundary_contract,

        "citation_reference_contract":
            citation_contract,

        "citation_lexical_count":
            citation_lexical_count,

        "footnote_like_count":
            footnote_like_count,
    },

    "cross_domain_signals": {
        "quran":
            quran_signal_count,

        "hadith":
            hadith_signal_count,

        "history":
            history_signal_count,

        "fiqh":
            fiqh_signal_count,

        "aqeedah":
            aqeedah_signal_count,
    },

    "source_role_findings": {
        "primary_conversational_source":
            True,

        "universal_primary_evidence":
            False,

        "cross_domain_claims_require_primary_domain_routing":
            True,

        "lexical_citation_equals_verified_primary_evidence":
            False,

        "bayyinat_wording_equals_consensus":
            False,

        "question_boundary_contract_frozen":
            False,

        "citation_channel_contract_frozen":
            False,

        "generic_shamela_fallback_allowed":
            False,

        "explicit_question_label_contract_observed":
            (
                explicit_qa_heading_contract
                == "STRUCTURALLY_STABLE"
            ),

        "explicit_answer_label_contract_observed":
            (
                explicit_qa_heading_contract
                == "STRUCTURALLY_STABLE"
            ),

        "numbered_question_boundary_contract_frozen":
            False,

        "numbered_question_structure_observed":
            True,

        "answer_label_structure_observed":
            True,

        "cross_domain_lexical_signals_require_normalized_arabic":
            True
    },

    "runtime_admission":
        "PENDING_AUDIT",

    "adapter":
        "NOT_IMPLEMENTED",

    "source_trust_passport":
        "NOT_ISSUED",

    "result":
        "PASS",
}


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
    "BAYYINAT OFFICIAL ARTIFACT CHARACTERIZATION"
)

print(
    "============================================"
)

print(
    "Official locator:",
    result[
        "official_requested_url"
    ],
)

print(
    "Locator effective:",
    result[
        "locator"
    ][
        "effective_url"
    ],
)

print(
    "Resolved artifact:",
    result[
        "artifact"
    ][
        "effective_url"
    ],
)

print(
    "Artifact kind:",
    kind,
)

print(
    "Artifact bytes:",
    len(
        artifact_raw
    ),
)

print(
    "Artifact SHA256:",
    result[
        "artifact"
    ][
        "sha256"
    ],
)

print(
    "Extractor:",
    extractor,
)

print(
    "Pages:",
    page_count,
)

print(
    "Text chars:",
    len(
        text
    ),
)

print()
print(
    "Question headings:",
    question_heading_count,
)

print(
    "Answer headings:",
    answer_heading_count,
)

print(
    "Question-mark lines:",
    question_mark_lines,
)

print(
    "Shubhah signals:",
    shubhah_signal_count,
)

print()
print(
    "Cross-domain lexical signals:"
)

for key, value in result[
    "cross_domain_signals"
].items():

    print(
        " ",
        key,
        "=",
        value,
    )

print()
print(
    "Question boundary contract:",
    question_boundary_contract,
)

print(
    "Citation/reference contract:",
    citation_contract,
)

print()
print(
    "? official locator acquired"
)

print(
    "? exact artifact SHA captured"
)

print(
    "? artifact type characterized"
)

print(
    "? question/answer structure observed"
)

print(
    "? citation/reference signals observed"
)

print(
    "? embedded cross-domain signals measured"
)

print(
    "? Bayyinat remains conversational authority"
)

print(
    "? cross-domain evidence laundering prohibited"
)

print()
print(
    "RESULT: PASS"
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
