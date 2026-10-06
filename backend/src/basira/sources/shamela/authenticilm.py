from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from basira.models.scholarly import ScholarlyDomain
from basira.sources.shamela.hierarchy import (
    ShamelaBookHierarchy,
    ShamelaBookSnapshot,
    ShamelaEvidenceSpan,
    ShamelaStructureKind,
    ShamelaStructureNode,
)

_REQUIRED_FILES = (
    "book_metadata.json",
    "pages.jsonl",
    "toc.jsonl",
)


_CATEGORY_MAP = {
    "الفقه الحنفي": (
        ScholarlyDomain.FIQH,
        "hanafi",
    ),
    "الفقه المالكي": (
        ScholarlyDomain.FIQH,
        "maliki",
    ),
    "الفقه الشافعي": (
        ScholarlyDomain.FIQH,
        "shafii",
    ),
    "الفقه الحنبلي": (
        ScholarlyDomain.FIQH,
        "hanbali",
    ),
}


_TITLE_SPAN_RE = re.compile(
    r"<span\b(?P<attrs>[^>]*)>"
    r"(?P<title>.*?)"
    r"</span\s*>",
    flags=(re.IGNORECASE | re.DOTALL),
)


def _attribute(
    attrs: str,
    name: str,
) -> str | None:
    pattern = re.compile(
        rf"(?:^|\s)"
        rf"{re.escape(name)}"
        r"\s*=\s*"
        r"(?:"
        r'"([^"]*)"'
        r"|"
        r"'([^']*)'"
        r"|"
        r"([^\s>]+)"
        r")",
        flags=re.IGNORECASE,
    )

    match = pattern.search(attrs)

    if match is None:
        return None

    return next(value for value in match.groups() if value is not None)


def _sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def _book_tree_sha256(
    book_dir: Path,
) -> str:
    inventory = [
        (
            "manifest.json",
            _sha256_file(book_dir / "manifest.json"),
        )
    ]

    for filename in sorted(_REQUIRED_FILES):
        inventory.append(
            (
                filename,
                _sha256_file(book_dir / filename),
            )
        )

    digest = hashlib.sha256()

    for filename, file_sha in inventory:
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha.encode("ascii"))
        digest.update(b"\n")

    return digest.hexdigest()


def _json(
    path: Path,
) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(
    path: Path,
) -> tuple[dict, ...]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return tuple(json.loads(line) for line in handle if line.strip())


def _required_text(
    mapping: dict,
    key: str,
) -> str:
    value = mapping.get(key)

    if value is None:
        raise ValueError(f"Missing required field: {key}")

    text = str(value).strip()

    if not text:
        raise ValueError(f"Blank required field: {key}")

    return text


