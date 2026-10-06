from __future__ import annotations

import pytest

from basira.models.scholarly import (
    ScholarlyDomain,
)
from basira.sources.shamela.contracts import (
    ShamelaCorpusManifest,
    ShamelaPassageIdentity,
    ShamelaPassageRecord,
)

HASH = "a" * 64


def test_record_preserves_structural_provenance() -> None:
    record = ShamelaPassageRecord(
        source_id="shamela-hanafi",
        source_version="v1",
        snapshot_id="fixture-v1",
        snapshot_sha256=HASH,
        book_id="book-1",
        page_id="page-10",
        domain=ScholarlyDomain.FIQH,
        work_title="كتاب فقهي",
        text="نص فقهي محفوظ",
        author_name="مؤلف",
        volume="2",
        page="15",
        edition="edition-1",
        madhhab="hanafi",
        era="classical",
        discipline="fiqh",
        book_family=("classical_fiqh"),
        parent_page_id="page-9",
        parent_text=("سياق الباب السابق"),
    )

    passage = record.to_scholarly_passage()

    identity = ShamelaPassageIdentity.from_passage(passage)

    assert passage.text == ("نص فقهي محفوظ")

    assert identity.book_id == "book-1"

    assert identity.madhhab == "hanafi"

    assert identity.parent_text == "سياق الباب السابق"

    assert identity.snapshot_sha256 == HASH


def test_invalid_snapshot_hash_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="SHA-256",
    ):
        ShamelaPassageRecord(
            source_id="source",
            source_version="v1",
            snapshot_id="snap",
            snapshot_sha256="bad",
            book_id="1",
            page_id="1",
            domain=(ScholarlyDomain.FIQH),
            work_title="book",
            text="text",
        )


def test_manifest_requires_sources() -> None:
    with pytest.raises(
        ValueError,
        match="source_ids",
    ):
        ShamelaCorpusManifest(
            corpus_id="corpus",
            snapshot_id="snapshot",
            snapshot_sha256=HASH,
            source_ids=(),
        )


def test_unknown_authority_is_not_invented() -> None:
    record = ShamelaPassageRecord(
        source_id="source",
        source_version="v1",
        snapshot_id="snap",
        snapshot_sha256=HASH,
        book_id="1",
        page_id="1",
        domain=ScholarlyDomain.FIQH,
        work_title="book",
        text="text",
    )

    passage = record.to_scholarly_passage()

    assert passage.author_name is None

    assert "authority_score" not in passage.metadata

    assert "religious_truth" not in passage.metadata
