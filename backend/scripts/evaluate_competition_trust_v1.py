from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import os
import sys
import time
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

BENCHMARK = (
    ROOT
    / "evaluation"
    / "competition"
    / "cases"
    / "trust_core_v1.json"
)

MANIFEST = (
    ROOT
    / "evaluation"
    / "competition"
    / "baselines"
    / "trust_core_v1_manifest.json"
)

OUTPUT = (
    ROOT
    / "evaluation"
    / "competition"
    / "results"
    / "trust_core_v1_preinnovation.json"
)


PASS = "PASS"
FAIL = "FAIL"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
NOT_EXECUTED = "NOT_EXECUTED"


def serialize(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, Enum):
        return value.value

    if hasattr(value, "model_dump"):
        return serialize(value.model_dump())

    if is_dataclass(value):
        return serialize(asdict(value))

    if isinstance(value, dict):
        return {
            str(k): serialize(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [serialize(v) for v in value]

    if isinstance(value, (str, int, float, bool)):
        return value

    if hasattr(value, "__dict__"):
        return {
            k: serialize(v)
            for k, v in vars(value).items()
            if not k.startswith("_")
        }

    return repr(value)


def optional_import(module: str) -> Any | None:
    try:
        return importlib.import_module(module)
    except ModuleNotFoundError:
        return None


def check_benchmark_integrity() -> dict[str, Any]:
    raw = BENCHMARK.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()

    manifest = json.loads(
        MANIFEST.read_text(encoding="utf-8")
    )

    expected = manifest["sha256"]

    if actual != expected:
        raise RuntimeError(
            "Frozen benchmark hash mismatch: "
            f"{actual} != {expected}"
        )

    return manifest


def capability(
    *,
    behavior: str,
    status: str,
    evidence: Any = None,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "behavior": behavior,
        "status": status,
        "evidence": serialize(evidence),
        "note": note,
    }


def inspect_competition_extensions() -> dict[str, bool]:
    return {
        "content_sensitivity": (
            optional_import(
                "basira.competition.sensitivity"
            )
            is not None
        ),
        "quran_witness_attestation": (
            optional_import(
                "basira.trust.quran_witness"
            )
            is not None
        ),
        "claim_evidence_semantics": (
            optional_import(
                "basira.trust.claim_evidence"
            )
            is not None
        ),
        "failure_certification": (
            optional_import(
                "basira.trust.failure"
            )
            is not None
        ),
        "safe_memory": (
            optional_import(
                "basira.learning.memory"
            )
            is not None
        ),
    }


def build_service() -> tuple[Any | None, str | None]:
    try:
        from basira.api.service import (
            build_default_query_service,
        )
    except Exception as exc:
        return None, f"import failure: {exc}"

    try:
        sig = inspect.signature(
            build_default_query_service
        )

        required = [
            p
            for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind
            not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )
        ]

        if required:
            return (
                None,
                "build_default_query_service "
                "requires arguments: "
                + ", ".join(p.name for p in required),
            )

        return build_default_query_service(), None

    except Exception as exc:
        return None, f"runtime construction failure: {exc}"


def execute_query(
    service: Any | None,
    question: str,
) -> tuple[Any | None, str | None]:
    if service is None:
        return None, "service unavailable"

    try:
        return service.execute(question=question), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def find_values(
    obj: Any,
    wanted_keys: set[str],
) -> list[Any]:
    found: list[Any] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() in wanted_keys:
                found.append(value)
            found.extend(
                find_values(value, wanted_keys)
            )

    elif isinstance(obj, list):
        for value in obj:
            found.extend(
                find_values(value, wanted_keys)
            )

    return found


def text_values(obj: Any) -> str:
    return json.dumps(
        serialize(obj),
        ensure_ascii=False,
        default=str,
    ).lower()


def evaluate_existing_query_case(
    case: dict[str, Any],
    service: Any | None,
) -> tuple[list[dict[str, Any]], Any, str | None]:

    question = case["input"]

    execution, error = execute_query(
        service,
        question,
    )

    if execution is None:
        checks = [
            capability(
                behavior=behavior,
                status=NOT_EXECUTED,
                note=error,
            )
            for behavior in case["expected"].get(
                "required_behaviors",
                [],
            )
        ]

        return checks, None, error

    raw = serialize(execution)
    dump = text_values(raw)

    checks: list[dict[str, Any]] = []

    for behavior in case["expected"].get(
        "required_behaviors",
        [],
    ):
        status = NOT_EXECUTED
        note = (
            "No deterministic evaluator rule exists "
            "for this behavior in baseline V1."
        )

        # Deterministic signals already available in baseline.
        if behavior == "route_to_comparative_fiqh":
            status = (
                PASS
                if "comparative" in dump
                else FAIL
            )
            note = None

        elif behavior == "create_multi_position_evidence_requirements":
            status = (
                PASS
                if (
                    "documented_disagreement" in dump
                    or "madhhab_scope" in dump
                    or "classical_fiqh_position" in dump
                )
                else FAIL
            )
            note = None

        elif behavior == "detect_disputed_issue":
            status = (
                PASS
                if (
                    "contested_claim" in dump
                    or "preserve_disagreement" in dump
                    or "do_not_claim_consensus" in dump
                )
                else FAIL
            )
            note = None

        elif behavior == "identify_individual_case":
            # Official A/B/C/D is not baseline functionality.
            status = NOT_IMPLEMENTED
            note = (
                "Official competition sensitivity "
                "classifier is not implemented."
            )

        elif behavior == "reject_request_to_invent_evidence":
            # We do not infer this from absence of generated text.
            status = NOT_IMPLEMENTED
            note = (
                "Competition prompt/policy guard is "
                "not implemented as a first-class contract."
            )

        checks.append(
            capability(
                behavior=behavior,
                status=status,
                evidence=raw if status in (PASS, FAIL) else None,
                note=note,
            )
        )

    return checks, raw, error


def evaluate_quran_case(
    case: dict[str, Any],
) -> tuple[list[dict[str, Any]], Any, str | None]:

    try:
        from basira.api.service import build_quran_runtime
        from basira.verification.quran_verifier import (
            QuranQuoteVerifier,
        )
    except Exception as exc:
        return (
            [
                capability(
                    behavior=b,
                    status=NOT_EXECUTED,
                    note=f"import failure: {exc}",
                )
                for b in case["expected"].get(
                    "required_behaviors",
                    [],
                )
            ],
            None,
            str(exc),
        )

    try:
        sig = inspect.signature(build_quran_runtime)

        required = [
            p
            for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind
            not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )
        ]

        if required:
            raise RuntimeError(
                "build_quran_runtime requires: "
                + ", ".join(p.name for p in required)
            )

        runtime = build_quran_runtime()

        repository = runtime

        # Common wrapper shapes.
        for attr in (
            "repository",
            "quran_repository",
            "repo",
        ):
            candidate = getattr(runtime, attr, None)
            if candidate is not None:
                repository = candidate
                break

        verifier = QuranQuoteVerifier(repository)

        # Remove benchmark instruction prefix.
        text = case["input"].split(":", 1)[-1].strip()

        result = verifier.verify(text)
        raw = serialize(result)
        dump = text_values(raw)

    except Exception as exc:
        return (
            [
                capability(
                    behavior=b,
                    status=NOT_EXECUTED,
                    note=f"{type(exc).__name__}: {exc}",
                )
                for b in case["expected"].get(
                    "required_behaviors",
                    [],
                )
            ],
            None,
            f"{type(exc).__name__}: {exc}",
        )

    altered_case = case["case_id"] == "quran_altered_001"

    checks = []

    for behavior in case["expected"].get(
        "required_behaviors",
        [],
    ):
        if behavior in (
            "identify_quranic_text",
            "resolve_surah_and_ayah",
            "accept_exact_or_valid_normalized_match",
        ):
            status = (
                PASS
                if (
                    "exact_match" in dump
                    or "normalized_match" in dump
                )
                else FAIL
            )

        elif behavior in (
            "detect_textual_mismatch",
            "resolve_likely_reference",
        ):
            status = (
                PASS
                if (
                    "altered_text" in dump
                    or "partial_match" in dump
                )
                else FAIL
            )

        elif behavior == "show_canonical_text":
            status = (
                PASS
                if (
                    "canonical" in dump
                    or "verse" in dump
                    or "candidate" in dump
                )
                else FAIL
            )

        elif behavior == "show_traceable_source":
            status = (
                PASS
                if (
                    "surah" in dump
                    and (
                        "ayah" in dump
                        or "verse" in dump
                    )
                )
                else FAIL
            )

        elif behavior == "prevent_reasoning_from_altered_text":
            # Quote verifier detects alteration, but this benchmark
            # requires a downstream hard gate.
            status = NOT_IMPLEMENTED

        else:
            status = NOT_EXECUTED

        checks.append(
            capability(
                behavior=behavior,
                status=status,
                evidence=raw,
                note=(
                    "Baseline detects altered text but "
                    "competition requires explicit downstream "
                    "reasoning gate."
                    if altered_case
                    and behavior
                    == "prevent_reasoning_from_altered_text"
                    else None
                ),
            )
        )

    return checks, raw, None


