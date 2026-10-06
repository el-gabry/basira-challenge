import json
from pathlib import Path


def test_tanzil_kfgqpc_audit_is_complete() -> None:
    path = Path(
        "data/audits/quran/"
        "tanzil-kfgqpc-orthography-v1.json"
    )

    audit = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        audit["references_compared"]
        == 6236
    )

    assert (
        audit["missing_from_source_a"]
        == 0
    )

    assert (
        audit["missing_from_source_b"]
        == 0
    )

    assert (
        audit["sequence_results"][
            "unresolved"
        ]
        == 0
    )

    assert audit["result"] == "PASS"

    assert (
        audit["integrity_status"]
        == "verified"
    )
