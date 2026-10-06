from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SurahAppSourceDescriptor:
    slug: str
    domain: ScholarlyDomain
    author_name: str | None = None
    institution: str | None = None
    publisher: str | None = None


SURAHAPP_SOURCE_CATALOG = {
    descriptor.slug: descriptor
    for descriptor in (
        SurahAppSourceDescriptor(
            slug="tafsir-katheer",
            domain=ScholarlyDomain.TAFSIR,
            author_name="ابن كثير",
            publisher="دار ابن الجوزي - السعودية",
        ),
        SurahAppSourceDescriptor(
            slug="tafsir-saadi",
            domain=ScholarlyDomain.TAFSIR,
            author_name=(
                "عبد الرحمن بن ناصر السعدي"
            ),
            publisher="دار ابن الجوزي - السعودية",
        ),
        SurahAppSourceDescriptor(
            slug="tafsir-mokhtasar",
            domain=ScholarlyDomain.TAFSIR,
            institution=(
                "مركز تفسير للدراسات القرآنية"
            ),
        ),
        SurahAppSourceDescriptor(
            slug="ayat-nozool",
            domain=(
                ScholarlyDomain
                .REVELATION_CONTEXT
            ),
            author_name="إبراهيم محمد العلي",
            publisher=(
                "دار القلم للنشر والتوزيع، دمشق"
            ),
        ),
    )
}