def evaluate_case(
    case: dict[str, Any],
    service: Any | None,
    extensions: dict[str, bool],
) -> dict[str, Any]:

    cid = case["case_id"]
    category = case["category"]
    input_type = case["input_type"]

    start = time.perf_counter()

    raw = None
    error = None

    if category == "quran_integrity":
        checks, raw, error = evaluate_quran_case(
            case
        )

    elif input_type == "user_query":
        checks, raw, error = (
            evaluate_existing_query_case(
                case,
                service,
            )
        )

    elif category == "source_attestation":
        implemented = extensions[
            "quran_witness_attestation"
        ]

        checks = [
            capability(
                behavior=b,
                status=(
                    NOT_EXECUTED
                    if implemented
                    else NOT_IMPLEMENTED
                ),
                note=(
                    "Witness-aware competition attestation "
                    "module not implemented."
                    if not implemented
                    else "Module exists; V1 adapter will "
                    "execute after public contract is present."
                ),
            )
            for b in case["expected"].get(
                "required_behaviors",
                [],
            )
        ]

    elif category == "claim_evidence_verification":
        implemented = extensions[
            "claim_evidence_semantics"
        ]

        checks = [
            capability(
                behavior="semantic_claim_evidence_relation",
                status=(
                    NOT_EXECUTED
                    if implemented
                    else NOT_IMPLEMENTED
                ),
                note=(
                    "Baseline claim integrity is literal/"
                    "structural, not semantic entailment."
                    if not implemented
                    else "Semantic verifier module detected."
                ),
            )
        ]

    elif category == "failure_learning":
        failure = extensions[
            "failure_certification"
        ]
        memory = extensions["safe_memory"]

        checks = [
            capability(
                behavior="failure_classification",
                status=(
                    NOT_EXECUTED
                    if failure
                    else NOT_IMPLEMENTED
                ),
                note=(
                    None
                    if failure
                    else "Failure certifier absent."
                ),
            ),
            capability(
                behavior="memory_destination",
                status=(
                    NOT_EXECUTED
                    if memory
                    else NOT_IMPLEMENTED
                ),
                note=(
                    None
                    if memory
                    else "Pluralism-safe memory absent."
                ),
            ),
        ]

    else:
        checks = [
            capability(
                behavior="case_execution",
                status=NOT_EXECUTED,
                note="No evaluator adapter.",
            )
        ]

    expected_level = (
        case.get("expected", {})
        .get("content_level")
    )

    if expected_level is not None:
        if extensions["content_sensitivity"]:
            checks.append(
                capability(
                    behavior="content_level",
                    status=NOT_EXECUTED,
                    note=(
                        "Competition sensitivity module "
                        "detected but not present in baseline."
                    ),
                )
            )
        else:
            checks.append(
                capability(
                    behavior="content_level",
                    status=NOT_IMPLEMENTED,
                    note=(
                        "Official A/B/C/D sensitivity "
                        "is absent from imported baseline."
                    ),
                )
            )

    duration_ms = round(
        (time.perf_counter() - start) * 1000,
        3,
    )

    counts = {
        state: sum(
            c["status"] == state
            for c in checks
        )
        for state in (
            PASS,
            FAIL,
            NOT_IMPLEMENTED,
            NOT_EXECUTED,
        )
    }

    return {
        "case_id": cid,
        "category": category,
        "checks": checks,
        "counts": counts,
        "duration_ms": duration_ms,
        "runtime_error": error,
        "raw_execution": raw,
    }


