from __future__ import annotations

import re
from dataclasses import dataclass

from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _clean_required(
    value: str,
    *,
    field_name: str,
) -> str:
    cleaned = " ".join(value.split())

    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")

    return cleaned


def _validate_sha256(
    value: str,
) -> str:
    normalized = value.strip().lower()

    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError("snapshot_sha256 must be a 64-character hexadecimal SHA-256")

    return normalized


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaCorpusManifest:
    """
    Governance boundary for one imported Shamela
    snapshot.

    This describes an authorized corpus artifact.
    It does NOT assign religious authority to the
    books contained in it.
    """

    corpus_id: str

    snapshot_id: str

    snapshot_sha256: str

    source_ids: tuple[
        str,
        ...,
    ]

    attested_complete: bool = False

    def __post_init__(
        self,
    ) -> None:
        _clean_required(
            self.corpus_id,
            field_name="corpus_id",
        )

        _clean_required(
            self.snapshot_id,
            field_name="snapshot_id",
        )

        _validate_sha256(self.snapshot_sha256)

        normalized_sources = tuple(
            dict.fromkeys(
                " ".join(source_id.split())
                for source_id in self.source_ids
                if " ".join(source_id.split())
            )
        )

        if not normalized_sources:
            raise ValueError("source_ids must contain at least one source")

        object.__setattr__(
            self,
            "source_ids",
            normalized_sources,
        )

        object.__setattr__(
            self,
            "snapshot_sha256",
            _validate_sha256(self.snapshot_sha256),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaPassageRecord:
    """
    Storage-independent record imported from Shamela.

    A .bok importer, SQLite importer, JSON importer,
    or future API adapter must normalize into this
    structure first.

    The record is provenance only. It does not state
    that the passage is correct, preferred, or
    authoritative.
    """

    source_id: str

    source_version: str

    snapshot_id: str

    snapshot_sha256: str

    book_id: str

    page_id: str

    domain: ScholarlyDomain

    work_title: str

    text: str

    author_name: str | None = None

    institution: str | None = None

    publisher: str | None = None

    source_url: str | None = None

    section_title: str | None = None

    chapter_title: str | None = None

    volume: str | None = None

    page: str | None = None

    edition: str | None = None

    madhhab: str | None = None

    era: str | None = None

    discipline: str | None = None

    book_family: str | None = None

    parent_page_id: str | None = None

    parent_text: str | None = None

    def __post_init__(
        self,
    ) -> None:
        for (
            field_name,
            value,
        ) in (
            (
                "source_id",
                self.source_id,
            ),
            (
                "source_version",
                self.source_version,
            ),
            (
                "snapshot_id",
                self.snapshot_id,
            ),
            (
                "book_id",
                self.book_id,
            ),
            (
                "page_id",
                self.page_id,
            ),
            (
                "work_title",
                self.work_title,
            ),
            (
                "text",
                self.text,
            ),
        ):
            _clean_required(
                value,
                field_name=field_name,
            )

        object.__setattr__(
            self,
            "snapshot_sha256",
            _validate_sha256(self.snapshot_sha256),
        )

    def to_scholarly_passage(
        self,
    ) -> ScholarlyPassage:
        metadata = {
            "physical_source": ("shamela"),
            "shamela_book_id": (self.book_id),
            "shamela_page_id": (self.page_id),
            "snapshot_id": (self.snapshot_id),
            "snapshot_sha256": (self.snapshot_sha256),
        }

        optional = {
            "edition": self.edition,
            "madhhab": self.madhhab,
            "era": self.era,
            "discipline": (self.discipline),
            "book_family": (self.book_family),
            "parent_page_id": (self.parent_page_id),
            "parent_text": (self.parent_text),
        }

        metadata.update(
            {
                key: value
                for key, value in optional.items()
                if value is not None and value.strip()
            }
        )

        return ScholarlyPassage(
            passage_id=(f"{self.source_id}:{self.book_id}:{self.page_id}"),
            source_id=self.source_id,
            domain=self.domain,
            work_id=self.book_id,
            work_title=self.work_title,
            text=self.text,
            author_name=(self.author_name),
            institution=(self.institution),
            publisher=self.publisher,
            source_version=(self.source_version),
            source_url=self.source_url,
            section_title=(self.section_title),
            chapter_title=(self.chapter_title),
            volume=self.volume,
            page=self.page,
            metadata=metadata,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaPassageIdentity:
    source_id: str

    book_id: str

    page_id: str

    snapshot_id: str

    snapshot_sha256: str

    edition: str | None

    madhhab: str | None

    era: str | None

    discipline: str | None

    book_family: str | None

    parent_page_id: str | None

    parent_text: str | None

    @classmethod
    def from_passage(
        cls,
        passage: ScholarlyPassage,
    ) -> ShamelaPassageIdentity:
        metadata = passage.metadata

        required_keys = (
            "shamela_book_id",
            "shamela_page_id",
            "snapshot_id",
            "snapshot_sha256",
        )

        missing = tuple(
            key
            for key in required_keys
            if not metadata.get(
                key,
                "",
            ).strip()
        )

        if missing:
            raise ValueError(
                "Shamela passage missing structural provenance: " + ", ".join(missing)
            )

        sha256 = _validate_sha256(metadata["snapshot_sha256"])

        return cls(
            source_id=passage.source_id,
            book_id=metadata["shamela_book_id"],
            page_id=metadata["shamela_page_id"],
            snapshot_id=metadata["snapshot_id"],
            snapshot_sha256=sha256,
            edition=metadata.get("edition"),
            madhhab=metadata.get("madhhab"),
            era=metadata.get("era"),
            discipline=metadata.get("discipline"),
            book_family=metadata.get("book_family"),
            parent_page_id=(metadata.get("parent_page_id")),
            parent_text=metadata.get("parent_text"),
        )
