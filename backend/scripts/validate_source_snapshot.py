from __future__ import annotations

import argparse
import json
from pathlib import Path

from basira.models.source_snapshot import (
    SourceSnapshot,
)
from basira.sources.snapshot_validation import (
    validate_source_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate local source artifacts "
            "against a Basira snapshot manifest."
        )
    )

    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--snapshot-root",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    payload = json.loads(
        args.manifest.read_text(
            encoding="utf-8"
        )
    )

    snapshot = (
        SourceSnapshot.model_validate(
            payload
        )
    )

    report = validate_source_snapshot(
        snapshot,
        snapshot_root=(
            args.snapshot_root
        ),
    )

    print(
        "Source:",
        report.source_id,
    )
    print(
        "Revision:",
        report.revision,
    )
    print(
        "Artifacts:",
        report.artifact_count,
    )

    for result in report.artifacts:
        status = (
            "OK"
            if result.valid
            else "FAIL"
        )

        print(
            f"{status:4} "
            f"{result.artifact.path}"
        )

    if not report.valid:
        print()
        print(
            "SNAPSHOT VALIDATION: FAIL"
        )

        return 1

    print()
    print(
        "SNAPSHOT VALIDATION: PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
