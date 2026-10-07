from __future__ import annotations

import json
import re
from functools import cached_property
from hashlib import sha256
from pathlib import Path
from typing import Any

from basira.competition.official_coverage import OfficialDomain
from basira.competition.retrieval_bridge import (
    CompetitionAuthorityBoundaryError,
    CompetitionRetrievalRequest,
    CompetitionSourceUnavailable,
)
from basira.evidence.models import EvidenceNode
from basira.evidence.quran_adapter import QuranEvidenceAdapter
from basira.models.quran import QuranVerse
from basira.sources.quran.repository import QuranRepository

QURANPEDIA_PASSPORT_PATH = Path("data/competition/passports/quranpedia-hafs.json")

QURANPEDIA_MANIFEST_PATH = Path(
    "data/competition/manifests/quran/quranpedia-hafs-2026-10-04.json"
)

_REFERENCE_RE = re.compile(r"(?<!\d)(\d{1,3})\s*:\s*(\d{1,3})(?!\d)")


class QuranpediaAdmissionError(ValueError):
    """Governed Quranpedia artifact failed runtime admission."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QuranpediaAdmissionError(f"cannot_load_json:{path}") from exc

    if not isinstance(value, dict):
        raise QuranpediaAdmissionError(f"json_root_not_object:{path}")

    return value


def _sha256(path: Path) -> str:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise QuranpediaAdmissionError(f"cannot_read_snapshot:{path}") from exc

    return sha256(payload).hexdigest()


def _collect_ayah_records(
    value: Any,
) -> tuple[dict[str, Any], ...]:
    """
    Extract Quran ayah records while preserving canonical
    parent-surah identity metadata from the same governed
    snapshot.

    Parent metadata grants no Quran-text authority. It is
    carried only so natural-language references such as
    "سورة الملك" can resolve to the same canonical coordinate
    that is later fetched through the governed evidence path.
    """

    records: list[dict[str, Any]] = []

    def visit(
        node: Any,
        *,
        parent_surah_id: int | None = None,
        parent_surah_name_ar: str | None = None,
    ) -> None:
        if isinstance(node, dict):
            next_surah_id = parent_surah_id
            next_surah_name_ar = parent_surah_name_ar

            ayahs = node.get("ayahs")

            if isinstance(ayahs, list):
                raw_id = node.get("id")
                raw_name = node.get("name")

                try:
                    next_surah_id = int(raw_id)
                except (TypeError, ValueError):
                    next_surah_id = None

                if isinstance(raw_name, str):
                    cleaned_name = raw_name.strip()

                    if cleaned_name:
                        next_surah_name_ar = cleaned_name

            required = {
                "surah",
                "number",
                "text",
            }

            if required.issubset(node):
                record = dict(node)

                if next_surah_id is not None:
                    record["_parent_surah_id"] = (
                        next_surah_id
                    )

                if next_surah_name_ar is not None:
                    record["_parent_surah_name_ar"] = (
                        next_surah_name_ar
                    )

                records.append(record)
                return

            for child in node.values():
                visit(
                    child,
                    parent_surah_id=next_surah_id,
                    parent_surah_name_ar=(
                        next_surah_name_ar
                    ),
                )

        elif isinstance(node, list):
            for child in node:
                visit(
                    child,
                    parent_surah_id=parent_surah_id,
                    parent_surah_name_ar=(
                        parent_surah_name_ar
                    ),
                )

    visit(value)

    return tuple(records)


def _clean_quran_text(value: Any) -> str:
    if not isinstance(value, str):
        raise QuranpediaAdmissionError("quran_text_not_string")

    text = value.lstrip("\ufeff").strip()

    if not text:
        raise QuranpediaAdmissionError("quran_text_blank")

    return text


def _optional_int(
    value: Any,
) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise QuranpediaAdmissionError("invalid_integer_metadata") from exc


def _clean_surah_name_ar(
    value: Any,
) -> str | None:
    if not isinstance(value, str):
        return None

    name = " ".join(
        value.strip().split()
    )

    if not name:
        return None

    prefix = "سورة "

    if name.startswith(prefix):
        name = name[len(prefix):].strip()

    return name or None


def _record_to_verse(
    record: dict[str, Any],
    *,
    source_id: str,
    narration: str,
) -> QuranVerse:
    try:
        surah = int(record["surah"])
        ayah = int(record["number"])
    except (KeyError, TypeError, ValueError) as exc:
        raise QuranpediaAdmissionError("invalid_quran_reference") from exc

    hafs_numbers = record.get("number_in_hafs")

    if hafs_numbers is not None:
        if not isinstance(hafs_numbers, list) or len(hafs_numbers) != 1:
            raise QuranpediaAdmissionError("invalid_number_in_hafs")

        try:
            hafs_number = int(hafs_numbers[0])
        except (TypeError, ValueError) as exc:
            raise QuranpediaAdmissionError("invalid_number_in_hafs") from exc

        if hafs_number != ayah:
            raise QuranpediaAdmissionError("number_in_hafs_mismatch")

    parent_surah_id = _optional_int(
        record.get("_parent_surah_id")
    )

    if (
        parent_surah_id is not None
        and parent_surah_id != surah
    ):
        raise QuranpediaAdmissionError(
            "parent_surah_identity_mismatch"
        )

    surah_name_ar = _clean_surah_name_ar(
        record.get("_parent_surah_name_ar")
    )

    text = _clean_quran_text(record["text"])

    return QuranVerse(
        source_id=source_id,
        surah_number=surah,
        ayah_number=ayah,
        surah_name_ar=surah_name_ar,
        text_uthmani=text,
        text_search=text,
        narration=narration,
        juz_number=_optional_int(record.get("juz")),
        page_number=_optional_int(record.get("page_number")),
    )


def _parse_reference(
    query: str,
) -> tuple[int, int] | None:
    match = _REFERENCE_RE.search(query)

    if match is None:
        return None

    return (
        int(match.group(1)),
        int(match.group(2)),
    )


class QuranpediaEvidenceAdapter:
    """
    Governed Competition Quran lane.

    passport
      -> manifest
      -> exact admitted snapshot hash
      -> QuranVerse
      -> QuranRepository lookup
      -> EvidenceNode

    Source authority comes exclusively from the competition
    passport/manifest admission state. The legacy source
    policy catalog is not consulted here.
    """

    def __init__(
        self,
        *,
        repo_root: Path | str = ".",
        evidence_adapter: QuranEvidenceAdapter | None = None,
    ) -> None:
        self._repo_root = Path(repo_root).resolve()
        self._evidence_adapter = evidence_adapter or QuranEvidenceAdapter()

    @cached_property
    def repository(self) -> QuranRepository:
        try:
            return self._load_governed_repository()
        except QuranpediaAdmissionError as exc:
            raise CompetitionSourceUnavailable("quranpedia") from exc

    def _load_governed_repository(
        self,
    ) -> QuranRepository:
        passport_path = self._repo_root / QURANPEDIA_PASSPORT_PATH
        manifest_path = self._repo_root / QURANPEDIA_MANIFEST_PATH

        passport = _load_json(passport_path)
        manifest = _load_json(manifest_path)

        if passport.get("provider") != "Quranpedia":
            raise QuranpediaAdmissionError("passport_provider_mismatch")

        if passport.get("role") != "quran":
            raise QuranpediaAdmissionError("passport_role_mismatch")

        passport_runtime = passport.get("runtime")

        if (
            not isinstance(passport_runtime, dict)
            or passport_runtime.get("eligible") is not True
        ):
            raise QuranpediaAdmissionError("passport_not_runtime_eligible")

        manifest_runtime = manifest.get("runtime")

        if (
            not isinstance(manifest_runtime, dict)
            or manifest_runtime.get("eligible") is not True
            or manifest_runtime.get("status") != "ELIGIBLE"
        ):
            raise QuranpediaAdmissionError("manifest_not_runtime_eligible")

        source_id = passport.get("source_id")

        if (
            not isinstance(source_id, str)
            or not source_id.strip()
            or manifest.get("source_id") != source_id
        ):
            raise QuranpediaAdmissionError("source_identity_mismatch")

        if manifest.get("provider") != "Quranpedia" or manifest.get("role") != "quran":
            raise QuranpediaAdmissionError("manifest_identity_mismatch")

        snapshot = manifest.get("snapshot")

        if not isinstance(snapshot, dict):
            raise QuranpediaAdmissionError("snapshot_manifest_missing")

        relative_path = snapshot.get("path")
        expected_sha256 = snapshot.get("sha256")
        expected_count = snapshot.get("record_count")

        if (
            not isinstance(relative_path, str)
            or not relative_path.strip()
            or not isinstance(expected_sha256, str)
            or len(expected_sha256) != 64
            or not isinstance(expected_count, int)
            or expected_count <= 0
        ):
            raise QuranpediaAdmissionError("invalid_snapshot_manifest")

        snapshot_path = (self._repo_root / relative_path).resolve()

        try:
            snapshot_path.relative_to(self._repo_root)
        except ValueError as exc:
            raise QuranpediaAdmissionError("snapshot_path_outside_repo") from exc

        actual_sha256 = _sha256(snapshot_path)

        passport_artifact = passport.get("artifact")

        if (
            not isinstance(passport_artifact, dict)
            or passport_artifact.get("snapshot_sha256") != expected_sha256
        ):
            raise QuranpediaAdmissionError("passport_snapshot_hash_mismatch")

        if actual_sha256 != expected_sha256:
            raise QuranpediaAdmissionError("snapshot_hash_mismatch")

        snapshot_root = _load_json(snapshot_path)

        if "data" not in snapshot_root:
            raise QuranpediaAdmissionError("snapshot_data_missing")

        records = _collect_ayah_records(snapshot_root["data"])

        if len(records) != expected_count:
            raise QuranpediaAdmissionError("snapshot_record_count_mismatch")

        witness = passport.get("witness")
        narration = "حفص عن عاصم"

        if isinstance(witness, dict):
            riwaya = witness.get("riwaya")

            if isinstance(riwaya, str) and riwaya.strip():
                narration = riwaya.strip()

        verses = tuple(
            _record_to_verse(
                record,
                source_id=source_id,
                narration=narration,
            )
            for record in records
        )

        references = {
            (
                verse.surah_number,
                verse.ayah_number,
            )
            for verse in verses
        }

        if len(references) != len(verses):
            raise QuranpediaAdmissionError("duplicate_quran_reference")

        return QuranRepository(verses)

    def retrieve(
        self,
        request: CompetitionRetrievalRequest,
    ) -> tuple[EvidenceNode, ...]:
        if request.official_domain is not OfficialDomain.QURAN:
            raise CompetitionAuthorityBoundaryError(
                "Quranpedia adapter only serves Quran."
            )

        if request.limit <= 0:
            return ()

        repository = self.repository

        reference = _parse_reference(request.query)

        if reference is not None:
            verse = repository.get(*reference)

            if verse is None:
                return ()

            return (self._evidence_adapter.from_verse(verse),)

        matches = repository.find_exact(request.query)

        if not matches:
            matches = repository.find_containing(request.query)

        return tuple(
            self._evidence_adapter.from_verse(verse)
            for verse in matches[: request.limit]
        )
