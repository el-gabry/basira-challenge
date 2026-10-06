from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum

from basira.models.scholarly import (
    ScholarlyDomain,
    ScholarlyPassage,
)
from basira.sources.shamela.contracts import (
    ShamelaPassageRecord,
)


def _sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_id(
    *parts: str,
) -> str:
    canonical = "\x1f".join(part.strip() for part in parts)

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_nonblank(
    value: str,
    *,
    field_name: str,
) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")

    return value


class ShamelaStructureKind(StrEnum):
    BOOK = "book"
    VOLUME = "volume"
    KITAB = "kitab"
    BAB = "bab"
    SECTION = "section"
    PAGE = "page"


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaBookSnapshot:
    """
    One immutable full-book artifact imported into
    Basira's governed Shamela corpus.

    The outer corpus snapshot and the raw book artifact
    are intentionally separate hashes.

    source_snapshot_sha256:
        provenance of the containing acquisition
        snapshot.

    raw_book_sha256:
        exact bytes/content identity of this book
        artifact.
    """

    corpus_id: str

    source_id: str
    source_version: str

    source_snapshot_id: str
    source_snapshot_sha256: str

    book_id: str

    work_title: str

    raw_book_sha256: str

    domain: ScholarlyDomain

    author_name: str | None = None
    publisher: str | None = None
    edition: str | None = None
    source_url: str | None = None

    madhhab: str | None = None
    era: str | None = None
    discipline: str | None = None
    book_family: str | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            ("corpus_id", self.corpus_id),
            ("source_id", self.source_id),
            (
                "source_version",
                self.source_version,
            ),
            (
                "source_snapshot_id",
                self.source_snapshot_id,
            ),
            ("book_id", self.book_id),
            ("work_title", self.work_title),
        ):
            _require_nonblank(
                value,
                field_name=field_name,
            )

        for field_name, value in (
            (
                "source_snapshot_sha256",
                self.source_snapshot_sha256,
            ),
            (
                "raw_book_sha256",
                self.raw_book_sha256,
            ),
        ):
            normalized = value.strip().lower()

            if len(normalized) != 64 or any(
                char not in "0123456789abcdef" for char in normalized
            ):
                raise ValueError(f"{field_name} must be a 64-character SHA-256")

            object.__setattr__(
                self,
                field_name,
                normalized,
            )

    @property
    def book_key(
        self,
    ) -> str:
        return f"{self.source_id}:{self.book_id}:{self.source_version}"


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaStructureNode:
    """
    One structural location inside a full book.

    Structure nodes contain navigation metadata.
    They are not themselves evidence claims.
    """

    node_id: str

    book_id: str

    kind: ShamelaStructureKind

    ordinal: int

    title: str | None = None

    parent_id: str | None = None

    source_locator: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _require_nonblank(
            self.node_id,
            field_name="node_id",
        )

        _require_nonblank(
            self.book_id,
            field_name="book_id",
        )

        if self.ordinal < 0:
            raise ValueError("ordinal must be non-negative")

        if self.kind is ShamelaStructureKind.BOOK and self.parent_id is not None:
            raise ValueError("book node cannot have a parent")

    @classmethod
    def create(
        cls,
        *,
        book: ShamelaBookSnapshot,
        kind: ShamelaStructureKind,
        ordinal: int,
        title: str | None = None,
        parent_id: str | None = None,
        source_locator: str | None = None,
    ) -> ShamelaStructureNode:
        locator = source_locator or f"{kind.value}:{ordinal}"

        node_id = "shamela-node:" + _stable_id(
            book.source_snapshot_id,
            book.book_id,
            kind.value,
            locator,
            title or "",
        )

        return cls(
            node_id=node_id,
            book_id=book.book_id,
            kind=kind,
            ordinal=ordinal,
            title=title,
            parent_id=parent_id,
            source_locator=source_locator,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaEvidenceSpan:
    """
    Primary retrieval/evidence unit.

    raw_text is preserved exactly from the normalized
    source representation.

    The ID binds:
    - source snapshot;
    - book;
    - structural parent;
    - source locator;
    - ordinal;
    - exact raw-text hash.

    Therefore changing either location or source text
    creates a different evidence identity.
    """

    span_id: str

    book_id: str

    parent_id: str

    ordinal: int

    raw_text: str

    raw_text_sha256: str

    source_locator: str

    page_start: str | None = None
    page_end: str | None = None

    previous_span_id: str | None = None
    next_span_id: str | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            ("span_id", self.span_id),
            ("book_id", self.book_id),
            ("parent_id", self.parent_id),
            ("raw_text", self.raw_text),
            (
                "source_locator",
                self.source_locator,
            ),
        ):
            _require_nonblank(
                value,
                field_name=field_name,
            )

        if self.ordinal < 0:
            raise ValueError("ordinal must be non-negative")

        expected = _sha256_text(self.raw_text)

        if self.raw_text_sha256 != expected:
            raise ValueError("raw_text_sha256 does not match raw_text")

    @classmethod
    def create(
        cls,
        *,
        book: ShamelaBookSnapshot,
        parent_id: str,
        ordinal: int,
        raw_text: str,
        source_locator: str,
        page_start: str | None = None,
        page_end: str | None = None,
        previous_span_id: str | None = None,
        next_span_id: str | None = None,
    ) -> ShamelaEvidenceSpan:
        raw_hash = _sha256_text(raw_text)

        span_id = "shamela-span:" + _stable_id(
            book.source_snapshot_id,
            book.book_id,
            parent_id,
            source_locator,
            str(ordinal),
            raw_hash,
        )

        return cls(
            span_id=span_id,
            book_id=book.book_id,
            parent_id=parent_id,
            ordinal=ordinal,
            raw_text=raw_text,
            raw_text_sha256=raw_hash,
            source_locator=source_locator,
            page_start=page_start,
            page_end=page_end,
            previous_span_id=(previous_span_id),
            next_span_id=next_span_id,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ShamelaContextEnvelope:
    """
    Structural context surrounding one exact evidence
    span.

    The evidence text remains separate from its
    context so citation integrity is not blurred.
    """

    span_id: str

    ancestor_ids: tuple[
        str,
        ...,
    ]

    ancestor_titles: tuple[
        str,
        ...,
    ]

    previous_span_id: str | None

    next_span_id: str | None


class ShamelaBookHierarchy:
    """
    Validated in-memory structural representation of
    one complete governed book.

    This is storage/index independent.

    SQLite, FTS5, dense embeddings, rerankers, and
    future providers must consume this contract rather
    than redefine book structure.
    """

    def __init__(
        self,
        *,
        book: ShamelaBookSnapshot,
        nodes: tuple[
            ShamelaStructureNode,
            ...,
        ],
        spans: tuple[
            ShamelaEvidenceSpan,
            ...,
        ],
    ) -> None:
        self.book = book
        self.nodes = nodes
        self.spans = spans

        self._nodes_by_id = {node.node_id: node for node in nodes}

        self._spans_by_id = {span.span_id: span for span in spans}

        if len(self._nodes_by_id) != len(nodes):
            raise ValueError("Duplicate hierarchy node ID")

        if len(self._spans_by_id) != len(spans):
            raise ValueError("Duplicate evidence span ID")

        self._validate()

    def _validate(
        self,
    ) -> None:
        roots = tuple(
            node for node in self.nodes if node.kind is ShamelaStructureKind.BOOK
        )

        if len(roots) != 1:
            raise ValueError("Book hierarchy must contain exactly one BOOK root")

        for node in self.nodes:
            if node.book_id != self.book.book_id:
                raise ValueError("Hierarchy node belongs to a different book")

            if node.parent_id is None:
                continue

            if node.parent_id not in self._nodes_by_id:
                raise ValueError("Hierarchy node references missing parent")

        self._validate_cycles()

        for span in self.spans:
            if span.book_id != self.book.book_id:
                raise ValueError("Evidence span belongs to a different book")

            if span.parent_id not in self._nodes_by_id:
                raise ValueError("Evidence span references missing structural parent")

            if (
                span.previous_span_id is not None
                and span.previous_span_id not in self._spans_by_id
            ):
                raise ValueError("Evidence span references missing previous span")

            if (
                span.next_span_id is not None
                and span.next_span_id not in self._spans_by_id
            ):
                raise ValueError("Evidence span references missing next span")

    def _validate_cycles(
        self,
    ) -> None:
        for node in self.nodes:
            seen: set[str] = set()

            current = node

            while current.parent_id is not None:
                if current.node_id in seen:
                    raise ValueError("Cycle detected in book hierarchy")

                seen.add(current.node_id)

                current = self._nodes_by_id[current.parent_id]

    def require_node(
        self,
        node_id: str,
    ) -> ShamelaStructureNode:
        try:
            return self._nodes_by_id[node_id]
        except KeyError as exc:
            raise KeyError(f"Unknown hierarchy node: {node_id}") from exc

    def require_span(
        self,
        span_id: str,
    ) -> ShamelaEvidenceSpan:
        try:
            return self._spans_by_id[span_id]
        except KeyError as exc:
            raise KeyError(f"Unknown evidence span: {span_id}") from exc

    def ancestors(
        self,
        span_id: str,
    ) -> tuple[
        ShamelaStructureNode,
        ...,
    ]:
        span = self.require_span(span_id)

        chain: list[ShamelaStructureNode] = []

        current = self.require_node(span.parent_id)

        while True:
            chain.append(current)

            if current.parent_id is None:
                break

            current = self.require_node(current.parent_id)

        chain.reverse()

        return tuple(chain)

    def context_envelope(
        self,
        span_id: str,
    ) -> ShamelaContextEnvelope:
        span = self.require_span(span_id)

        ancestors = self.ancestors(span_id)

        return ShamelaContextEnvelope(
            span_id=span.span_id,
            ancestor_ids=tuple(node.node_id for node in ancestors),
            ancestor_titles=tuple(node.title for node in ancestors if node.title),
            previous_span_id=(span.previous_span_id),
            next_span_id=(span.next_span_id),
        )

    def to_passage_record(
        self,
        span_id: str,
    ) -> ShamelaPassageRecord:
        span = self.require_span(span_id)

        ancestors = self.ancestors(span_id)

        volume = self._nearest_title(
            ancestors,
            ShamelaStructureKind.VOLUME,
        )

        kitab = self._nearest_title(
            ancestors,
            ShamelaStructureKind.KITAB,
        )

        bab = self._nearest_title(
            ancestors,
            ShamelaStructureKind.BAB,
        )

        section = self._nearest_title(
            ancestors,
            ShamelaStructureKind.SECTION,
        )

        parent_text = self._parent_context_text(span)

        page = (
            span.page_start
            if span.page_end
            in {
                None,
                span.page_start,
            }
            else (f"{span.page_start}-{span.page_end}")
        )

        record = ShamelaPassageRecord(
            source_id=(self.book.source_id),
            source_version=(self.book.source_version),
            snapshot_id=(self.book.source_snapshot_id),
            snapshot_sha256=(self.book.source_snapshot_sha256),
            book_id=self.book.book_id,
            page_id=span.span_id,
            domain=self.book.domain,
            work_title=(self.book.work_title),
            text=span.raw_text,
            author_name=(self.book.author_name),
            publisher=(self.book.publisher),
            source_url=(self.book.source_url),
            section_title=(section or bab or kitab),
            chapter_title=(bab or kitab),
            volume=volume,
            page=page,
            edition=self.book.edition,
            madhhab=self.book.madhhab,
            era=self.book.era,
            discipline=(self.book.discipline),
            book_family=(self.book.book_family),
            parent_page_id=(span.parent_id),
            parent_text=parent_text,
        )

        return record

    def to_scholarly_passage(
        self,
        span_id: str,
    ) -> ScholarlyPassage:
        passage = self.to_passage_record(span_id).to_scholarly_passage()

        hierarchy_metadata = {
            "evidence_span_id": (span_id),
            "raw_book_sha256": (self.book.raw_book_sha256),
            "corpus_id": (self.book.corpus_id),
        }

        span = self.require_span(span_id)

        hierarchy_metadata.update(
            {
                "raw_text_sha256": (span.raw_text_sha256),
                "source_locator": (span.source_locator),
                "structural_parent_id": (span.parent_id),
            }
        )

        return passage.model_copy(
            update={
                "passage_id": span_id,
                "metadata": {
                    **passage.metadata,
                    **hierarchy_metadata,
                },
            }
        )

    @staticmethod
    def _nearest_title(
        ancestors: tuple[
            ShamelaStructureNode,
            ...,
        ],
        kind: ShamelaStructureKind,
    ) -> str | None:
        for node in reversed(ancestors):
            if node.kind is kind and node.title:
                return node.title

        return None

    def _parent_context_text(
        self,
        span: ShamelaEvidenceSpan,
    ) -> str | None:
        parent = self.require_node(span.parent_id)

        return parent.title
