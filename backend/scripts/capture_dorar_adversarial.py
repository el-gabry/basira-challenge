from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

OUT = (
    ROOT
    / "data"
    / "competition"
    / "discovery"
    / "dorar"
    / "adversarial"
)

BASE_URL = "https://dorar.net/dorar_api.json"


CASES = [
    {
        "case_id": "weak_variant_phrase",
        "query": "اطلبوا العلم ولو بالصين",
        "expected_behavior":
            "preserve returned attribution and verdicts",
    },
    {
        "case_id": "nonce_no_hit",
        "query":
            "بصيرةاختبارعدموجودحديث987654321",
        "expected_behavior":
            "zero hits must not become a fabricated hadith",
    },
]


def fetch(query: str) -> bytes:
    url = (
        BASE_URL
        + "?"
        + urllib.parse.urlencode(
            {"skey": query}
        )
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Basira-Competition-Dorar-Audit/1",
            "Cache-Control":
                "no-cache",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        return response.read()


def main() -> None:
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest = []

    for index, case in enumerate(CASES):
        raw = fetch(
            case["query"]
        )

        # Provider contract should remain JSON.
        payload = json.loads(
            raw.decode("utf-8")
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise RuntimeError(
                f'{case["case_id"]}: '
                "top level is not object"
            )

        path = (
            OUT
            / f'{case["case_id"]}.json'
        )

        path.write_bytes(raw)

        manifest.append({
            **case,
            "file": str(
                path.relative_to(ROOT)
            ),
            "bytes": len(raw),
            "sha256":
                hashlib.sha256(
                    raw
                ).hexdigest(),
        })

        print(
            case["case_id"],
            "| bytes",
            len(raw),
            "| sha256",
            manifest[-1]["sha256"],
        )

        if index + 1 < len(CASES):
            time.sleep(1)

    manifest_path = (
        OUT / "cases.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