class SurahAppScholarlyParser:
    """
    Parse an already-audited Surah App snapshot into
    attributable ScholarlyPassage objects.

    Safety properties
    -----------------
    - only explicitly registered sources are accepted;
    - the aggregate snapshot must have PASS integrity;
    - each source must have PASS Quran alignment;
    - unresolved Quran alignment is rejected;
    - source scholarly text is preserved verbatim;
    - Quran references are treated as source anchors,
      not inferred semantic spans.
    """

    def parse_snapshot(
        self,
        snapshot_root: Path,
    ) -> tuple[
        ScholarlyPassage,
        ...,
    ]:
        manifest = self._read_object(
            snapshot_root
            / "snapshot-manifest.json"
        )

        if (
            manifest.get(
                "integrity_status"
            )
            != "PASS"
        ):
            raise ValueError(
                "Surah App snapshot integrity "
                "must be PASS before ingestion."
            )

        snapshot_version_raw = (
            manifest.get(
                "snapshot_version"
            )
        )

        snapshot_version = (
            str(snapshot_version_raw)
            if snapshot_version_raw
            is not None
            else None
        )

        source_entries = (
            manifest.get(
                "sources"
            )
        )

        if not isinstance(
            source_entries,
            list,
        ):
            raise ValueError(
                "Surah App snapshot manifest "
                "must contain a sources list."
            )

        passages: list[
            ScholarlyPassage
        ] = []

        seen_ids: set[str] = set()

        for source_entry in (
            source_entries
        ):
            if not isinstance(
                source_entry,
                dict,
            ):
                raise ValueError(
                    "Surah App source entry "
                    "must be an object."
                )

            parsed = (
                self._parse_source(
                    snapshot_root=(
                        snapshot_root
                    ),
                    source_entry=(
                        source_entry
                    ),
                    snapshot_version=(
                        snapshot_version
                    ),
                )
            )

            for passage in parsed:
                if (
                    passage.passage_id
                    in seen_ids
                ):
                    raise ValueError(
                        "Duplicate scholarly "
                        "passage id: "
                        f"{passage.passage_id}"
                    )

                seen_ids.add(
                    passage.passage_id
                )

                passages.append(
                    passage
                )

        return tuple(
            passages
        )

    def _parse_source(
        self,
        *,
        snapshot_root: Path,
        source_entry: dict[
            str,
            Any,
        ],
        snapshot_version: (
            str | None
        ),
    ) -> tuple[
        ScholarlyPassage,
        ...,
    ]:
        source_slug = (
            self._require_string(
                source_entry,
                "source_slug",
            )
        )

        descriptor = (
            SURAHAPP_SOURCE_CATALOG.get(
                source_slug
            )
        )

        if descriptor is None:
            raise ValueError(
                "Unapproved Surah App source: "
                f"{source_slug}"
            )

        alignment = (
            source_entry.get(
                "quran_alignment"
            )
        )

        if not isinstance(
            alignment,
            dict,
        ):
            raise ValueError(
                f"{source_slug}: missing "
                "Quran alignment audit."
            )

        if (
            alignment.get(
                "status"
            )
            != "PASS"
        ):
            raise ValueError(
                f"{source_slug}: Quran "
                "alignment must be PASS."
            )

        unresolved = int(
            alignment.get(
                "unresolved_reference_count",
                -1,
            )
        )

        if unresolved != 0:
            raise ValueError(
                f"{source_slug}: unresolved "
                "Quran alignment references "
                f"must be zero, got "
                f"{unresolved}."
            )

        source_id = (
            self._require_string(
                source_entry,
                "source_id",
            )
        )

        work_title = (
            self._require_string(
                source_entry,
                "title",
            )
        )

        coverage_mode = (
            self._require_string(
                source_entry,
                "coverage_mode",
            )
        )

        corpus_relative = (
            self._require_string(
                source_entry,
                "corpus_file",
            )
        )

        expected_count = int(
            source_entry[
                "record_count"
            ]
        )

        corpus_path = (
            snapshot_root
            / corpus_relative
        )

        rows = self._read_list(
            corpus_path
        )

        if (
            len(rows)
            != expected_count
        ):
            raise ValueError(
                f"{source_slug}: corpus "
                "record count does not match "
                "aggregate manifest."
            )

        project_path = (
            snapshot_root
            / source_slug
            / "project.json"
        )

        project = self._read_object(
            project_path
        )

        project_type = str(
            project.get(
                "type",
                "",
            )
        )

        source_url = (
            "https://dev.surahapp.com/"
            "api/v1/project/"
            f"{source_slug}"
        )

        passages: list[
            ScholarlyPassage
        ] = []

        seen_references: set[
            tuple[int, int]
        ] = set()

        for row in rows:
            if not isinstance(
                row,
                dict,
            ):
                raise ValueError(
                    f"{source_slug}: corpus "
                    "row must be an object."
                )

            surah_number = int(
                str(
                    row[
                        "sura_number"
                    ]
                )
            )

            ayah_number = int(
                str(
                    row[
                        "aya_number"
                    ]
                )
            )

            reference = (
                surah_number,
                ayah_number,
            )

            if (
                reference
                in seen_references
            ):
                raise ValueError(
                    f"{source_slug}: duplicate "
                    "Quran anchor "
                    f"{surah_number}:"
                    f"{ayah_number}"
                )

            seen_references.add(
                reference
            )

            content = row.get(
                "content"
            )

            if not isinstance(
                content,
                str,
            ):
                raise ValueError(
                    f"{source_slug}: content "
                    "must be a string at "
                    f"{surah_number}:"
                    f"{ayah_number}."
                )

            if not content:
                raise ValueError(
                    f"{source_slug}: empty "
                    "scholarly content at "
                    f"{surah_number}:"
                    f"{ayah_number}."
                )

            sura_name = str(
                row.get(
                    "sura_name",
                    "",
                )
            )

            aya_text = str(
                row.get(
                    "aya_text",
                    "",
                )
            )

            passage_id = (
                f"{source_id}:"
                f"{surah_number}:"
                f"{ayah_number}"
            )

            passages.append(
                ScholarlyPassage(
                    passage_id=(
                        passage_id
                    ),
                    source_id=(
                        source_id
                    ),
                    domain=(
                        descriptor.domain
                    ),
                    work_id=(
                        source_slug
                    ),
                    work_title=(
                        work_title
                    ),
                    text=content,
                    author_name=(
                        descriptor
                        .author_name
                    ),
                    institution=(
                        descriptor
                        .institution
                    ),
                    publisher=(
                        descriptor
                        .publisher
                    ),
                    source_version=(
                        snapshot_version
                    ),
                    source_url=(
                        source_url
                    ),
                    surah_number=(
                        surah_number
                    ),
                    ayah_start=(
                        ayah_number
                    ),
                    ayah_end=(
                        ayah_number
                    ),
                    metadata={
                        "provider": (
                            "Surah App / "
                            "Tafsir Center"
                        ),
                        "source_slug": (
                            source_slug
                        ),
                        "coverage_mode": (
                            coverage_mode
                        ),
                        "project_type": (
                            project_type
                        ),
                        "sura_name": (
                            sura_name
                        ),
                        "quran_anchor_text": (
                            aya_text
                        ),
                    },
                )
            )

        return tuple(
            passages
        )

    @staticmethod
    def _require_string(
        value: dict[
            str,
            Any,
        ],
        key: str,
    ) -> str:
        result = value.get(
            key
        )

        if (
            not isinstance(
                result,
                str,
            )
            or not result
        ):
            raise ValueError(
                f"Required non-empty "
                f"string field missing: "
                f"{key}"
            )

        return result

    @staticmethod
    def _read_object(
        path: Path,
    ) -> dict[
        str,
        Any,
    ]:
        value = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                f"{path}: expected "
                "JSON object."
            )

        return value

    @staticmethod
    def _read_list(
        path: Path,
    ) -> list[Any]:
        value = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

        if not isinstance(
            value,
            list,
        ):
            raise ValueError(
                f"{path}: expected "
                "JSON list."
            )

        return value
