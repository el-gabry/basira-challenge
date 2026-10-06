from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SURAH_COUNT = 114
EXPECTED_HAFS_REFERENCE_COUNT = 6236


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def find_mushaf_root(
    value: Any,
) -> dict[str, Any] | None:
    """
    Locate the actual mushaf payload without assuming
    whether the provider wraps the JSON response.
    """
    if isinstance(value, dict):
        surahs = value.get("surahs")

        if (
            isinstance(surahs, list)
            and len(surahs) > 0
        ):
            return value

        for child in value.values():
            result = find_mushaf_root(child)

            if result is not None:
                return result

    elif isinstance(value, list):
        for child in value:
            result = find_mushaf_root(child)

            if result is not None:
                return result

    return None


def flatten_strings(
    value: Any,
) -> list[str]:
    result: list[str] = []

    if isinstance(value, str):
        if value.strip():
            result.append(value.strip())

    elif isinstance(value, dict):
        for child in value.values():
            result.extend(
                flatten_strings(child)
            )

    elif isinstance(value, list):
        for child in value:
            result.extend(
                flatten_strings(child)
            )

    return result


def audit_provider_attempts(
    raw_root: Path,
    output: Path,
) -> None:
    """
    Preserve source-drift / acquisition evidence.

    This is useful because an approved source family does
    not imply that every downloaded artifact is coherent
    with the provider manifest.
    """
    attempts = []

    for folder in sorted(raw_root.iterdir()):
        if not folder.is_dir():
            continue

        manifest_path = folder / "manifest.json"
        artifact_path = folder / "mushafs-1.json.gz"

        if not (
            manifest_path.exists()
            and artifact_path.exists()
        ):
            continue

        try:
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception as exc:
            attempts.append(
                {
                    "folder": folder.name,
                    "status": "MANIFEST_PARSE_FAILED",
                    "error": str(exc),
                }
            )
            continue

        expected = None
        entry = None

        def walk(value: Any):
            if isinstance(value, dict):
                yield value
                for child in value.values():
                    yield from walk(child)

            elif isinstance(value, list):
                for child in value:
                    yield from walk(child)

        for obj in walk(manifest):
            if not isinstance(obj, dict):
                continue

            if obj.get("name") == "mushafs-1.json.gz":
                entry = obj
                expected = obj.get("sha256")
                break

        actual = sha256(artifact_path)

        attempts.append(
            {
                "folder": folder.name,
                "manifest_version":
                    manifest.get("version"),
                "built_at":
                    entry.get("built_at")
                    if entry else None,
                "declared_bytes":
                    entry.get("bytes")
                    if entry else None,
                "actual_bytes":
                    artifact_path.stat().st_size,
                "expected_sha256":
                    expected,
                "actual_sha256":
                    actual,
                "sha_match":
                    expected == actual
                    if expected else False,
                "status":
                    "VERIFIED"
                    if expected == actual
                    else "QUARANTINED"
            }
        )

    output.write_text(
        json.dumps(
            {
                "source": "Quranpedia",
                "artifact": "mushafs-1.json.gz",
                "attempts": attempts,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--version",
        required=True,
    )

    args = parser.parse_args()

    version = args.version

    raw = (
        ROOT
        / "data"
        / "competition"
        / "raw"
        / "quranpedia"
        / version
    )

    normalized = (
        ROOT
        / "data"
        / "competition"
        / "normalized"
        / "quranpedia"
        / version
    )

    audit_dir = (
        ROOT
        / "data"
        / "competition"
        / "audits"
        / "quran"
    )

    manifest_dir = (
        ROOT
        / "data"
        / "competition"
        / "manifests"
        / "quran"
    )

    normalized.mkdir(
        parents=True,
        exist_ok=True,
    )

    audit_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    provider_manifest = raw / "manifest.json"
    compressed = raw / "mushafs-1.json.gz"
    verification = raw / "verification-result.json"

    for path in (
        provider_manifest,
        compressed,
        verification,
    ):
        if not path.exists():
            raise RuntimeError(
                f"missing required artifact: {path}"
            )

    verify = json.loads(
        verification.read_text(
            encoding="utf-8"
        )
    )

    if verify.get("sha_match") is not True:
        raise RuntimeError(
            "provider SHA256 is not verified"
        )

    if verify.get("size_match") is not True:
        raise RuntimeError(
            "provider byte size is not verified"
        )

    if (
        verify.get("provider_version")
        != version
    ):
        raise RuntimeError(
            "provider release identity mismatch"
        )

    expected_sha = verify[
        "expected_sha256"
    ]

    current_sha = sha256(compressed)

    if current_sha != expected_sha:
        raise RuntimeError(
            "artifact changed after provider verification"
        )

    snapshot = normalized / "mushafs-1.json"

    with gzip.open(
        compressed,
        "rb",
    ) as src:
        snapshot.write_bytes(
            src.read()
        )

    payload = json.loads(
        snapshot.read_text(
            encoding="utf-8"
        )
    )

    mushaf = find_mushaf_root(payload)

    if mushaf is None:
        raise RuntimeError(
            "could not locate Quran mushaf payload"
        )

    mushaf_id = mushaf.get("id")

    if mushaf_id != 1:
        raise RuntimeError(
            f"expected mushaf id 1; got {mushaf_id!r}"
        )

    surahs = mushaf.get("surahs")

    if not isinstance(surahs, list):
        raise RuntimeError(
            "surahs collection missing"
        )

    if len(surahs) != EXPECTED_SURAH_COUNT:
        raise RuntimeError(
            f"expected 114 surahs; got {len(surahs)}"
        )

    surah_ids = [
        int(s["id"])
        for s in surahs
    ]

    if surah_ids != list(range(1, 115)):
        raise RuntimeError(
            "surah IDs are not exactly 1..114"
        )

    rawi = mushaf.get("rawi") or {}
    qiraa = (
        rawi.get("qiraa")
        if isinstance(rawi, dict)
        else {}
    ) or {}

    # Witness identity is verified from the independently
    # hashed, same-release Quranpedia mushaf index artifact.
    #
    # Do NOT infer qiraa identity from rawi.full_name:
    # rawi.full_name is the narrator's biographical name.
    identity_path = (
        raw / "mushaf-1-witness-identity.json"
    )

    if not identity_path.exists():
        raise RuntimeError(
            "verified witness identity metadata is missing"
        )

    identity = json.loads(
        identity_path.read_text(encoding="utf-8")
    )

    if identity.get("mushaf_id") != 1:
        raise RuntimeError(
            "witness metadata mushaf identity mismatch"
        )

    riwaya_identity = identity.get("riwaya") or {}
    qiraa_identity = identity.get("qiraa") or {}

    if riwaya_identity.get("rawi_name") != "حفص":
        raise RuntimeError(
            "normalized witness metadata does not identify Hafs"
        )

    if qiraa_identity.get("short_name") != "عاصم":
        raise RuntimeError(
            "normalized qiraa metadata does not identify Asim"
        )

    # Bind normalized identity back to the exact metadata artifact.
    index_artifact = raw / "mushafs-index.json.gz"

    if not index_artifact.exists():
        raise RuntimeError(
            "verified mushaf index artifact is missing"
        )

    index_sha = hashlib.sha256(
        index_artifact.read_bytes()
    ).hexdigest()

    if identity.get("metadata_sha256") != index_sha:
        raise RuntimeError(
            "witness identity metadata is not bound to "
            "the current verified index artifact"
        )

    refs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    duplicates = []
    empty_text = []
    non_contiguous = []

    global_hafs_numbers = []

    for surah in surahs:
        sid = int(surah["id"])

        ayahs = surah.get("ayahs") or []

        observed_numbers = []

        for ayah in ayahs:
            number = int(
                ayah["number"]
            )

            observed_numbers.append(number)

            ref = (sid, number)

            if ref in seen:
                duplicates.append(ref)

            seen.add(ref)
            refs.append(ref)

            text = str(
                ayah.get("text") or ""
            ).strip()

            if not text:
                empty_text.append(ref)

            # Quranpedia number_in_hafs is a list
            # of SURAH-LOCAL Hafs ayah numbers.
            #
            # For Mushaf 1 the corpus-wide audit proves:
            # - exactly one mapping per ayah;
            # - mapped Hafs number equals local ayah number.
            hafs_numbers = ayah.get(
                "number_in_hafs"
            )

            if not isinstance(
                hafs_numbers,
                list,
            ):
                raise RuntimeError(
                    "number_in_hafs must be a list"
                )

            if len(hafs_numbers) != 1:
                raise RuntimeError(
                    "Hafs witness must have exactly "
                    "one local Hafs reference per ayah"
                )

            hafs_number = hafs_numbers[0]

            if isinstance(
                hafs_number,
                bool,
            ):
                raise RuntimeError(
                    "invalid boolean Hafs reference"
                )

            try:
                normalized_hafs_number = int(
                    hafs_number
                )
            except (
                TypeError,
                ValueError,
            ) as exc:
                raise RuntimeError(
                    "invalid number_in_hafs value"
                ) from exc

            if (
                normalized_hafs_number
                != number
            ):
                raise RuntimeError(
                    "Hafs reference does not match "
                    "the local ayah number"
                )

            global_hafs_numbers.append(
                (
                    sid,
                    normalized_hafs_number,
                )
            )

        expected_numbers = list(
            range(
                1,
                len(observed_numbers) + 1,
            )
        )

        if observed_numbers != expected_numbers:
            non_contiguous.append(
                {
                    "surah": sid,
                    "observed":
                        observed_numbers[:20],
                }
            )

    if duplicates:
        raise RuntimeError(
            f"duplicate refs: {duplicates[:10]}"
        )

    if empty_text:
        raise RuntimeError(
            f"empty Quran text: {empty_text[:10]}"
        )

    if non_contiguous:
        raise RuntimeError(
            "non-contiguous ayah numbering found"
        )

    observed_count = len(refs)

    if (
        observed_count
        != EXPECTED_HAFS_REFERENCE_COUNT
    ):
        raise RuntimeError(
            "Hafs reference coverage mismatch: "
            f"{observed_count} != "
            f"{EXPECTED_HAFS_REFERENCE_COUNT}"
        )

    hafs_number_check = "NOT_PRESENT"

    if global_hafs_numbers:
        if (
            len(global_hafs_numbers)
            != EXPECTED_HAFS_REFERENCE_COUNT
        ):
            raise RuntimeError(
                "number_in_hafs coverage incomplete"
            )

        if (
            len(set(global_hafs_numbers))
            != EXPECTED_HAFS_REFERENCE_COUNT
        ):
            raise RuntimeError(
                "duplicate (surah, Hafs ayah) references"
            )

        if (
            set(global_hafs_numbers)
            != set(refs)
        ):
            raise RuntimeError(
                "Hafs reference mapping does not exactly "
                "match the canonical local ayah references"
            )

        hafs_number_check = "PASS"

    snapshot_sha = sha256(snapshot)

    rawi_name = riwaya_identity["rawi_name"]
    rawi_full = riwaya_identity["rawi_full_name"]
    qiraa_name = qiraa_identity["short_name"]

    audit_id = (
        f"quranpedia-hafs-{version}-audit"
    )

    audit = {
        "audit_id": audit_id,
        "source_id": "quranpedia:mushaf:1",
        "provider": "Quranpedia",
        "provider_release": version,

        "witness": {
            "mushaf_id": mushaf_id,
            "name": mushaf.get("name"),
            "rawi_name": rawi_name,
            "rawi_full_name": rawi_full,
            "qiraa": qiraa_name,
            "riwaya": "حفص عن عاصم",

            # Deliberately unknown until separately
            # attested from source metadata.
            "rasm_standard": None,
            "dabt_standard": None,
            "edition": None,
        },

        "artifact": {
            "compressed_sha256":
                current_sha,
            "snapshot_sha256":
                snapshot_sha,
            "compressed_bytes":
                compressed.stat().st_size,
            "snapshot_bytes":
                snapshot.stat().st_size,
        },

        "structure": {
            "surah_count":
                len(surahs),
            "ayah_reference_count":
                observed_count,
            "unique_reference_count":
                len(seen),
            "empty_text_count":
                len(empty_text),
            "duplicate_reference_count":
                len(duplicates),
            "number_in_hafs_check":
                hafs_number_check,
        },

        "checks": {
            "provider_release_identity":
                "PASS",
            "provider_sha256":
                "PASS",
            "provider_byte_size":
                "PASS",
            "mushaf_identity":
                "PASS",
            "rawi_identity":
                "PASS",
            "qiraa_identity":
                "PASS",
            "surah_coverage":
                "PASS",
            "ayah_reference_coverage":
                "PASS",
            "ayah_number_continuity":
                "PASS",
            "unique_references":
                "PASS",
            "non_empty_quran_text":
                "PASS",
        },

        "trust_levels": {
            "source_family_eligibility":
                "VERIFIED",
            "artifact_integrity":
                "VERIFIED",
            "structural_integrity":
                "VERIFIED",
            "witness_identity":
                "VERIFIED",
            "cross_source_attestation":
                "PENDING",
            "rasm_identity":
                "UNRESOLVED",
            "dabt_identity":
                "UNRESOLVED",
        },

        "runtime_admission":
            "ELIGIBLE",
    }

    audit_path = (
        audit_dir
        / f"quranpedia-hafs-{version}.json"
    )

    audit_path.write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    governance = {
        "source_id":
            "quranpedia:mushaf:1",

        "name":
            mushaf.get("name"),

        "role":
            "quran",

        "provider":
            "Quranpedia",

        "provider_release":
            version,

        "official_reference_basis":
            "Approved Quran source family in the competition scientific reference.",

        "witness":
            audit["witness"],

        "snapshot": {
            "path":
                str(
                    snapshot.relative_to(ROOT)
                ),
            "sha256":
                snapshot_sha,
            "compressed_sha256":
                current_sha,
            "record_count":
                observed_count,
        },

        "audit_ids": [
            audit_id
        ],

        "runtime": {
            "status":
                "ELIGIBLE",
            "eligible":
                True,

            # This is an additional trust level,
            # not falsely claimed as complete.
            "cross_source_attestation":
                "PENDING",
        },
    }

    governance_path = (
        manifest_dir
        / f"quranpedia-hafs-{version}.json"
    )

    governance_path.write_text(
        json.dumps(
            governance,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    audit_provider_attempts(
        ROOT
        / "data"
        / "competition"
        / "raw"
        / "quranpedia",
        audit_dir
        / "quranpedia-acquisition-history.json",
    )

    print(
        "============================================"
    )
    print("QURAN WITNESS AUDIT PASSED")
    print(
        "============================================"
    )
    print("release:", version)
    print("mushaf:", mushaf.get("name"))
    print("rawi:", rawi_full or rawi_name)
    print("qiraa:", qiraa_name)
    print("surahs:", len(surahs))
    print("ayah refs:", observed_count)
    print("snapshot sha256:", snapshot_sha)
    print()
    print("artifact integrity : VERIFIED")
    print("structure          : VERIFIED")
    print("witness identity   : VERIFIED")
    print("rasm identity      : UNRESOLVED")
    print("dabt identity      : UNRESOLVED")
    print("cross-source       : PENDING")
    print("runtime            : ELIGIBLE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