def main() -> int:
    manifest = check_benchmark_integrity()

    benchmark = json.loads(
        BENCHMARK.read_text(encoding="utf-8")
    )

    extensions = inspect_competition_extensions()

    service, service_error = build_service()

    results = [
        evaluate_case(
            case,
            service,
            extensions,
        )
        for case in benchmark["cases"]
    ]

    totals = {
        state: sum(
            result["counts"][state]
            for result in results
        )
        for state in (
            PASS,
            FAIL,
            NOT_IMPLEMENTED,
            NOT_EXECUTED,
        )
    }

    executed = totals[PASS] + totals[FAIL]

    score = (
        totals[PASS] / executed
        if executed
        else 0.0
    )

    coverage_denominator = sum(totals.values())

    implementation_coverage = (
        (
            totals[PASS]
            + totals[FAIL]
            + totals[NOT_EXECUTED]
        )
        / coverage_denominator
        if coverage_denominator
        else 0.0
    )

    report = {
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_sha256": manifest["sha256"],
        "phase": "PRE_INNOVATION",
        "git_commit": os.popen(
            "git rev-parse HEAD"
        ).read().strip(),
        "git_branch": os.popen(
            "git branch --show-current"
        ).read().strip(),
        "competition_extensions": extensions,
        "default_query_service": {
            "available": service is not None,
            "error": service_error,
        },
        "totals": totals,
        "executed_check_accuracy": round(
            score,
            6,
        ),
        "implementation_coverage": round(
            implementation_coverage,
            6,
        ),
        "cases": results,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "benchmark": report[
                    "benchmark_id"
                ],
                "phase": report["phase"],
                "totals": totals,
                "executed_check_accuracy": (
                    report[
                        "executed_check_accuracy"
                    ]
                ),
                "implementation_coverage": (
                    report[
                        "implementation_coverage"
                    ]
                ),
                "default_query_service": (
                    report[
                        "default_query_service"
                    ]
                ),
                "extensions": extensions,
                "result_file": str(OUTPUT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
