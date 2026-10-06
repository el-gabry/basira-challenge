from __future__ import annotations

import argparse
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

import pyarrow.parquet as pq

MAIN_NS = (
    "http://schemas.openxmlformats.org/"
    "spreadsheetml/2006/main"
)

REL_NS = (
    "http://schemas.openxmlformats.org/"
    "officeDocument/2006/relationships"
)

PKG_REL_NS = (
    "http://schemas.openxmlformats.org/"
    "package/2006/relationships"
)

NS = {
    "main": MAIN_NS,
    "rel": REL_NS,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare official HadeethEnc XLSX releases "
            "with the pinned QuranLab HadeethEnc snapshot."
        )
    )

    parser.add_argument(
        "--official-ar",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--official-en",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--quranlab-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--inspect-id",
        type=str,
        default="65065",
    )

    return parser.parse_args()


def column_number(ref: str) -> int:
    match = re.match(
        r"[A-Z]+",
        ref,
    )

    if match is None:
        raise ValueError(
            f"Invalid XLSX cell reference: {ref}"
        )

    result = 0

    for char in match.group():
        result = (
            result * 26
            + ord(char)
            - ord("A")
            + 1
        )

    return result


def shared_strings(
    archive: zipfile.ZipFile,
) -> list[str]:
    path = "xl/sharedStrings.xml"

    if path not in archive.namelist():
        return []

    root = ET.fromstring(
        archive.read(path)
    )

    values: list[str] = []

    for item in root.findall(
        "main:si",
        NS,
    ):
        text = "".join(
            node.text or ""
            for node in item.iter(
                f"{{{MAIN_NS}}}t"
            )
        )

        values.append(text)

    return values


def workbook_sheets(
    archive: zipfile.ZipFile,
) -> list[tuple[str, str]]:
    workbook = ET.fromstring(
        archive.read(
            "xl/workbook.xml"
        )
    )

    relationships = ET.fromstring(
        archive.read(
            "xl/_rels/workbook.xml.rels"
        )
    )

    relationship_map = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall(
            f"{{{PKG_REL_NS}}}Relationship"
        )
    }

    result: list[tuple[str, str]] = []

    for sheet in workbook.findall(
        "main:sheets/main:sheet",
        NS,
    ):
        relationship_id = sheet.attrib[
            f"{{{REL_NS}}}id"
        ]

        target = relationship_map[
            relationship_id
        ]

        if target.startswith("/"):
            path = target.lstrip("/")
        else:
            path = f"xl/{target}"

        result.append(
            (
                sheet.attrib["name"],
                path,
            )
        )

    return result


def cell_value(
    cell: ET.Element,
    strings: list[str],
) -> str:
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        return "".join(
            node.text or ""
            for node in cell.iter(
                f"{{{MAIN_NS}}}t"
            )
        )

    value = cell.find(
        "main:v",
        NS,
    )

    if value is None:
        return ""

    raw = value.text or ""

    if cell_type == "s":
        return strings[int(raw)]

    return raw


def load_xlsx_rows(
    path: Path,
) -> tuple[str, list[dict[str, str]]]:
    with zipfile.ZipFile(path) as archive:
        strings = shared_strings(
            archive
        )

        sheets = workbook_sheets(
            archive
        )

        if len(sheets) != 1:
            raise ValueError(
                f"Expected one sheet in {path}, "
                f"found {len(sheets)}."
            )

        _, sheet_path = sheets[0]

        root = ET.fromstring(
            archive.read(sheet_path)
        )

        xml_rows = root.findall(
            ".//main:sheetData/main:row",
            NS,
        )

        if len(xml_rows) < 2:
            raise ValueError(
                f"Workbook has no data: {path}"
            )

        metadata = ""

        records: list[
            list[str]
        ] = []

        for row in xml_rows:
            cells: dict[int, str] = {}

            for cell in row.findall(
                "main:c",
                NS,
            ):
                cells[
                    column_number(
                        cell.attrib["r"]
                    )
                ] = cell_value(
                    cell,
                    strings,
                )

            if not cells:
                records.append([])
                continue

            max_column = max(cells)

            records.append(
                [
                    cells.get(
                        index,
                        "",
                    )
                    for index in range(
                        1,
                        max_column + 1,
                    )
                ]
            )

        metadata = (
            records[0][0]
            if records
            and records[0]
            else ""
        )

        headers = records[1]

        data: list[
            dict[str, str]
        ] = []

        for values in records[2:]:
            if not values:
                continue

            padded = values + [
                ""
            ] * (
                len(headers)
                - len(values)
            )

            row = dict(
                zip(
                    headers,
                    padded,
                    strict=False,
                )
            )

            if row.get("id"):
                data.append(row)

        return metadata, data


