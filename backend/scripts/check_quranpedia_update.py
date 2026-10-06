from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from basira.competition.source_trust import (
    ReleaseRelation,
    SourceUpdateSentinel,
)


ROOT = Path(__file__).resolve().parents[1]

PASSPORT = (
    ROOT
    / "data"
    / "competition"
    / "passports"
    / "quranpedia-hafs.json"
)

MANIFEST_URL = (
    "https://api.quranpedia.net/dumps/manifest.json"
)

TARGET = "mushafs-1.json.gz"


def walk(value: Any):
    if isinstance(value, dict):
        yield value

        for child in value.values():
            yield from walk(child)

    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def exact_artifact(
    manifest: dict[str, Any],
) -> dict[str, Any]:

    matches = [
        obj
        for obj in walk(manifest)
        if (
            isinstance(obj, dict)
            and obj.get("name") == TARGET
        )
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "expected exactly one Quranpedia Hafs artifact"
        )

    return matches[0]


def fetch_manifest() -> dict[str, Any]:
    request = urllib.request.Request(
        MANIFEST_URL,
        headers={
            "Cache-Control": "no-cache",
            "User-Agent":
                "Basira-Competition-Source-Sentinel/2",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=20,
    ) as response:
        return json.load(response)


def compare_release(
    governed: str,
    observed: str,
) -> ReleaseRelation:

    try:
        governed_date = date.fromisoformat(
            governed
        )

        observed_date = date.fromisoformat(
            observed
        )

    except ValueError:
        return ReleaseRelation.UNORDERED

    if observed_date > governed_date:
        return ReleaseRelation.NEWER

    if observed_date < governed_date:
        return ReleaseRelation.OLDER

    return ReleaseRelation.SAME


def main() -> None:
    passport = json.loads(
        PASSPORT.read_text(
            encoding="utf-8"
        )
    )

    manifest = fetch_manifest()

    artifact = exact_artifact(
        manifest
    )

    governed = passport[
        "current_governed_release"
    ]

    observed = manifest.get("version")

    if not observed:
        raise RuntimeError(
            "Quranpedia manifest has no version"
        )

    relation = compare_release(
        governed,
        observed,
    )

    result = SourceUpdateSentinel().assess(
        source_id=passport["source_id"],
        governed_release=governed,
        observed_release=observed,
        release_relation=relation,
        current_artifact_sha256=(
            passport["artifact"][
                "compressed_sha256"
            ]
        ),
        observed_artifact_sha256=(
            artifact.get("sha256")
        ),
    )

    output = result.model_dump(
        mode="json"
    )

    output["provider_artifact"] = TARGET
    output["provider_built_at"] = (
        artifact.get("built_at")
    )

    output["provider_declared_bytes"] = (
        artifact.get("bytes")
    )

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
