from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = (
    "https://dev.surahapp.com/api/v1"
)


def fetch_bytes(
    url: str,
) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "BasiraVerify/1.0 "
                "(trusted-source-discovery)"
            ),
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=45,
        ) as response:
            content_type = (
                response.headers.get(
                    "Content-Type",
                    "",
                )
            )

            payload = response.read()

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Failed to fetch {url}: {exc}"
        ) from exc

    print(
        "HTTP content type:",
        content_type,
    )

    return payload


def sha256_bytes(
    payload: bytes,
) -> str:
    return hashlib.sha256(
        payload
    ).hexdigest()


def print_json_shape(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 4,
    prefix: str = "root",
) -> None:
    if depth > max_depth:
        return

    indent = "  " * depth

    if isinstance(
        value,
        dict,
    ):
        print(
            f"{indent}{prefix}: "
            f"object keys="
            f"{list(value.keys())}"
        )

        for key, child in value.items():
            if isinstance(
                child,
                (dict, list),
            ):
                print_json_shape(
                    child,
                    depth=depth + 1,
                    max_depth=max_depth,
                    prefix=str(key),
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
            print_json_shape(
                value[0],
                depth=depth + 1,
                max_depth=max_depth,
                prefix="[0]",
            )

    else:
        print(
            f"{indent}{prefix}: "
            f"{type(value).__name__}"
        )


def iter_objects(
    value: Any,
):
    if isinstance(
        value,
        dict,
    ):
        yield value

        for child in value.values():
            yield from iter_objects(
                child
            )

    elif isinstance(
        value,
        list,
    ):
        for child in value:
            yield from iter_objects(
                child
            )


def looks_like_project(
    value: dict[str, Any],
) -> bool:
    interesting = {
        "slug",
        "name",
        "title",
        "type",
        "project_type",
        "projectType",
    }

    return bool(
        interesting
        & set(value)
    )


def print_project_candidates(
    payload: Any,
) -> None:
    candidates = [
        value
        for value in iter_objects(
            payload
        )
        if looks_like_project(
            value
        )
    ]

    print()
    print("=" * 88)
    print(
        "PROJECT CANDIDATES"
    )
    print("=" * 88)

    print(
        "Candidate objects:",
        len(candidates),
    )

    fields = (
        "id",
        "slug",
        "name",
        "title",
        "name_ar",
        "title_ar",
        "type",
        "project_type",
        "projectType",
        "description",
        "author",
        "author_name",
        "source",
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        print()
        print(
            f"[{index}]"
        )

        printed = False

        for field in fields:
            if field not in candidate:
                continue

            print(
                f"{field}:",
                candidate[field],
            )

            printed = True

        if not printed:
            print(
                json.dumps(
                    candidate,
                    ensure_ascii=False,
                    indent=2,
                )[:1500]
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    url = (
        args.base_url.rstrip("/")
        + "/projects"
    )

    print(
        "Fetching:",
        url,
    )

    raw = fetch_bytes(
        url
    )

    raw_path = (
        args.output_dir
        / "projects-raw.json"
    )

    raw_path.write_bytes(
        raw
    )

    try:
        payload = json.loads(
            raw.decode("utf-8")
        )
    except json.JSONDecodeError as exc:
        print(
            "Response is not valid JSON."
        )

        print(
            "Prefix:",
            repr(
                raw[:1000]
            ),
        )

        raise SystemExit(1) from exc

    normalized_path = (
        args.output_dir
        / "projects.json"
    )

    normalized_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest = {
        "provider": (
            "Surah App / "
            "Tafsir Center"
        ),
        "endpoint": url,
        "downloaded_at": (
            datetime.now(UTC)
            .isoformat()
        ),
        "sha256": (
            sha256_bytes(raw)
        ),
    }

    (
        args.output_dir
        / "projects-manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 88)
    print(
        "SURAH APP PROJECT DISCOVERY"
    )
    print("=" * 88)

    print(
        "SHA256:",
        manifest["sha256"],
    )

    print()
    print(
        "JSON SHAPE"
    )

    print_json_shape(
        payload
    )

    print_project_candidates(
        payload
    )

    print()
    print(
        "Saved:",
        normalized_path,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
