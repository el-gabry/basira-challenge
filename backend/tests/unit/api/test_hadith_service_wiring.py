from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from basira.api import service


def test_hadith_runtime_is_optional_when_root_is_unset(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "BASIRA_HADEETHENC_ROOT",
        raising=False,
    )

    def unexpected_builder(
        root: Path,
    ) -> object:
        del root

        raise AssertionError(
            "Hadith builder must not run "
            "when the root is not configured."
        )

    monkeypatch.setattr(
        service,
        "build_default_hadith_retriever",
        unexpected_builder,
    )

    assert (
        service._configured_hadith_retriever()
        is None
    )


def test_hadith_runtime_uses_configured_root(
    monkeypatch,
    tmp_path,
) -> None:
    root = (
        tmp_path
        / "hadeethenc"
    )

    root.mkdir()

    sentinel = object()

    seen: list[Path] = []

    def fake_builder(
        configured_root: Path,
    ) -> object:
        seen.append(
            configured_root
        )

        return sentinel

    monkeypatch.setenv(
        "BASIRA_HADEETHENC_ROOT",
        str(root),
    )

    monkeypatch.setattr(
        service,
        "build_default_hadith_retriever",
        fake_builder,
    )

    result = (
        service._configured_hadith_retriever()
    )

    assert result is sentinel

    assert seen == [
        root.resolve()
    ]


def test_hadith_snapshot_validation_fails_closed(
    monkeypatch,
    tmp_path,
) -> None:
    root = (
        tmp_path
        / "hadeethenc"
    )

    root.mkdir()

    artifact = (
        root
        / "HadeethEnc.com_ar-v1.7.0.xlsx"
    )

    artifact.write_bytes(
        b"tampered"
    )

    snapshot_path = (
        tmp_path
        / "snapshot.json"
    )

    snapshot_path.write_text(
        json.dumps(
            {
                "source_id": (
                    "hadeethenc-official"
                ),
                "repository": (
                    "hadeethenc.com"
                ),
                "revision": (
                    "ar-v1.7.0+en-v1.25.0"
                ),
                "integrity_status": (
                    "verified_local_copy"
                ),
                "snapshot_manifest_sha256": None,
                "artifacts": [
                    {
                        "config": (
                            "ar-v1.7.0"
                        ),
                        "path": (
                            artifact.name
                        ),
                        "sha256": (
                            hashlib.sha256(
                                b"expected-other-bytes"
                            ).hexdigest()
                        ),
                        "size_bytes": (
                            artifact.stat().st_size
                        ),
                        "row_count": 1,
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        service,
        "DEFAULT_HADEETHENC_SNAPSHOT",
        snapshot_path,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "HadeethEnc snapshot "
            "validation failed"
        ),
    ):
        service.build_default_hadith_retriever(
            root
        )


def test_hadith_manifest_version_must_match_snapshot(
    monkeypatch,
    tmp_path,
) -> None:
    manifest_payload = json.loads(
        service.DEFAULT_HADEETHENC_MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    manifest_payload["version"] = (
        "ar-v0.0.0+en-v0.0.0"
    )

    manifest_path = (
        tmp_path
        / "manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        service,
        "DEFAULT_HADEETHENC_MANIFEST",
        manifest_path,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "manifest version and "
            "snapshot revision do not match"
        ),
    ):
        service.build_default_hadith_retriever(
            tmp_path
        )