def load_quranlab(
    root: Path,
    config: str,
) -> list[dict]:
    files = sorted(
        (root / config).glob(
            "*.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No Parquet file for {config}"
        )

    rows: list[dict] = []

    for file in files:
        rows.extend(
            pq.read_table(
                file
            ).to_pylist()
        )

    return rows


def by_id(
    rows: list[dict],
    *,
    field: str,
) -> dict[str, dict]:
    result: dict[str, dict] = {}

    duplicates: list[str] = []

    for row in rows:
        value = row.get(field)

        if value is None:
            continue

        key = str(value)

        if key in result:
            duplicates.append(key)

        result[key] = row

    if duplicates:
        raise ValueError(
            "Duplicate IDs found: "
            f"{duplicates[:10]}"
        )

    return result


def unwrap_brackets(
    value: str | None,
) -> str:
    if value is None:
        return ""

    normalized = value.strip()

    if (
        normalized.startswith("[")
        and normalized.endswith("]")
    ):
        return normalized[1:-1]

    return normalized


def compare_field(
    official: dict[str, dict],
    quranlab: dict[str, dict],
    *,
    official_field: str,
    quranlab_field: str,
    shared_ids: set[str],
) -> tuple[int, list[str]]:
    mismatches: list[str] = []

    matches = 0

    for hadith_id in sorted(
        shared_ids
    ):
        left = official[
            hadith_id
        ].get(
            official_field,
            ""
        )

        right = quranlab[
            hadith_id
        ].get(
            quranlab_field,
            ""
        )

        if left == right:
            matches += 1
        else:
            mismatches.append(
                hadith_id
            )

    return matches, mismatches


def print_metadata(
    label: str,
    metadata: str,
) -> None:
    print()
    print(label)

    for line in metadata.splitlines():
        if (
            "Language:" in line
            or "Last update:" in line
            or "Source:" in line
            or "Check for updates:" in line
        ):
            print(
                " ",
                line.lstrip("# "),
            )


def main() -> int:
    args = parse_args()

    ar_metadata, official_ar_rows = (
        load_xlsx_rows(
            args.official_ar
        )
    )

    en_metadata, official_en_rows = (
        load_xlsx_rows(
            args.official_en
        )
    )

    quranlab_ar_rows = load_quranlab(
        args.quranlab_root,
        "hadeethenc-ar",
    )

    quranlab_en_rows = load_quranlab(
        args.quranlab_root,
        "hadeethenc-en",
    )

    official_ar = by_id(
        official_ar_rows,
        field="id",
    )

    official_en = by_id(
        official_en_rows,
        field="id",
    )

    quranlab_ar = by_id(
        quranlab_ar_rows,
        field="hadeethenc_id",
    )

    quranlab_en = by_id(
        quranlab_en_rows,
        field="hadeethenc_id",
    )

    print("=" * 88)
    print(
        "HADEETHENC OFFICIAL ↔ QURANLAB AUDIT"
    )
    print("=" * 88)

    print_metadata(
        "OFFICIAL ARABIC METADATA",
        ar_metadata,
    )

    print_metadata(
        "OFFICIAL ENGLISH METADATA",
        en_metadata,
    )

    print()
    print("COUNTS")
    print(
        " Official Arabic:",
        len(official_ar),
    )
    print(
        " QuranLab Arabic:",
        len(quranlab_ar),
    )
    print(
        " Official English:",
        len(official_en),
    )
    print(
        " QuranLab English:",
        len(quranlab_en),
    )

    official_ar_ids = set(
        official_ar
    )
    quranlab_ar_ids = set(
        quranlab_ar
    )

    official_en_ids = set(
        official_en
    )
    quranlab_en_ids = set(
        quranlab_en
    )

    print()
    print("ARABIC ID COVERAGE")
    print(
        " Shared:",
        len(
            official_ar_ids
            & quranlab_ar_ids
        ),
    )
    print(
        " Official-only:",
        len(
            official_ar_ids
            - quranlab_ar_ids
        ),
    )
    print(
        " QuranLab-only:",
        len(
            quranlab_ar_ids
            - official_ar_ids
        ),
    )

    official_only_ar = sorted(
        official_ar_ids
        - quranlab_ar_ids
    )

    quranlab_only_ar = sorted(
        quranlab_ar_ids
        - official_ar_ids
    )

    print(
        " Official-only IDs:",
        official_only_ar,
    )

    print(
        " QuranLab-only IDs:",
        quranlab_only_ar,
    )

    print()
    print("ENGLISH ID COVERAGE")
    print(
        " Shared:",
        len(
            official_en_ids
            & quranlab_en_ids
        ),
    )
    print(
        " Official-only:",
        len(
            official_en_ids
            - quranlab_en_ids
        ),
    )
    print(
        " QuranLab-only:",
        len(
            quranlab_en_ids
            - official_en_ids
        ),
    )

    shared_ar = (
        official_ar_ids
        & quranlab_ar_ids
    )

    shared_en = (
        official_en_ids
        & quranlab_en_ids
    )

    ar_text_matches, ar_text_mismatches = (
        compare_field(
            official_ar,
            quranlab_ar,
            official_field=(
                "hadith_text"
            ),
            quranlab_field="text",
            shared_ids=shared_ar,
        )
    )

    ar_grade_matches, ar_grade_mismatches = (
        compare_field(
            official_ar,
            quranlab_ar,
            official_field="grade",
            quranlab_field="grade",
            shared_ids=shared_ar,
        )
    )

    en_text_matches, en_text_mismatches = (
        compare_field(
            official_en,
            quranlab_en,
            official_field=(
                "hadith_text"
            ),
            quranlab_field="text",
            shared_ids=shared_en,
        )
    )

    print()
    print("EXACT CONTENT COMPARISON")
    print(
        " Arabic hadith_text exact:",
        ar_text_matches,
        "/",
        len(shared_ar),
    )
    print(
        " Arabic text mismatches:",
        len(ar_text_mismatches),
    )

    print(
        " Arabic grade exact:",
        ar_grade_matches,
        "/",
        len(shared_ar),
    )
    print(
        " Arabic grade mismatches:",
        len(ar_grade_mismatches),
    )

    print(
        " English hadith_text exact:",
        en_text_matches,
        "/",
        len(shared_en),
    )
    print(
        " English text mismatches:",
        len(en_text_mismatches),
    )

    english_grade_exact = 0
    english_grade_unwrapped = 0
    english_grade_mismatch: list[
        str
    ] = []

    for hadith_id in sorted(
        shared_en
    ):
        official_grade = (
            official_en[
                hadith_id
            ].get(
                "grade",
                "",
            )
        )

        quranlab_grade = (
            quranlab_en[
                hadith_id
            ].get(
                "grade",
                "",
            )
        )

        if (
            official_grade
            == quranlab_grade
        ):
            english_grade_exact += 1
            continue

        if (
            unwrap_brackets(
                official_grade
            )
            == quranlab_grade
        ):
            english_grade_unwrapped += 1
            continue

        english_grade_mismatch.append(
            hadith_id
        )

    print(
        " English grade exact:",
        english_grade_exact,
    )
    print(
        " English grade equal after [] unwrap:",
        english_grade_unwrapped,
    )
    print(
        " English grade real mismatches:",
        len(
            english_grade_mismatch
        ),
    )

    inspect_id = args.inspect_id

    print()
    print("=" * 88)
    print(
        f"INSPECT HADITH ID {inspect_id}"
    )
    print("=" * 88)

    sources = {
        "official_ar": (
            official_ar.get(
                inspect_id
            )
        ),
        "official_en": (
            official_en.get(
                inspect_id
            )
        ),
        "quranlab_ar": (
            quranlab_ar.get(
                inspect_id
            )
        ),
        "quranlab_en": (
            quranlab_en.get(
                inspect_id
            )
        ),
    }

    for name, row in sources.items():
        print()
        print(name)

        if row is None:
            print("  NOT PRESENT")
            continue

        if name == "official_ar":
            print(
                "  grade:",
                repr(
                    row.get("grade")
                ),
            )
            print(
                "  takhrij:",
                repr(
                    row.get("takhrij")
                ),
            )

        elif name == "official_en":
            print(
                "  grade_ar:",
                repr(
                    row.get("grade_ar")
                ),
            )
            print(
                "  grade_en:",
                repr(
                    row.get("grade")
                ),
            )
            print(
                "  takhrij_ar:",
                repr(
                    row.get(
                        "takhrij_ar"
                    )
                ),
            )
            print(
                "  takhrij_en:",
                repr(
                    row.get("takhrij")
                ),
            )

        else:
            print(
                "  grade:",
                repr(
                    row.get("grade")
                ),
            )
            print(
                "  grade_source:",
                repr(
                    row.get(
                        "grade_source"
                    )
                ),
            )

    mismatch_counts = Counter(
        {
            "ar_text": len(
                ar_text_mismatches
            ),
            "ar_grade": len(
                ar_grade_mismatches
            ),
            "en_text": len(
                en_text_mismatches
            ),
            "en_grade": len(
                english_grade_mismatch
            ),
        }
    )

    print()
    print("MISMATCH SUMMARY")

    for key, count in (
        mismatch_counts.items()
    ):
        print(
            f" {key:10}: {count}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
