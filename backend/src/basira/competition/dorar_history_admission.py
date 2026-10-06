from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel

from basira.competition.dorar_history import (
    DorarHistoryEvent,
    parse_dorar_history_event,
)
from basira.competition.history_policy import (
    HistoricalReportStatus,
)


class DorarHistoryAdmissionError(
    ValueError
):
    pass


class DorarHistoryEvidenceEnvelope(
    BaseModel
):
    source_id: str

    source_family: str

    provider: str

    runtime_eligibility: str

    passport_id: str

    canonical_url: str

    response_sha256: str

    response_bytes: int

    adapter_contract: str

    event: DorarHistoryEvent

    runtime_evidence_role: str = (
        "historical_source_report"
    )

    historical_report_status: (
        HistoricalReportStatus
    ) = HistoricalReportStatus.UNASSESSED

    may_state_as_established_fact: bool = False

    categorical_claim_requires_governed_report_assessment: bool = True

    independent_hadith_authentication: bool = False

    canonical_quran_witness: bool = False

    event_reference_channel_established: bool = False

    generic_shamela_fallback_allowed: bool = False


def _load_json(
    path: Path,
) -> dict:

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def _validate_url_against_manifest(
    *,
    url: str,
    manifest: dict,
) -> None:

    parsed = urlsplit(
        url
    )

    if parsed.scheme != "https":
        raise DorarHistoryAdmissionError(
            "https_required"
        )

    if (
        parsed.hostname
        != manifest[
            "canonical_origin"
        ].removeprefix(
            "https://"
        )
    ):
        raise DorarHistoryAdmissionError(
            "exact_dorar_host_required"
        )

    if (
        parsed.username
        or parsed.password
        or parsed.port is not None
    ):
        raise DorarHistoryAdmissionError(
            "noncanonical_authority"
        )

    if parsed.query:
        raise DorarHistoryAdmissionError(
            "query_not_allowed"
        )

    if parsed.fragment:
        raise DorarHistoryAdmissionError(
            "fragment_not_allowed"
        )

    allowed = False

    for route in manifest[
        "allowed_route_families"
    ]:

        if re.fullmatch(
            route["regex"],
            parsed.path,
        ):

            allowed = True
            break

    if not allowed:
        raise DorarHistoryAdmissionError(
            "noncanonical_history_event_route"
        )


def _audited_baseline_hash(
    *,
    canonical_url: str,
    manifest: dict,
) -> str | None:

    matches = [
        item
        for item in manifest[
            "audited_baselines"
        ]
        if (
            item[
                "canonical_url"
            ]
            == canonical_url
        )
    ]

    if len(matches) > 1:
        raise DorarHistoryAdmissionError(
            "duplicate_audited_baseline"
        )

    if not matches:
        return None

    return matches[
        0
    ][
        "sha256"
    ]


