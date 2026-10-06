from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from basira.sources.hadith.hadeethenc.models import (
    HadeethEncArabicRow,
    HadeethEncEnglishRow,
    HadeethEncLanguage,
    HadeethEncRelease,
)

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


class HadeethEncWorkbookError(
    ValueError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class HadeethEncArabicWorkbook:
    release: HadeethEncRelease
    rows: tuple[
        HadeethEncArabicRow,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class HadeethEncEnglishWorkbook:
    release: HadeethEncRelease
    rows: tuple[
        HadeethEncEnglishRow,
        ...,
    ]


def _column_number(
    ref: str,
) -> int:
    match = re.match(
        r"[A-Z]+",
        ref,
    )

    if match is None:
        raise HadeethEncWorkbookError(
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


def _shared_strings(
    archive: zipfile.ZipFile,
) -> list[str]:
    path = "xl/sharedStrings.xml"

    if path not in archive.namelist():
        return []

    root = ET.fromstring(
        archive.read(path)
    )

    result: list[str] = []

    for item in root.findall(
        "main:si",
        NS,
    ):
        result.append(
            "".join(
                node.text or ""
                for node in item.iter(
                    f"{{{MAIN_NS}}}t"
                )
            )
        )

    return result


def _sheet_paths(
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


def _cell_value(
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


def _read_workbook_rows(
    path: Path,
) -> tuple[
    str,
    tuple[str, ...],
    list[dict[str, str]],
]:
    if not path.is_file():
        raise HadeethEncWorkbookError(
            f"Workbook not found: {path}"
        )

    with zipfile.ZipFile(path) as archive:
        strings = _shared_strings(
            archive
        )

        sheets = _sheet_paths(
            archive
        )

        if len(sheets) != 1:
            raise HadeethEncWorkbookError(
                "Expected exactly one worksheet, "
                f"found {len(sheets)}."
            )

        _, sheet_path = sheets[0]

        root = ET.fromstring(
            archive.read(
                sheet_path
            )
        )

        xml_rows = root.findall(
            ".//main:sheetData/main:row",
            NS,
        )

        logical_rows: list[
            list[str]
        ] = []

        for row in xml_rows:
            cells: dict[
                int,
                str,
            ] = {}

            for cell in row.findall(
                "main:c",
                NS,
            ):
                cells[
                    _column_number(
                        cell.attrib["r"]
                    )
                ] = _cell_value(
                    cell,
                    strings,
                )

            if not cells:
                logical_rows.append(
                    []
                )
                continue

            max_column = max(cells)

            logical_rows.append(
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

    if len(logical_rows) < 2:
        raise HadeethEncWorkbookError(
            "Workbook must contain metadata "
            "and header rows."
        )

    metadata = (
        logical_rows[0][0]
        if logical_rows[0]
        else ""
    )

    headers = tuple(
        logical_rows[1]
    )

    rows: list[
        dict[str, str]
    ] = []

    for values in logical_rows[2:]:
        if not values:
            continue

        padded = values + [
            ""
        ] * (
            len(headers)
            - len(values)
        )

        payload = dict(
            zip(
                headers,
                padded,
                strict=False,
            )
        )

        if payload.get("id"):
            rows.append(payload)

    return (
        metadata,
        headers,
        rows,
    )


def _metadata_value(
    metadata: str,
    prefix: str,
) -> str:
    for line in (
        metadata.splitlines()
    ):
        cleaned = line.lstrip(
            "# "
        )

        if cleaned.startswith(prefix):
            return cleaned[
                len(prefix):
            ].strip()

    raise HadeethEncWorkbookError(
        f"Missing metadata field: {prefix}"
    )


def _parse_release(
    metadata: str,
    *,
    language: HadeethEncLanguage,
) -> HadeethEncRelease:
    source_url = _metadata_value(
        metadata,
        "Source:",
    )

    update_check_url = (
        _metadata_value(
            metadata,
            "Check for updates:",
        )
    )

    last_update = _metadata_value(
        metadata,
        "Last update:",
    )

    match = re.fullmatch(
        r"(.+?)\s+\((v[^)]+)\)",
        last_update,
    )

    if match is None:
        raise HadeethEncWorkbookError(
            "Could not parse HadeethEnc "
            f"release metadata: {last_update!r}"
        )

    last_updated = (
        match.group(1).strip()
    )

    version = (
        match.group(2).strip()
    )

    return HadeethEncRelease(
        language=language,
        version=version,
        last_updated=last_updated,
        source_url=source_url,
        update_check_url=(
            update_check_url
        ),
    )


def load_hadeethenc_arabic_workbook(
    path: Path,
) -> HadeethEncArabicWorkbook:
    metadata, headers, rows = (
        _read_workbook_rows(path)
    )

    expected_headers = (
        "id",
        "title",
        "hadith_text",
        "explanation",
        "word_meanings",
        "benefits",
        "grade",
        "takhrij",
        "link",
    )

    if headers != expected_headers:
        raise HadeethEncWorkbookError(
            "Unexpected Arabic workbook schema: "
            f"{headers!r}"
        )

    release = _parse_release(
        metadata,
        language=(
            HadeethEncLanguage.ARABIC
        ),
    )

    parsed = tuple(
        HadeethEncArabicRow.model_validate(
            row
        )
        for row in rows
    )

    return HadeethEncArabicWorkbook(
        release=release,
        rows=parsed,
    )


def load_hadeethenc_english_workbook(
    path: Path,
) -> HadeethEncEnglishWorkbook:
    metadata, headers, rows = (
        _read_workbook_rows(path)
    )

    expected_headers = (
        "id",
        "title_ar",
        "title",
        "hadith_text_ar",
        "hadith_text",
        "explanation_ar",
        "explanation",
        "benefits_ar",
        "benefits",
        "grade_ar",
        "takhrij_ar",
        "grade",
        "takhrij",
        "lang",
        "link",
    )

    if headers != expected_headers:
        raise HadeethEncWorkbookError(
            "Unexpected English workbook schema: "
            f"{headers!r}"
        )

    release = _parse_release(
        metadata,
        language=(
            HadeethEncLanguage.ENGLISH
        ),
    )

    parsed = tuple(
        HadeethEncEnglishRow.model_validate(
            row
        )
        for row in rows
    )

    return HadeethEncEnglishWorkbook(
        release=release,
        rows=parsed,
    )
