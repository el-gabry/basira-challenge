from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

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
            "Audit official HadeethEnc XLSX files "
            "without requiring openpyxl."
        )
    )

    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
    )

    parser.add_argument(
        "--preview-rows",
        type=int,
        default=5,
    )

    return parser.parse_args()


def column_number(
    ref: str,
) -> int:
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
        value = "".join(
            node.text or ""
            for node in item.iter(
                f"{{{MAIN_NS}}}t"
            )
        )

        values.append(value)

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

    result: list[
        tuple[str, str]
    ] = []

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
    cell_type = cell.attrib.get(
        "t"
    )

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


def audit_file(
    path: Path,
    *,
    preview_rows: int,
) -> None:
    print()
    print("=" * 100)
    print("FILE:", path.name)
    print("=" * 100)

    with zipfile.ZipFile(path) as archive:
        strings = shared_strings(
            archive
        )

        sheets = workbook_sheets(
            archive
        )

        print(
            "SHEETS:",
            len(sheets),
        )

        for sheet_name, sheet_path in sheets:
            root = ET.fromstring(
                archive.read(
                    sheet_path
                )
            )

            rows = root.findall(
                ".//main:sheetData/main:row",
                NS,
            )

            print()
            print(
                "SHEET:",
                repr(sheet_name),
            )

            print(
                "PHYSICAL ROWS:",
                len(rows),
            )

            for row in rows[
                :preview_rows
            ]:
                cells: dict[
                    int,
                    str,
                ] = {}

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
                    continue

                max_column = max(
                    cells
                )

                ordered = [
                    cells.get(
                        index,
                        "",
                    )
                    for index in range(
                        1,
                        max_column + 1,
                    )
                ]

                print(
                    "ROW",
                    row.attrib.get("r"),
                    ":",
                )

                for index, value in enumerate(
                    ordered,
                    start=1,
                ):
                    preview = value

                    if len(preview) > 250:
                        preview = (
                            preview[:250]
                            + "..."
                        )

                    print(
                        f"  C{index}:",
                        repr(preview),
                    )


def main() -> int:
    args = parse_args()

    for path in args.files:
        if not path.is_file():
            raise SystemExit(
                f"File not found: {path}"
            )

        audit_file(
            path,
            preview_rows=(
                args.preview_rows
            ),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