def _optional_text(
    value: object,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _normalized_space(
    value: str,
) -> str:
    return " ".join(value.split())


class _VisibleTextParser(HTMLParser):
    def __init__(
        self,
    ) -> None:
        super().__init__(convert_charrefs=True)

        self.parts: list[str] = []

    def handle_data(
        self,
        data: str,
    ) -> None:
        self.parts.append(data)

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:
        del attrs

        if tag.lower() in {
            "br",
            "p",
            "div",
            "li",
        }:
            self.parts.append("\n")

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if tag.lower() in {
            "p",
            "div",
            "li",
        }:
            self.parts.append("\n")


def _visible_text(
    fragment: str,
) -> str:
    parser = _VisibleTextParser()

    parser.feed(fragment)

    parser.close()

    return "".join(parser.parts)


@dataclass(
    frozen=True,
    slots=True,
)
class _InlineTitleMarker:
    shamela_title_id: str

    start: int
    end: int

    title_text: str


def _inline_title_markers(
    body: str,
) -> tuple[
    _InlineTitleMarker,
    ...,
]:
    markers = []

    for match in _TITLE_SPAN_RE.finditer(body):
        attrs = match.group("attrs")

        if (
            _attribute(
                attrs,
                "data-type",
            )
            or ""
        ).strip().lower() != "title":
            continue

        marker_id = (
            _attribute(
                attrs,
                "id",
            )
            or ""
        ).strip()

        id_match = re.fullmatch(
            r"toc-(\d+)",
            marker_id,
        )

        if id_match is None:
            continue

        markers.append(
            _InlineTitleMarker(
                shamela_title_id=(id_match.group(1)),
                start=match.start(),
                end=match.end(),
                title_text=(_visible_text(match.group("title"))),
            )
        )

    return tuple(markers)


def _structure_kind(
    title: str,
) -> ShamelaStructureKind:
    normalized = _normalized_space(title)

    if normalized.startswith("كتاب "):
        return ShamelaStructureKind.KITAB

    if normalized.startswith("باب "):
        return ShamelaStructureKind.BAB

    return ShamelaStructureKind.SECTION


def _title_order(
    item: dict,
    fallback: int,
) -> tuple[int, int]:
    raw = str(
        item.get(
            "shamela_title_id",
            "",
        )
    )

    if raw.isdigit():
        return (
            int(raw),
            fallback,
        )

    return (
        10**12,
        fallback,
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AuthenticIlmParseAudit:
    page_count: int

    toc_count: int

    volume_count: int

    span_count: int

    inline_marker_count: int

    inline_marker_mapped_count: int

    pages_with_inline_markers: int

    toc_without_inline_count: int

    fallback_anchor_pages: int

    ambiguous_fallback_pages: int

    normalized_title_mismatches: int

    pages_with_footnotes: int

    unattributed_span_count: int


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAuthenticIlmBook:
    hierarchy: ShamelaBookHierarchy

    audit: AuthenticIlmParseAudit


class AuthenticIlmShamelaParser:
    """
    Parse one fully acquired AuthenticIlm Shamela4
    book into Basira's governed hierarchy contract.

    Structural policy
    -----------------
    * page sequence is the canonical text order;
    * toc.jsonl is the canonical structural catalog;
    * inline ``toc-N`` markers are exact intra-page
      boundaries;
    * an unmarked TOC entry never retroactively claims
      text on its anchor page;
    * unmarked page anchors may establish context for
      following pages only;
    * title-text similarity is never used for identity.

    This parser performs no semantic inference and no
    religious judgment.
    """

    def parse(
        self,
        book_dir: Path,
    ) -> ParsedAuthenticIlmBook:
        book_dir = Path(book_dir)

        self._require_files(book_dir)

        manifest = _json(book_dir / "manifest.json")

        metadata = _json(book_dir / "book_metadata.json")

        acquisition = _json(book_dir / "acquisition.json")

        pages = _jsonl(book_dir / "pages.jsonl")

        toc = _jsonl(book_dir / "toc.jsonl")

        (
            manifest_sha,
            raw_book_sha,
        ) = self._verify_integrity(
            book_dir=book_dir,
            manifest=manifest,
            metadata=metadata,
            acquisition=acquisition,
            pages=pages,
            toc=toc,
        )

        (
            domain,
            madhhab,
        ) = self._classify(metadata)

        book = self._book_snapshot(
            manifest=manifest,
            metadata=metadata,
            acquisition=acquisition,
            manifest_sha=manifest_sha,
            raw_book_sha=raw_book_sha,
            domain=domain,
            madhhab=madhhab,
        )

        (
            nodes,
            root,
            volume_nodes,
            toc_node_by_title_id,
            toc_node_by_shamela_id,
        ) = self._build_nodes(
            book=book,
            pages=pages,
            toc=toc,
        )

        (
            spans,
            metrics,
        ) = self._build_spans(
            book=book,
            pages=pages,
            toc=toc,
            root=root,
            volume_nodes=(volume_nodes),
            toc_node_by_title_id=(toc_node_by_title_id),
            toc_node_by_shamela_id=(toc_node_by_shamela_id),
        )

        hierarchy = ShamelaBookHierarchy(
            book=book,
            nodes=nodes,
            spans=spans,
        )

        structural_parents = {
            root.node_id,
            *(node.node_id for node in volume_nodes.values()),
        }

        unattributed = sum(1 for span in spans if span.parent_id in structural_parents)

        audit = AuthenticIlmParseAudit(
            page_count=len(pages),
            toc_count=len(toc),
            volume_count=len(volume_nodes),
            span_count=len(spans),
            inline_marker_count=(metrics["inline_markers"]),
            inline_marker_mapped_count=(metrics["mapped_markers"]),
            pages_with_inline_markers=(metrics["pages_with_markers"]),
            toc_without_inline_count=(metrics["toc_without_inline"]),
            fallback_anchor_pages=(metrics["fallback_pages"]),
            ambiguous_fallback_pages=(metrics["ambiguous_pages"]),
            normalized_title_mismatches=(metrics["title_mismatches"]),
            pages_with_footnotes=(metrics["pages_with_footnotes"]),
            unattributed_span_count=(unattributed),
        )

        return ParsedAuthenticIlmBook(
            hierarchy=hierarchy,
            audit=audit,
        )

    @staticmethod
    def _require_files(
        book_dir: Path,
    ) -> None:
        required = {
            "manifest.json",
            "book_metadata.json",
            "toc.jsonl",
            "pages.jsonl",
            "acquisition.json",
        }

        missing = tuple(
            name for name in sorted(required) if not (book_dir / name).is_file()
        )

        if missing:
            raise ValueError("Missing Shamela acquisition files: " + ", ".join(missing))

    @staticmethod
    def _verify_integrity(
        *,
        book_dir: Path,
        manifest: dict,
        metadata: dict,
        acquisition: dict,
        pages: tuple[
            dict,
            ...,
        ],
        toc: tuple[
            dict,
            ...,
        ],
    ) -> tuple[str, str]:
        if manifest.get("rejects"):
            raise ValueError("Shamela manifest contains rejects")

        if metadata.get(
            "is_hidden",
            False,
        ):
            raise ValueError("Hidden Shamela book is not eligible for ingestion")

        manifest_book_id = _required_text(
            manifest,
            "book_id",
        )

        metadata_book_id = _required_text(
            metadata,
            "book_id",
        )

        acquisition_book_id = _required_text(
            acquisition,
            "book_id",
        )

        if (
            len(
                {
                    manifest_book_id,
                    metadata_book_id,
                    acquisition_book_id,
                }
            )
            != 1
        ):
            raise ValueError(
                "Book identity mismatch across manifest, metadata, and acquisition"
            )

        entries = {str(item["path"]): item for item in manifest.get("files", ())}

        for filename in _REQUIRED_FILES:
            entry = entries.get(filename)

            if entry is None:
                raise ValueError(f"Manifest missing governed file: {filename}")

            actual_sha = _sha256_file(book_dir / filename)

            expected_sha = (
                str(
                    entry.get(
                        "sha256",
                        "",
                    )
                )
                .strip()
                .lower()
            )

            if not expected_sha or actual_sha != expected_sha:
                raise ValueError(f"SHA-256 mismatch for {filename}")

            expected_bytes = entry.get("bytes")

            if expected_bytes is not None and (
                book_dir / filename
            ).stat().st_size != int(expected_bytes):
                raise ValueError(f"Byte-size mismatch for {filename}")

            if filename == "pages.jsonl":
                expected_rows = entry.get("rows")

                if expected_rows is not None and len(pages) != int(expected_rows):
                    raise ValueError("Page row-count mismatch")

            if filename == "toc.jsonl":
                expected_rows = entry.get("rows")

                if expected_rows is not None and len(toc) != int(expected_rows):
                    raise ValueError("TOC row-count mismatch")

        manifest_sha = _sha256_file(book_dir / "manifest.json")

        if (
            _required_text(
                acquisition,
                "manifest_sha256",
            ).lower()
            != manifest_sha
        ):
            raise ValueError(
                "Acquisition manifest SHA-256 does not match local manifest"
            )

        raw_book_sha = _book_tree_sha256(book_dir)

        if (
            _required_text(
                acquisition,
                "raw_book_sha256",
            ).lower()
            != raw_book_sha
        ):
            raise ValueError(
                "Acquisition raw-book SHA-256 does not match governed files"
            )

        page_ids = [
            _required_text(
                page,
                "page_id",
            )
            for page in pages
        ]

        if len(set(page_ids)) != len(page_ids):
            raise ValueError("Duplicate Shamela page_id")

        sequences = [
            int(
                _required_text(
                    page,
                    "sequence_num",
                )
            )
            for page in pages
        ]

        if sequences != list(
            range(
                1,
                len(pages) + 1,
            )
        ):
            raise ValueError("Shamela page sequence is not contiguous and canonical")

        page_id_set = set(page_ids)

        title_ids = [
            _required_text(
                item,
                "title_id",
            )
            for item in toc
        ]

        if len(set(title_ids)) != len(title_ids):
            raise ValueError("Duplicate TOC title_id")

        shamela_title_ids = [
            _required_text(
                item,
                "shamela_title_id",
            )
            for item in toc
        ]

        if len(set(shamela_title_ids)) != len(shamela_title_ids):
            raise ValueError("Duplicate TOC shamela_title_id")

        title_id_set = set(title_ids)

        for item in toc:
            page_id = _required_text(
                item,
                "page_id",
            )

            if page_id not in page_id_set:
                raise ValueError(f"TOC references missing page: {page_id}")

            parent = _optional_text(item.get("parent_id"))

            if parent is not None and parent not in title_id_set:
                raise ValueError(f"TOC references missing parent title: {parent}")

        return (
            manifest_sha,
            raw_book_sha,
        )

    @staticmethod
    def _classify(
        metadata: dict,
    ) -> tuple[
        ScholarlyDomain,
        str,
    ]:
        category = _normalized_space(
            _required_text(
                metadata,
                "category_name_ar",
            )
        )

        resolved = _CATEGORY_MAP.get(category)

        if resolved is None:
            raise ValueError(
                f"Unsupported Shamela category for governed fiqh parser: {category}"
            )

        return resolved

    @staticmethod
    def _book_snapshot(
        *,
        manifest: dict,
        metadata: dict,
        acquisition: dict,
        manifest_sha: str,
        raw_book_sha: str,
        domain: ScholarlyDomain,
        madhhab: str,
    ) -> ShamelaBookSnapshot:
        book_id = _required_text(
            metadata,
            "book_id",
        )

        dataset_repo = _required_text(
            acquisition,
            "dataset_repo",
        )

        revision = _required_text(
            acquisition,
            "dataset_revision",
        )

        relative_path = _required_text(
            acquisition,
            "relative_book_path",
        )

        quoted_path = urllib.parse.quote(
            relative_path,
            safe="/",
        )

        source_url = (
            "https://huggingface.co/"
            "datasets/"
            f"{dataset_repo}/tree/"
            f"{revision}/"
            f"{quoted_path}"
        )

        snapshot_id = _required_text(
            manifest,
            "snapshot_id",
        )

        return ShamelaBookSnapshot(
            corpus_id=(f"{dataset_repo}@{revision}"),
            source_id=(f"shamela4:{book_id}"),
            source_version=revision,
            source_snapshot_id=(f"{snapshot_id}:book:{book_id}"),
            source_snapshot_sha256=(manifest_sha),
            book_id=book_id,
            work_title=(
                _required_text(
                    metadata,
                    "title_ar",
                )
            ),
            raw_book_sha256=(raw_book_sha),
            domain=domain,
            author_name=(_optional_text(metadata.get("main_author_name_ar"))),
            source_url=source_url,
            madhhab=madhhab,
            discipline="fiqh",
            book_family=("classical_fiqh"),
        )

    @staticmethod
    def _build_nodes(
        *,
        book: ShamelaBookSnapshot,
        pages: tuple[
            dict,
            ...,
        ],
        toc: tuple[
            dict,
            ...,
        ],
    ) -> tuple[
        tuple[
            ShamelaStructureNode,
            ...,
        ],
        ShamelaStructureNode,
        dict[
            str,
            ShamelaStructureNode,
        ],
        dict[
            str,
            ShamelaStructureNode,
        ],
        dict[
            str,
            ShamelaStructureNode,
        ],
    ]:
        root = ShamelaStructureNode.create(
            book=book,
            kind=(ShamelaStructureKind.BOOK),
            ordinal=0,
            title=book.work_title,
            source_locator="book",
        )

        page_part = {
            _required_text(
                page,
                "page_id",
            ): _optional_text(page.get("part"))
            for page in pages
        }

        part_order = []

        for page in pages:
            part = _optional_text(page.get("part"))

            if part is not None and part not in part_order:
                part_order.append(part)

        volume_nodes = {}

        for index, part in enumerate(
            part_order,
            start=1,
        ):
            volume_nodes[part] = ShamelaStructureNode.create(
                book=book,
                kind=(ShamelaStructureKind.VOLUME),
                ordinal=index,
                title=(f"الجزء {part}"),
                parent_id=(root.node_id),
                source_locator=(f"part:{part}"),
            )

        provisional = {}

        for index, item in enumerate(
            toc,
            start=1,
        ):
            title_id = _required_text(
                item,
                "title_id",
            )

            title = _required_text(
                item,
                "title_text",
            )

            shamela_title_id = _required_text(
                item,
                "shamela_title_id",
            )

            provisional[title_id] = ShamelaStructureNode.create(
                book=book,
                kind=(_structure_kind(title)),
                ordinal=index,
                title=title,
                parent_id=(root.node_id),
                source_locator=("toc:" + shamela_title_id),
            )

        final_toc_nodes = []

        by_title_id = {}

        by_shamela_id = {}

        for index, item in enumerate(
            toc,
            start=1,
        ):
            title_id = _required_text(
                item,
                "title_id",
            )

            title = _required_text(
                item,
                "title_text",
            )

            shamela_title_id = _required_text(
                item,
                "shamela_title_id",
            )

            parent_title_id = _optional_text(item.get("parent_id"))

            if parent_title_id:
                parent_node_id = provisional[parent_title_id].node_id
            else:
                page_id = _required_text(
                    item,
                    "page_id",
                )

                part = page_part.get(page_id)

                volume = volume_nodes.get(part) if part is not None else None

                parent_node_id = volume.node_id if volume is not None else root.node_id

            node = ShamelaStructureNode.create(
                book=book,
                kind=(_structure_kind(title)),
                ordinal=index,
                title=title,
                parent_id=(parent_node_id),
                source_locator=("toc:" + shamela_title_id),
            )

            final_toc_nodes.append(node)

            by_title_id[title_id] = node

            by_shamela_id[shamela_title_id] = node

        nodes = (
            root,
            *volume_nodes.values(),
            *final_toc_nodes,
        )

        return (
            nodes,
            root,
            volume_nodes,
            by_title_id,
            by_shamela_id,
        )

    def _build_spans(
        self,
        *,
        book: ShamelaBookSnapshot,
        pages: tuple[
            dict,
            ...,
        ],
        toc: tuple[
            dict,
            ...,
        ],
        root: ShamelaStructureNode,
        volume_nodes: dict[
            str,
            ShamelaStructureNode,
        ],
        toc_node_by_title_id: dict[
            str,
            ShamelaStructureNode,
        ],
        toc_node_by_shamela_id: dict[
            str,
            ShamelaStructureNode,
        ],
    ) -> tuple[
        tuple[
            ShamelaEvidenceSpan,
            ...,
        ],
        dict[
            str,
            int,
        ],
    ]:
        del toc_node_by_title_id

        toc_by_shamela = {
            _required_text(
                item,
                "shamela_title_id",
            ): item
            for item in toc
        }

        toc_by_page: dict[
            str,
            list[
                tuple[
                    int,
                    dict,
                ]
            ],
        ] = {}

        for index, item in enumerate(toc):
            page_id = _required_text(
                item,
                "page_id",
            )

            toc_by_page.setdefault(
                page_id,
                [],
            ).append(
                (
                    index,
                    item,
                )
            )

        for entries in toc_by_page.values():
            entries.sort(
                key=lambda pair: _title_order(
                    pair[1],
                    pair[0],
                )
            )

        page_markers = {}

        marker_page = {}

        marker_titles = {}

        pages_with_markers = 0

        title_mismatches = 0

        for page in pages:
            page_id = _required_text(
                page,
                "page_id",
            )

            markers = _inline_title_markers(str(page.get("body") or ""))

            page_markers[page_id] = markers

            if markers:
                pages_with_markers += 1

            for marker in markers:
                marker_id = marker.shamela_title_id

                if marker_id in marker_page:
                    raise ValueError(f"Duplicate inline toc marker: toc-{marker_id}")

                toc_item = toc_by_shamela.get(marker_id)

                if toc_item is None:
                    raise ValueError(
                        f"Inline toc marker missing from TOC: toc-{marker_id}"
                    )

                toc_page_id = _required_text(
                    toc_item,
                    "page_id",
                )

                if toc_page_id != page_id:
                    raise ValueError(
                        f"Inline title marker page mismatch: toc-{marker_id}"
                    )

                marker_page[marker_id] = page_id

                marker_titles[marker_id] = marker.title_text

                if _normalized_space(marker.title_text) != _normalized_space(
                    _required_text(
                        toc_item,
                        "title_text",
                    )
                ):
                    title_mismatches += 1

        all_inline_ids = set(marker_page)

        toc_without_inline = [
            item
            for item in toc
            if _required_text(
                item,
                "shamela_title_id",
            )
            not in all_inline_ids
        ]

        fallback_by_page = {}

        for item in toc_without_inline:
            page_id = _required_text(
                item,
                "page_id",
            )

            fallback_by_page.setdefault(
                page_id,
                [],
            ).append(item)

        for page_id, items in fallback_by_page.items():
            source_entries = toc_by_page[page_id]

            order = {
                _required_text(
                    item,
                    "shamela_title_id",
                ): position
                for position, (
                    _,
                    item,
                ) in enumerate(source_entries)
            }

            items.sort(
                key=lambda item: order[
                    _required_text(
                        item,
                        "shamela_title_id",
                    )
                ]
            )

        ambiguous_pages = sum(
            1 for items in fallback_by_page.values() if len(items) > 1
        )

        seeds = []

        span_ordinal = 0

        active_parent = root.node_id

        active_part = None

        pages_with_footnotes = 0

        def append_fragment(
            *,
            fragment: str,
            page: dict,
            page_id: str,
            start: int,
            end: int,
            parent_id: str,
        ) -> None:
            nonlocal span_ordinal

            text = _visible_text(fragment)

            if not text.strip():
                return

            span_ordinal += 1

            page_number = (
                _optional_text(page.get("page_num"))
                or _optional_text(page.get("shamela_page_id"))
                or page_id
            )

            seeds.append(
                ShamelaEvidenceSpan.create(
                    book=book,
                    parent_id=(parent_id),
                    ordinal=(span_ordinal),
                    raw_text=text,
                    source_locator=(f"page:{page_id}:body:{start}:{end}"),
                    page_start=(page_number),
                    page_end=(page_number),
                )
            )

        for page in pages:
            page_id = _required_text(
                page,
                "page_id",
            )

            part = _optional_text(page.get("part"))

            if part != active_part:
                active_part = part

                volume = volume_nodes.get(part) if part is not None else None

                active_parent = volume.node_id if volume is not None else root.node_id

            if _optional_text(page.get("footnotes")):
                pages_with_footnotes += 1

            body = str(page.get("body") or "")

            markers = page_markers[page_id]

            cursor = 0

            for marker in markers:
                append_fragment(
                    fragment=body[cursor : marker.start],
                    page=page,
                    page_id=page_id,
                    start=cursor,
                    end=marker.start,
                    parent_id=(active_parent),
                )

                active_parent = toc_node_by_shamela_id[marker.shamela_title_id].node_id

                cursor = marker.end

            append_fragment(
                fragment=body[cursor:],
                page=page,
                page_id=page_id,
                start=cursor,
                end=len(body),
                parent_id=(active_parent),
            )

            # A source TOC anchor without an inline
            # offset cannot safely claim text earlier
            # on this page. It may establish context
            # for subsequent pages only.
            anchors = toc_by_page.get(page_id, [])

            if anchors:
                last_item = anchors[-1][1]

                last_id = _required_text(
                    last_item,
                    "shamela_title_id",
                )

                if last_id not in {marker.shamela_title_id for marker in markers}:
                    active_parent = toc_node_by_shamela_id[last_id].node_id

        if not seeds:
            raise ValueError("Shamela book produced no evidence spans")

        spans = []

        for index, seed in enumerate(seeds):
            previous_id = seeds[index - 1].span_id if index > 0 else None

            next_id = seeds[index + 1].span_id if index + 1 < len(seeds) else None

            spans.append(
                ShamelaEvidenceSpan(
                    span_id=seed.span_id,
                    book_id=seed.book_id,
                    parent_id=(seed.parent_id),
                    ordinal=(seed.ordinal),
                    raw_text=(seed.raw_text),
                    raw_text_sha256=(seed.raw_text_sha256),
                    source_locator=(seed.source_locator),
                    page_start=(seed.page_start),
                    page_end=(seed.page_end),
                    previous_span_id=(previous_id),
                    next_span_id=(next_id),
                )
            )

        metrics = {
            "inline_markers": len(marker_page),
            "mapped_markers": len(marker_page),
            "pages_with_markers": (pages_with_markers),
            "toc_without_inline": len(toc_without_inline),
            "fallback_pages": len(fallback_by_page),
            "ambiguous_pages": (ambiguous_pages),
            "title_mismatches": (title_mismatches),
            "pages_with_footnotes": (pages_with_footnotes),
        }

        return (
            tuple(spans),
            metrics,
        )
