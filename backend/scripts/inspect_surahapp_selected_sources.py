from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = (
    "https://dev.surahapp.com/api/v1"
)

SELECTED_SOURCES = (
    "tafsir-katheer",
    "tafsir-saadi",
    "tafsir-mokhtasar",
    "ayat-nozool",
)


def fetch(
    url: str,
) -> tuple[
    bytes,
    str,
    int,
]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "BasiraVerify/1.0 "
                "(trusted-source-inspection)"
            ),
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=45,
        ) as response:
            return (
                response.read(),
                response.headers.get(
                    "Content-Type",
                    "",
                ),
                response.status,
            )

    except urllib.error.HTTPError as exc:
        return (
            exc.read(),
            exc.headers.get(
                "Content-Type",
                "",
            ),
            exc.code,
        )

    except urllib.error.URLError as exc:
        return (
            str(exc).encode(
                "utf-8"
            ),
            "",
            0,
        )


def describe(
    value: Any,
    *,
    prefix: str = "root",
    depth: int = 0,
    max_depth: int = 4,
) -> None:
    indent = "  " * depth

    if depth > max_depth:
        return

    if isinstance(
        value,
        dict,
    ):
        print(
            f"{indent}{prefix}: "
            f"dict keys="
            f"{list(value.keys())}"
        )

        for key, child in value.items():
            if isinstance(
                child,
                (dict, list),
            ):
                describe(
                    child,
                    prefix=str(key),
                    depth=depth + 1,
                    max_depth=max_depth,
                )

    elif isinstance(
        value,
        list,
    ):
        print(
            f"{indent}{prefix}: "
            f"list count={len(value)}"
        )

        if value:
            describe(
                value[0],
                prefix="[0]",
                depth=depth + 1,
                max_depth=max_depth,
            )

    else:
        print(
            f"{indent}{prefix}: "
            f"{type(value).__name__}"
        )


def inspect_endpoint(
    *,
    name: str,
    url: str,
    output_path: Path,
) -> None:
    print()
    print("-" * 88)
    print(name)
    print(url)

    raw, content_type, status = fetch(
        url
    )

    print(
        "HTTP STATUS:",
        status,
    )

    print(
        "CONTENT-TYPE:",
        content_type,
    )

    output_path.write_bytes(
        raw
    )

    if not (
        200 <= status < 300
    ):
        print(
            "HTTP REQUEST: FAIL"
        )

        print(
            "BODY PREFIX:",
            repr(
                raw[:1000]
            ),
        )

        return

    try:
        payload = json.loads(
            raw.decode("utf-8")
        )
    except json.JSONDecodeError as exc:
        print(
            "JSON: FAIL",
            exc,
        )

        print(
            "PREFIX:",
            repr(raw[:500]),
        )

        return

    print("JSON: PASS")

    describe(
        payload
    )

    print()
    print(
        "PREVIEW:"
    )

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )[:2500]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for slug in SELECTED_SOURCES:
        source_root = (
            args.output_dir
            / slug
        )

        source_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        print()
        print("=" * 88)
        print(
            "SOURCE:",
            slug,
        )
        print("=" * 88)

        inspect_endpoint(
            name="PROJECT METADATA",
            url=(
                f"{BASE_URL}/project/"
                f"{slug}"
            ),
            output_path=(
                source_root
                / "project.json"
            ),
        )

        inspect_endpoint(
            name="AYA 1:1",
            url=(
                f"{BASE_URL}/aya/"
                f"{slug}/1/1"
            ),
            output_path=(
                source_root
                / "aya-1-1.json"
            ),
        )

        inspect_endpoint(
            name="SURA 1",
            url=(
                f"{BASE_URL}/sura/"
                f"{slug}/1"
            ),
            output_path=(
                source_root
                / "sura-1.json"
            ),
        )

        inspect_endpoint(
            name="SURA RANGE 1-2",
            url=(
                f"{BASE_URL}/sura/"
                f"{slug}/1/2"
            ),
            output_path=(
                source_root
                / "sura-1-2.json"
            ),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