def admit_dorar_history_response(
    *,
    canonical_url: str,
    response_bytes: bytes,
    runtime_manifest_path: Path,
    passport_path: Path,
) -> DorarHistoryEvidenceEnvelope:

    manifest = _load_json(
        runtime_manifest_path
    )

    passport = _load_json(
        passport_path
    )


    if (
        manifest[
            "runtime_eligibility"
        ]
        != "eligible"
    ):
        raise DorarHistoryAdmissionError(
            "runtime_not_eligible"
        )


    if (
        passport[
            "runtime_eligibility"
        ]
        != "eligible"
    ):
        raise DorarHistoryAdmissionError(
            "passport_not_runtime_eligible"
        )


    if (
        passport[
            "source_id"
        ]
        != manifest[
            "source_id"
        ]
    ):
        raise DorarHistoryAdmissionError(
            "passport_source_mismatch"
        )


    if (
        passport[
            "adapter_contract"
        ]
        != manifest[
            "adapter_contract"
        ]
    ):
        raise DorarHistoryAdmissionError(
            "adapter_contract_mismatch"
        )


    _validate_url_against_manifest(
        url=canonical_url,
        manifest=manifest,
    )


    if not response_bytes:
        raise DorarHistoryAdmissionError(
            "empty_response"
        )


    response_sha256 = (
        hashlib.sha256(
            response_bytes
        ).hexdigest()
    )


    baseline_sha = (
        _audited_baseline_hash(
            canonical_url=canonical_url,
            manifest=manifest,
        )
    )


    if (
        baseline_sha is not None
        and response_sha256
        != baseline_sha
    ):
        raise DorarHistoryAdmissionError(
            "audited_baseline_artifact_drift"
        )


    event = parse_dorar_history_event(
        html=response_bytes.decode(
            "utf-8",
            errors="replace",
        ),
        canonical_url=canonical_url,
    )


    # --------------------------------------------------------
    # STRUCTURAL SAFETY
    # --------------------------------------------------------

    audit = event.structural_audit

    if (
        audit.canonical_root_count
        != 1
    ):
        raise DorarHistoryAdmissionError(
            "canonical_root_contract_failed"
        )

    if (
        audit.event_accordion_count
        != 1
    ):
        raise DorarHistoryAdmissionError(
            "event_accordion_contract_failed"
        )

    if (
        audit.event_container_count
        != 1
    ):
        raise DorarHistoryAdmissionError(
            "event_container_contract_failed"
        )

    if (
        audit.event_card_count
        != 1
    ):
        raise DorarHistoryAdmissionError(
            "event_card_contract_failed"
        )

    if (
        audit.provenance_violation_count
        != 0
    ):
        raise DorarHistoryAdmissionError(
            "provenance_contract_failed"
        )


    # --------------------------------------------------------
    # SEMANTIC SAFETY
    #
    # Runtime eligibility means governed retrieval.
    #
    # It does NOT mean every Dorar event becomes an
    # ESTABLISHED historical fact.
    # --------------------------------------------------------

    if (
        event.historical_report_status
        is not HistoricalReportStatus
        .UNASSESSED
    ):
        raise DorarHistoryAdmissionError(
            "adapter_must_not_promote_historical_status"
        )

    if (
        event.lexical_signal_is_truth_grade
        is not False
    ):
        raise DorarHistoryAdmissionError(
            "unsafe_disagreement_truth_promotion"
        )

    if (
        event
        .lexical_signal_is_hadith_authentication
        is not False
    ):
        raise DorarHistoryAdmissionError(
            "unsafe_hadith_authentication"
        )

    if (
        event.hadith_matn_structurally_extractable
        is not False
    ):
        raise DorarHistoryAdmissionError(
            "unsafe_hadith_matn_promotion"
        )

    if (
        event.event_reference_channel_established
        is not False
    ):
        raise DorarHistoryAdmissionError(
            "unsafe_event_reference_channel"
        )

    if (
        event.quran_typed_channel_established
        is not False
    ):
        raise DorarHistoryAdmissionError(
            "unsafe_quran_channel"
        )

    if (
        event.hadith_typed_channel_established
        is not False
    ):
        raise DorarHistoryAdmissionError(
            "unsafe_hadith_channel"
        )

    if (
        event.promoted_event_reference_count
        != 0
    ):
        raise DorarHistoryAdmissionError(
            "event_reference_promotion_detected"
        )

    if (
        event.promoted_quran_witness_count
        != 0
    ):
        raise DorarHistoryAdmissionError(
            "quran_witness_promotion_detected"
        )

    if (
        event
        .independent_hadith_authentication_count
        != 0
    ):
        raise DorarHistoryAdmissionError(
            "independent_hadith_authentication_detected"
        )

    if (
        event
        .per_event_machine_truth_grade_count
        != 0
    ):
        raise DorarHistoryAdmissionError(
            "machine_truth_grade_detected"
        )


    boundaries = manifest[
        "semantic_boundaries"
    ]


    if (
        boundaries[
            "runtime_admission_equals_established_fact"
        ]
        is not False
    ):
        raise DorarHistoryAdmissionError(
            "unsafe_runtime_fact_semantics"
        )


    if (
        boundaries[
            "categorical_claim_requires_separate_governed_report_assessment"
        ]
        is not True
    ):
        raise DorarHistoryAdmissionError(
            "categorical_claim_gate_missing"
        )


    return DorarHistoryEvidenceEnvelope(
        source_id=(
            manifest[
                "source_id"
            ]
        ),
        source_family=(
            manifest[
                "source_family"
            ]
        ),
        provider=(
            manifest[
                "provider"
            ]
        ),
        runtime_eligibility=(
            manifest[
                "runtime_eligibility"
            ]
        ),
        passport_id=(
            passport[
                "passport_id"
            ]
        ),
        canonical_url=canonical_url,
        response_sha256=(
            response_sha256
        ),
        response_bytes=(
            len(
                response_bytes
            )
        ),
        adapter_contract=(
            manifest[
                "adapter_contract"
            ]
        ),
        event=event,
    )
