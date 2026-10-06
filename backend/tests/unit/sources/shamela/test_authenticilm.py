from __future__ import annotations

import hashlib
import json
from itertools import pairwise
from pathlib import Path

import pytest

from basira.sources.shamela.authenticilm import (
    AuthenticIlmShamelaParser,
)


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    digest.update(path.read_bytes())

    return digest.hexdigest()


def write_jsonl(
    path: Path,
    rows,
) -> None:
    path.write_text(
        "".join(
            json.dumps(
                row,
                ensure_ascii=False,
            )
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def tree_hash(
    root: Path,
) -> str:
    inventory = [
        (
            "manifest.json",
            sha256_file(root / "manifest.json"),
        )
    ]

    for filename in (
        "book_metadata.json",
        "pages.jsonl",
        "toc.jsonl",
    ):
        inventory.append(
            (
                filename,
                sha256_file(root / filename),
            )
        )

    inventory[1:] = sorted(inventory[1:])

    digest = hashlib.sha256()

    for filename, value in inventory:
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")

    return digest.hexdigest()


def fixture_book(
    tmp_path: Path,
    *,
    wrong_marker_page: bool = False,
) -> Path:
    root = tmp_path / "book"

    root.mkdir()

    metadata = {
        "book_id": "1",
        "title_ar": "كتاب تجريبي",
        "main_author_name_ar": ("مؤلف تجريبي"),
        "category_name_ar": ("الفقه الحنفي"),
        "is_hidden": False,
    }

    toc = [
        {
            "title_id": "t1",
            "book_id": "1",
            "page_id": "p1",
            "parent_id": None,
            "shamela_title_id": "1",
            "title_text": "كتاب البيوع",
        },
        {
            "title_id": "t2",
            "book_id": "1",
            "page_id": ("p2" if wrong_marker_page else "p1"),
            "parent_id": "t1",
            "shamela_title_id": "2",
            "title_text": "باب الصرف",
        },
        {
            "title_id": "t3",
            "book_id": "1",
            "page_id": "p2",
            "parent_id": "t1",
            "shamela_title_id": "3",
            "title_text": "فصل لاحق",
        },
    ]

    pages = [
        {
            "page_id": "p1",
            "book_id": "1",
            "shamela_page_id": "1",
            "part": "1",
            "page_num": "10",
            "sequence_num": "1",
            "body": (
                "تمهيد\r"
                "<span "
                "data-type='title' "
                "id=toc-1>"
                "كتاب البيوع"
                "</span>\r"
                "نص الكتاب\r"
                "<span "
                'data-type="title" '
                "id=toc-2>"
                "باب الصرف"
                "</span>\r"
                "نص الصرف"
            ),
            "footnotes": None,
        },
        {
            "page_id": "p2",
            "book_id": "1",
            "shamela_page_id": "2",
            "part": "1",
            "page_num": "11",
            "sequence_num": "2",
            "body": ("نص صفحة عنوان غير معلّم"),
            "footnotes": "هامش",
        },
        {
            "page_id": "p3",
            "book_id": "1",
            "shamela_page_id": "3",
            "part": "1",
            "page_num": "12",
            "sequence_num": "3",
            "body": ("نص الفصل التالي"),
            "footnotes": None,
        },
    ]

    (root / "book_metadata.json").write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    write_jsonl(
        root / "toc.jsonl",
        toc,
    )

    write_jsonl(
        root / "pages.jsonl",
        pages,
    )

    files = []

    for filename, rows in (
        (
            "book_metadata.json",
            None,
        ),
        (
            "toc.jsonl",
            len(toc),
        ),
        (
            "pages.jsonl",
            len(pages),
        ),
    ):
        path = root / filename

        entry = {
            "path": filename,
            "sha256": (sha256_file(path)),
            "bytes": (path.stat().st_size),
        }

        if rows is not None:
            entry["rows"] = rows

        files.append(entry)

    manifest = {
        "book_id": "1",
        "snapshot_id": ("fixture-snapshot"),
        "rejects": [],
        "files": files,
    }

    (root / "manifest.json").write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    acquisition = {
        "provider": ("fixture"),
        "dataset_repo": ("fixture/repo"),
        "dataset_revision": ("a" * 40),
        "relative_book_path": ("fiqh/book-1"),
        "book_id": "1",
        "manifest_sha256": (sha256_file(root / "manifest.json")),
        "raw_book_sha256": (tree_hash(root)),
    }

    (root / "acquisition.json").write_text(
        json.dumps(
            acquisition,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return root


def test_parser_uses_exact_inline_toc_boundaries(
    tmp_path: Path,
) -> None:
    root = fixture_book(tmp_path)

    result = AuthenticIlmShamelaParser().parse(root)

    assert result.audit.inline_marker_count == 2

    assert result.audit.inline_marker_mapped_count == 2

    assert result.audit.toc_without_inline_count == 1

    assert result.audit.volume_count == 1

    texts = tuple(span.raw_text for span in (result.hierarchy.spans))

    assert any("نص الصرف" in text for text in texts)

    target = next(
        span for span in (result.hierarchy.spans) if "نص الصرف" in span.raw_text
    )

    context = result.hierarchy.context_envelope(target.span_id)

    assert "كتاب البيوع" in context.ancestor_titles

    assert "باب الصرف" in context.ancestor_titles


def test_unmarked_toc_anchor_does_not_claim_anchor_page(
    tmp_path: Path,
) -> None:
    root = fixture_book(tmp_path)

    result = AuthenticIlmShamelaParser().parse(root)

    anchor_page_span = next(
        span for span in (result.hierarchy.spans) if ("نص صفحة عنوان" in span.raw_text)
    )

    next_page_span = next(
        span
        for span in (result.hierarchy.spans)
        if ("نص الفصل التالي" in span.raw_text)
    )

    anchor_context = result.hierarchy.context_envelope(anchor_page_span.span_id)

    next_context = result.hierarchy.context_envelope(next_page_span.span_id)

    assert "باب الصرف" in anchor_context.ancestor_titles

    assert "فصل لاحق" not in anchor_context.ancestor_titles

    assert "فصل لاحق" in next_context.ancestor_titles


def test_parser_preserves_source_derived_text(
    tmp_path: Path,
) -> None:
    root = fixture_book(tmp_path)

    result = AuthenticIlmShamelaParser().parse(root)

    assert any("\rنص الصرف" in span.raw_text for span in (result.hierarchy.spans))


def test_parser_fails_on_local_artifact_tamper(
    tmp_path: Path,
) -> None:
    root = fixture_book(tmp_path)

    with (root / "pages.jsonl").open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(" ")

    with pytest.raises(
        ValueError,
        match="SHA-256 mismatch",
    ):
        (AuthenticIlmShamelaParser().parse(root))


def test_parser_fails_on_marker_page_mismatch(
    tmp_path: Path,
) -> None:
    root = fixture_book(
        tmp_path,
        wrong_marker_page=True,
    )

    with pytest.raises(
        ValueError,
        match=("Inline title marker page mismatch"),
    ):
        (AuthenticIlmShamelaParser().parse(root))


def test_span_links_are_bidirectional_in_sequence(
    tmp_path: Path,
) -> None:
    root = fixture_book(tmp_path)

    result = AuthenticIlmShamelaParser().parse(root)

    spans = result.hierarchy.spans

    assert spans[0].previous_span_id is None

    assert spans[-1].next_span_id is None

    for previous, current in pairwise(spans):
        assert previous.next_span_id == current.span_id

        assert current.previous_span_id == previous.span_id
